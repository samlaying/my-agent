"""Tests for the 定时推荐 (scheduled recommendations) system."""

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


class _FakeRecommender:
    """Minimal stand-in matching the Recommender interface."""

    def __init__(self, source, recs):
        self.source = source
        self._recs = recs

    def recommend(self):
        return list(self._recs)


class ContractTests(unittest.TestCase):
    def test_roundtrip_preserves_fields(self):
        from recommendations.contract import Recommendation

        rec = Recommendation(
            id="x", source="task", kind="task", title="T", reason="R",
            priority=4, action={"type": "tool", "name": "claim_task"},
        )
        rec2 = Recommendation.from_dict(rec.to_dict())
        self.assertEqual(rec2.id, "x")
        self.assertEqual(rec2.priority, 4)
        self.assertEqual(rec2.action["name"], "claim_task")

    def test_from_dict_ignores_unknown_keys(self):
        from recommendations.contract import Recommendation

        rec = Recommendation.from_dict(
            {"id": "y", "source": "s", "kind": "k", "title": "t", "reason": "r", "bogus": 1}
        )
        self.assertEqual(rec.id, "y")
        self.assertEqual(rec.status, "new")

    def test_stable_id_is_deterministic(self):
        from recommendations.contract import stable_id

        self.assertEqual(stable_id("a", "b"), stable_id("a", "b"))
        self.assertNotEqual(stable_id("a"), stable_id("b"))


class FeedTests(unittest.TestCase):
    def setUp(self):
        import recommendations.feed as feed_mod
        self.feed_mod = feed_mod
        self._orig_path = feed_mod.RECOMMENDATIONS_PATH
        self._tmp = tempfile.TemporaryDirectory()
        feed_mod.RECOMMENDATIONS_PATH = Path(self._tmp.name) / "recs.json"

    def tearDown(self):
        self.feed_mod.RECOMMENDATIONS_PATH = self._orig_path
        self._tmp.cleanup()

    def _rec(self, rec_id, status="new", priority=3):
        from recommendations.contract import Recommendation
        return Recommendation(
            id=rec_id, source="task", kind="task", title=rec_id, reason="r",
            priority=priority, status=status,
        )

    def test_replace_all_preserves_user_status_across_refresh(self):
        self.feed_mod.replace_all([self._rec("a"), self._rec("b")])
        self.feed_mod.set_status("a", "dismissed")
        # regenerate with an overlapping set — 'a' must stay dismissed
        self.feed_mod.replace_all([self._rec("a"), self._rec("c")])
        by_id = {r.id: r.status for r in self.feed_mod.read_all()}
        self.assertEqual(by_id["a"], "dismissed")
        self.assertEqual(by_id["c"], "new")

    def test_read_active_filters_non_new(self):
        self.feed_mod.replace_all([self._rec("a"), self._rec("b")])
        self.feed_mod.set_status("a", "done")
        self.assertEqual({r.id for r in self.feed_mod.read_active()}, {"b"})

    def test_set_status_rejects_invalid_status(self):
        self.feed_mod.replace_all([self._rec("a")])
        self.assertTrue(self.feed_mod.set_status("a", "bogus").startswith("Error"))

    def test_set_status_unknown_id(self):
        self.feed_mod.replace_all([self._rec("a")])
        self.assertIn("Not found", self.feed_mod.set_status("zzz", "done"))


class RecommenderTests(unittest.TestCase):
    def test_task_recommender_picks_unclaimed_and_inprogress(self):
        from recommendations.recommenders import task_recommender as tr

        tr.list_tasks = lambda: [
            SimpleNamespace(id="t1", subject="Fix bug", status="pending", owner=None, blockedBy=[]),
            SimpleNamespace(id="t2", subject="Owned", status="in_progress", owner="x", blockedBy=[]),
        ]
        recs = tr.TaskRecommender().recommend()
        by_id = {r.id: r for r in recs}
        self.assertIn("task:t1", by_id)
        self.assertIn("task:t2", by_id)
        self.assertEqual(by_id["task:t1"].priority, 5)  # ready to start

    def test_loop_recommender_inbox_and_blocked(self):
        from recommendations.recommenders import loop_recommender as lr

        lr.read_loop_state = lambda: {
            "Inbox": ["- [ ] flaky test", "- [ ] add docs"],
            "In Progress": [], "Done": [], "Decisions": [],
            "Blocked": ["- risky migration — **Blocked:** needs approval"],
        }
        recs = lr.LoopRecommender().recommend()
        kinds = [r.kind for r in recs]
        self.assertIn("fix", kinds)
        self.assertIn("note", kinds)

    def test_cron_recommender_flags_triage_gap(self):
        from recommendations.recommenders import cron_recommender as cr

        cr.scheduled_jobs = {}
        recs = cr.CronRecommender().recommend()
        self.assertTrue(any(r.id == "cron:triage-gap" for r in recs))

    def test_memory_recommender_scans_markers(self):
        from recommendations.recommenders import memory_recommender as mr

        with tempfile.TemporaryDirectory() as tmp:
            mr.MEMORY_DIR = Path(tmp)
            (Path(tmp) / "notes.md").write_text("TODO: call client\nnothing here\n", encoding="utf-8")
            recs = mr.MemoryRecommender().recommend()
            self.assertTrue(any("call client" in r.title for r in recs))

    def test_tool_recommender_suggests_disabled_and_warns_risk(self):
        from recommendations.recommenders import tool_recommender as tr

        # write_file enabled (not suggested), edit_file disabled (suggested),
        # remove_worktree enabled (high-risk warning).
        tr.is_tool_enabled = lambda name, td=None: name in ("write_file", "remove_worktree")
        ids = {r.id for r in tr.ToolRecommender().recommend()}
        self.assertIn("tool:enable:edit_file", ids)
        self.assertNotIn("tool:enable:write_file", ids)
        self.assertIn("tool:risk:remove_worktree", ids)


class EngineTests(unittest.TestCase):
    def setUp(self):
        from recommendations import engine
        self.engine = engine
        self._saved = list(engine.REGISTERED)

    def tearDown(self):
        self.engine.REGISTERED = self._saved

    def test_collect_dedupes_by_id_keeps_higher_priority_and_ranks(self):
        from recommendations.contract import Recommendation

        self.engine.REGISTERED = [
            _FakeRecommender("s1", [
                Recommendation(id="dup", source="s1", kind="k", title="a", reason="r", priority=2),
            ]),
            _FakeRecommender("s2", [
                Recommendation(id="dup", source="s2", kind="k", title="b", reason="r", priority=5),
                Recommendation(id="hi", source="s2", kind="k", title="c", reason="r", priority=4),
            ]),
        ]
        ranked = self.engine.collect()
        # 'dup' deduped to priority 5; ranked before 'hi' (priority 4).
        self.assertEqual([r.id for r in ranked], ["dup", "hi"])
        self.assertEqual(ranked[0].priority, 5)

    def test_engine_isolates_failing_recommenders(self):
        from recommendations.contract import Recommendation

        class Boom:
            source = "boom"
            def recommend(self):
                raise RuntimeError("nope")

        self.engine.REGISTERED = [
            Boom(),
            _FakeRecommender("good", [
                Recommendation(id="g", source="good", kind="k", title="g", reason="r", priority=3),
            ]),
        ]
        ranked = self.engine.collect()
        ids = [r.id for r in ranked]
        self.assertIn("g", ids)
        self.assertTrue(any(r.id.startswith("engine:error:boom") for r in ranked))


class ToolIntegrationTests(unittest.TestCase):
    def test_recommend_tools_registered_and_categorized(self):
        from tools.dispatch import register_all_handlers, assemble_all_tool_pool
        from tools.registry import DEFAULT_TOOL_META

        register_all_handlers()
        tools, handlers = assemble_all_tool_pool()
        names = {t["name"] for t in tools}
        for name in ("recommend", "list_recommendations", "dismiss_recommendation"):
            self.assertIn(name, names, f"{name} missing from pool")
            self.assertIn(name, handlers, f"{name} has no handler")
            self.assertEqual(DEFAULT_TOOL_META[name]["category"], "context")

    def test_recommend_handler_returns_summary(self):
        from recommendations.tools import run_recommend

        out = run_recommend(3)
        self.assertIsInstance(out, str)
        self.assertIn("[Recommendations]", out)


if __name__ == "__main__":
    unittest.main()
