"""memory_recommender — 从 .memory 扫出待跟进的条目（含 TODO/should 等标记）。"""

from __future__ import annotations

from core.config import MEMORY_DIR

from recommendations.contract import Recommendation, Recommender, stable_id

_MARKERS = ("todo", "should", "remember to", "don't forget", "needs ", "pending", "follow up")
_MAX = 6


class MemoryRecommender(Recommender):
    source = "memory"

    def recommend(self) -> list[Recommendation]:
        recs: list[Recommendation] = []
        if not MEMORY_DIR.exists():
            return recs

        for path in sorted(MEMORY_DIR.glob("*.md")):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for line in text.splitlines():
                low = line.lower()
                if len(line.strip()) <= 6 or not any(m in low for m in _MARKERS):
                    continue
                recs.append(
                    Recommendation(
                        id=f"memory:{stable_id(path.name, line)}",
                        source=self.source,
                        kind="note",
                        title=f"Follow up: {line.strip()[:72]}",
                        reason=f"Noted in {path.name}.",
                        priority=2,
                        action={"type": "none"},
                    )
                )
                if len(recs) >= _MAX:
                    return recs
        return recs
