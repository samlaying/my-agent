"""cron_recommender — 检测定时缺口，并展示当前活跃的定时任务。"""

from __future__ import annotations

from scheduler.cron import scheduled_jobs

from recommendations.contract import Recommendation, Recommender


class CronRecommender(Recommender):
    source = "cron"

    def recommend(self) -> list[Recommendation]:
        recs: list[Recommendation] = []
        jobs = list(scheduled_jobs.values())

        has_triage = any(
            "triage" in (j.prompt or "").lower() or "loop_triage" in (j.prompt or "").lower()
            for j in jobs
        )
        if not has_triage:
            recs.append(
                Recommendation(
                    id="cron:triage-gap",
                    source=self.source,
                    kind="schedule",
                    title="Schedule a daily project triage",
                    reason="No recurring triage cron found; the loop inbox may go stale.",
                    priority=3,
                    action={
                        "type": "tool",
                        "name": "schedule_cron",
                        "args": {
                            "cron": "17 9 * * 1-5",
                            "prompt": "Use loop_triage to run project triage.",
                            "recurring": True,
                            "durable": True,
                        },
                    },
                )
            )

        for j in jobs[:5]:
            recs.append(
                Recommendation(
                    id=f"cron:active:{j.id}",
                    source=self.source,
                    kind="schedule",
                    title=f"Recurring job active: '{j.cron}'",
                    reason=f"Prompt: {(j.prompt or '')[:90]}",
                    priority=2,
                    action={"type": "none"},
                )
            )
        return recs
