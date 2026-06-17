"""recommendations.tools — 推荐系统的工具包装（供 dispatch 注册）。"""

from __future__ import annotations

from recommendations import feed
from recommendations.engine import status


def run_recommend(limit: int = 12) -> str:
    """刷新整条推荐流并返回摘要。"""
    return status(limit=int(limit or 12))


def run_list_recommendations() -> str:
    """只读：列出当前活跃的推荐（不刷新）。"""
    recs = feed.read_active()
    if not recs:
        return "[Recommendations] No active recommendations."
    lines = [f"[Recommendations] {len(recs)} active:"]
    for r in recs:
        lines.append(f"  P{r.priority} [{r.source}/{r.kind}] {r.title}")
    return "\n".join(lines)


def run_dismiss_recommendation(id: str, status: str = "dismissed") -> str:
    """把某条推荐标记为 dismissed / done / new。"""
    return feed.set_status(id, status)
