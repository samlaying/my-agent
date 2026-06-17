"""loop_recommender — 从 LOOP_STATE.md 的 Inbox / Blocked 推荐修复与人工决策。"""

from __future__ import annotations

from agents.loop_state import read_loop_state

from recommendations.contract import Recommendation, Recommender, stable_id


class LoopRecommender(Recommender):
    source = "loop"

    def recommend(self) -> list[Recommendation]:
        sections = read_loop_state()
        recs: list[Recommendation] = []

        inbox = [l for l in sections.get("Inbox", []) if "- [ ]" in l]
        for line in inbox[:8]:
            item = line.strip("- [] \t")
            if not item:
                continue
            recs.append(
                Recommendation(
                    id=f"loop:fix:{stable_id(item)}",
                    source=self.source,
                    kind="fix",
                    title=f"Fix loop inbox item: {item[:70]}",
                    reason="Discovered by triage, awaiting a fix.",
                    priority=4,
                    action={"type": "tool", "name": "loop_fix", "args": {}},
                )
            )

        blocked = [
            l for l in sections.get("Blocked", [])
            if l.strip() and not l.strip().startswith("<!--") and not l.strip().startswith("|")
        ]
        for line in blocked[:4]:
            text = line.strip("- *").strip()
            if not text:
                continue
            recs.append(
                Recommendation(
                    id=f"loop:blocked:{stable_id(text)}",
                    source=self.source,
                    kind="note",
                    title=f"Blocked item needs a decision: {text[:60]}",
                    reason="Marked blocked, needs human judgment.",
                    priority=3,
                    action={"type": "none"},
                )
            )
        return recs
