"""task_recommender — 从 .tasks 推荐可认领/待完成的任务。"""

from __future__ import annotations

from tasks.task import list_tasks

from recommendations.contract import Recommendation, Recommender


class TaskRecommender(Recommender):
    source = "task"

    def recommend(self) -> list[Recommendation]:
        recs: list[Recommendation] = []
        try:
            tasks = list_tasks()
        except Exception:
            return recs

        for t in tasks:
            if t.status == "pending" and not t.owner:
                ready = not t.blockedBy
                recs.append(
                    Recommendation(
                        id=f"task:{t.id}",
                        source=self.source,
                        kind="task",
                        title=f"Pick up task: {t.subject}",
                        reason=(
                            "Unclaimed and ready to start."
                            if ready
                            else f"Blocked by {len(t.blockedBy)} task(s)."
                        ),
                        priority=5 if ready else 4,
                        action={"type": "tool", "name": "claim_task", "args": {"task_id": t.id}},
                    )
                )
            elif t.status == "in_progress":
                recs.append(
                    Recommendation(
                        id=f"task:{t.id}",
                        source=self.source,
                        kind="task",
                        title=f"Finish in-progress task: {t.subject}",
                        reason="Already claimed, still open.",
                        priority=3,
                        action={"type": "tool", "name": "complete_task", "args": {"task_id": t.id}},
                    )
                )
        return recs[:10]
