"""recommendations.feed — 推荐流的持久化与状态管理。

文件：``.agent/recommendations.json``。每次刷新会保留用户已设置的 dismissed/done
状态（按 id 匹配），避免刷新把用户处理过的卡片再次顶起来。
"""

from __future__ import annotations

import json

from core.config import RECOMMENDATIONS_PATH
from recommendations.contract import Recommendation

_ACTIVE_STATUSES = {"new", "dismissed", "done"}


def _load_raw() -> dict:
    if not RECOMMENDATIONS_PATH.exists():
        return {}
    try:
        return json.loads(RECOMMENDATIONS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _dump(recs: list[Recommendation]) -> None:
    RECOMMENDATIONS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"items": [r.to_dict() for r in recs]}
    RECOMMENDATIONS_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def read_all() -> list[Recommendation]:
    items = _load_raw().get("items", [])
    return [Recommendation.from_dict(it) for it in items if isinstance(it, dict)]


def read_active() -> list[Recommendation]:
    """仅返回未处理的卡片（status == new）。"""
    return [r for r in read_all() if r.status == "new"]


def replace_all(new_recs: list[Recommendation]) -> list[Recommendation]:
    """刷新整条流：保留旧的 dismissed/done 状态。"""
    prev_status = {r.id: r.status for r in read_all()}
    for rec in new_recs:
        old = prev_status.get(rec.id)
        if old in ("dismissed", "done"):
            rec.status = old
    _dump(new_recs)
    return new_recs


def set_status(rec_id: str, status: str) -> str:
    if status not in _ACTIVE_STATUSES:
        return f"Error: invalid status '{status}'. Use one of: {', '.join(sorted(_ACTIVE_STATUSES))}"
    recs = read_all()
    changed = False
    for r in recs:
        if r.id == rec_id:
            r.status = status
            changed = True
    if not changed:
        return f"Not found: {rec_id}"
    _dump(recs)
    return f"Recommendation {rec_id} marked {status}."
