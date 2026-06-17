"""recommendations.engine — 聚合原子 recommender，去重排序，持久化，定时刷新。

设计要点：
- 每个 recommender 独立 try/except，单个失败不拖垮整条流，失败本身会变成一张卡片。
- 去重按 id（stable_id 保证跨进程稳定），冲突取更高优先级。
- ``ensure_scheduled`` 注册一条默认的每日 cron（幂等），由 agent_loop 在到点时刷新。
"""

from __future__ import annotations

from recommendations import feed
from recommendations.contract import Recommendation, Recommender
from recommendations.recommenders import (
    CronRecommender,
    LoopRecommender,
    MemoryRecommender,
    TaskRecommender,
    ToolRecommender,
)

# 原子 recommender 注册表。新增来源 = 在此追加一项。
REGISTERED: list[Recommender] = [
    TaskRecommender(),
    LoopRecommender(),
    CronRecommender(),
    ToolRecommender(),
    MemoryRecommender(),
]

_DEFAULT_CRON = "17 9 * * 1-5"
_DEFAULT_PROMPT = (
    "[Scheduled] Refresh scheduled recommendations: call the recommend tool now."
)
_MARKER = "recommend"


def collect() -> list[Recommendation]:
    """运行所有 recommender，去重排序，但不落盘。"""
    raw: list[Recommendation] = []
    for recommender in REGISTERED:
        try:
            raw.extend(recommender.recommend())
        except Exception as exc:  # noqa: BLE001 — 一个失败不应影响其它来源
            raw.append(
                Recommendation(
                    id=f"engine:error:{recommender.source}",
                    source=recommender.source,
                    kind="note",
                    title=f"Recommender '{recommender.source}' failed",
                    reason=f"{type(exc).__name__}: {exc}",
                    priority=1,
                    action={"type": "none"},
                )
            )

    by_id: dict[str, Recommendation] = {}
    for rec in raw:
        current = by_id.get(rec.id)
        if current is None or rec.priority > current.priority:
            by_id[rec.id] = rec
    return sorted(by_id.values(), key=lambda r: (-r.priority, r.source, r.title))


def run_all() -> list[Recommendation]:
    """刷新并持久化整条推荐流，返回活跃卡片。"""
    ranked = collect()
    feed.replace_all(ranked)
    return ranked


def status(limit: int = 12) -> str:
    """供 /reco 与工具调用：刷新并返回可读摘要。"""
    recs = run_all()
    active = [r for r in recs if r.status == "new"]
    if not active:
        return "[Recommendations] Nothing to recommend right now."
    lines = [f"[Recommendations] {len(active)} active item(s) (refreshed just now):"]
    for rec in active[:limit]:
        lines.append(f"  P{rec.priority} [{rec.source}/{rec.kind}] {rec.title}")
        if rec.reason:
            lines.append(f"      ↳ {rec.reason}")
    return "\n".join(lines)


def ensure_scheduled() -> bool:
    """若无任何 recommend 相关 cron，则注册一条每日定时任务。返回是否新建。"""
    from scheduler.cron import schedule_job, scheduled_jobs

    for job in scheduled_jobs.values():
        if _MARKER in (job.prompt or "").lower():
            return False
    result = schedule_job(_DEFAULT_CRON, _DEFAULT_PROMPT, recurring=True, durable=True)
    return not isinstance(result, str)
