import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")


class AgentProfileTests(unittest.TestCase):
    def test_profile_carries_soul_tools_triggers_and_memory_policy(self):
        from agents.profile import AgentProfile, MemoryPolicy, Trigger

        profile = AgentProfile(
            id="english",
            soul="You help me pass CET-4 and CET-6.",
            skills=["cet4-cet6"],
            tool_profile="learning",
            memory=MemoryPolicy(namespaces=["global", "learning", "english"], max_chars=1200),
            triggers=[Trigger(type="cron", value="0 8 * * *", prompt="Start listening practice.")],
        )

        self.assertEqual(profile.id, "english")
        self.assertEqual(profile.tool_profile, "learning")
        self.assertIn("cet4-cet6", profile.skills)
        self.assertEqual(profile.memory.namespaces, ["global", "learning", "english"])
        self.assertEqual(profile.triggers[0].type, "cron")

    def test_memory_service_searches_selected_namespaces_only(self):
        from agents.profile import MemoryPolicy
        from context.memory import MemoryService

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "global.md").write_text("I prefer concise reports.\n", encoding="utf-8")
            (root / "english.md").write_text("CET listening needs commute drills.\n", encoding="utf-8")
            (root / "work.md").write_text("Customer renewal risk is high.\n", encoding="utf-8")

            service = MemoryService(root)
            result = service.retrieve(
                query="listening commute",
                policy=MemoryPolicy(namespaces=["global", "english"], max_chars=500),
            )

        self.assertIn("[global]", result)
        self.assertIn("[english]", result)
        self.assertIn("CET listening", result)
        self.assertNotIn("Customer renewal", result)

    def test_system_prompt_uses_profile_soul_and_memory_policy(self):
        from agents.profile import AgentProfile, MemoryPolicy
        from context.system_prompt import assemble_system_prompt

        profile = AgentProfile(
            id="butler",
            soul="You are my life butler.",
            skills=["daily-review"],
            tool_profile="automation",
            memory=MemoryPolicy(namespaces=["global", "life"], max_chars=300),
        )
        context = {
            "memories": "[life]\nDrink water at 10:00.",
            "connected_mcp": [],
            "active_teammates": [],
        }

        prompt = assemble_system_prompt(context, profile=profile)

        self.assertIn("Agent profile: butler", prompt)
        self.assertIn("You are my life butler.", prompt)
        self.assertIn("Required skills: daily-review", prompt)
        self.assertIn("Memory namespaces: global, life", prompt)
        self.assertIn("Drink water", prompt)

    def test_tool_executor_normalizes_tool_result_and_logs(self):
        from tools.executor import ToolExecutor

        events = []
        executor = ToolExecutor(
            handlers={"echo": lambda text: f"echo:{text}"},
            pre_hook=lambda block: None,
            post_hook=lambda block, output: events.append(("post", block.name, output)),
            logger=lambda name, args, output, latency_ms, blocked=False: events.append(("log", name, output, blocked)),
        )
        block = SimpleNamespace(name="echo", input={"text": "hello"}, id="toolu_1")

        result = executor.execute(block)

        self.assertEqual(result["type"], "tool_result")
        self.assertEqual(result["tool_use_id"], "toolu_1")
        self.assertEqual(result["content"], "echo:hello")
        self.assertIn(("post", "echo", "echo:hello"), events)
        self.assertIn(("log", "echo", "echo:hello", False), events)


if __name__ == "__main__":
    unittest.main()
