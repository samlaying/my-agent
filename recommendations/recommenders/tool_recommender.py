"""tool_recommender — 基于 active profile 推荐启用/禁用工具。

不依赖 handler 是否已注册，只用 registry 的 meta + 开关判断。
"""

from __future__ import annotations

from tools.registry import is_tool_enabled

from recommendations.contract import Recommendation, Recommender


# 常见缺口：编码场景常被 profile 关掉的写入工具。
_GAP_CANDIDATES = ["write_file", "edit_file"]
# 高风险工具：若处于启用状态则提醒。
_RISK_CANDIDATES = ["remove_worktree"]


class ToolRecommender(Recommender):
    source = "tool"

    def recommend(self) -> list[Recommendation]:
        recs: list[Recommendation] = []

        for name in _GAP_CANDIDATES:
            try:
                enabled = is_tool_enabled(name, None)
            except Exception:
                continue
            if not enabled:
                recs.append(
                    Recommendation(
                        id=f"tool:enable:{name}",
                        source=self.source,
                        kind="tool",
                        title=f"Enable {name}",
                        reason="Useful for the current workflow but not enabled by the active profile.",
                        priority=2,
                        action={"type": "tool", "name": "tool_enable", "args": {"name": name}},
                    )
                )

        for name in _RISK_CANDIDATES:
            try:
                enabled = is_tool_enabled(name, None)
            except Exception:
                continue
            if enabled:
                recs.append(
                    Recommendation(
                        id=f"tool:risk:{name}",
                        source=self.source,
                        kind="note",
                        title=f"{name} is enabled (high risk)",
                        reason="Destructive tool is currently available; disable it if not needed.",
                        priority=3,
                        action={"type": "tool", "name": "tool_disable", "args": {"name": name}},
                    )
                )
        return recs
