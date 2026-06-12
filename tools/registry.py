"""tools.registry - tool profiles, runtime switches, and hot reload state."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from core.config import WORKDIR


CONFIG_PATH = WORKDIR / ".agent" / "tools.json"
CONTROL_TOOLS = {
    "tool_status",
    "tool_enable",
    "tool_disable",
    "tool_profile",
    "tool_reload",
}

DEFAULT_PROFILES: dict[str, dict[str, Any]] = {
    "minimal": {
        "description": "Smallest useful toolset for reading, searching, and loading skills.",
        "categories": ["file", "skills", "context", "control"],
        "tools": ["todo_write"],
        "disabled": [],
    },
    "coding": {
        "description": "Default local coding workflow with files, shell, tasks, and skills.",
        "categories": ["shell", "file", "core", "skills", "context", "agent", "task", "control"],
        "tools": ["connect_mcp"],
        "disabled": ["remove_worktree"],
    },
    "research": {
        "description": "Research-oriented profile for docs, search, skills, and read-only local context.",
        "categories": ["file", "skills", "context", "mcp", "control"],
        "tools": ["bash", "todo_write"],
        "disabled": ["write_file", "edit_file"],
    },
    "automation": {
        "description": "Background work, cron jobs, teammates, worktrees, and project loops.",
        "categories": ["*"],
        "tools": [],
        "disabled": [],
    },
    "full": {
        "description": "Everything currently registered.",
        "categories": ["*"],
        "tools": [],
        "disabled": [],
    },
}

DEFAULT_TOOL_META: dict[str, dict[str, Any]] = {
    "bash": {"category": "shell", "risk": "medium"},
    "read_file": {"category": "file", "risk": "low"},
    "write_file": {"category": "file", "risk": "medium"},
    "edit_file": {"category": "file", "risk": "medium"},
    "glob": {"category": "file", "risk": "low"},
    "todo_write": {"category": "core", "risk": "low"},
    "task": {"category": "agent", "risk": "medium"},
    "load_skill": {"category": "skills", "risk": "low"},
    "compact": {"category": "context", "risk": "low"},
    "create_task": {"category": "task", "risk": "low"},
    "list_tasks": {"category": "task", "risk": "low"},
    "get_task": {"category": "task", "risk": "low"},
    "claim_task": {"category": "task", "risk": "low"},
    "complete_task": {"category": "task", "risk": "low"},
    "schedule_cron": {"category": "automation", "risk": "medium"},
    "list_crons": {"category": "automation", "risk": "low"},
    "cancel_cron": {"category": "automation", "risk": "medium"},
    "spawn_teammate": {"category": "team", "risk": "medium"},
    "send_message": {"category": "team", "risk": "low"},
    "check_inbox": {"category": "team", "risk": "low"},
    "request_shutdown": {"category": "team", "risk": "medium"},
    "request_plan": {"category": "team", "risk": "low"},
    "review_plan": {"category": "team", "risk": "medium"},
    "create_worktree": {"category": "worktree", "risk": "medium"},
    "remove_worktree": {"category": "worktree", "risk": "high"},
    "keep_worktree": {"category": "worktree", "risk": "low"},
    "connect_mcp": {"category": "mcp", "risk": "medium"},
    "loop_triage": {"category": "loop", "risk": "medium"},
    "loop_fix": {"category": "loop", "risk": "high"},
    "loop_status": {"category": "loop", "risk": "low"},
    "loop_inbox_add": {"category": "loop", "risk": "low"},
    "loop_done": {"category": "loop", "risk": "low"},
    "loop_block": {"category": "loop", "risk": "low"},
    "loop_decision": {"category": "loop", "risk": "low"},
    "writer_loop": {"category": "writing", "risk": "medium"},
    "score_draft": {"category": "writing", "risk": "low"},
    "writer_status": {"category": "writing", "risk": "low"},
}

for _name in CONTROL_TOOLS:
    DEFAULT_TOOL_META[_name] = {"category": "control", "risk": "low"}


def _default_state() -> dict[str, Any]:
    return {
        "activeProfile": "coding",
        "profiles": deepcopy(DEFAULT_PROFILES),
        "tools": {},
    }


def load_tool_state() -> dict[str, Any]:
    state = _default_state()
    if not CONFIG_PATH.exists():
        return state
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return state

    if isinstance(data.get("profiles"), dict):
        for name, profile in data["profiles"].items():
            if isinstance(profile, dict):
                merged = deepcopy(DEFAULT_PROFILES.get(name, {}))
                merged.update(profile)
                state["profiles"][name] = merged
    if isinstance(data.get("tools"), dict):
        state["tools"].update(data["tools"])
    if data.get("activeProfile") in state["profiles"]:
        state["activeProfile"] = data["activeProfile"]
    return state


def save_tool_state(state: dict[str, Any]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tool_meta(name: str, tool_def: dict | None = None) -> dict[str, Any]:
    meta = deepcopy(DEFAULT_TOOL_META.get(name, {}))
    if name.startswith("mcp__"):
        parts = name.split("__", 2)
        server = parts[1] if len(parts) > 1 else "unknown"
        meta.setdefault("category", "mcp")
        meta.setdefault("server", server)
        meta.setdefault("risk", "medium")
    meta.setdefault("category", "other")
    meta.setdefault("risk", "medium")
    if tool_def:
        meta["description"] = tool_def.get("description", "")
    return meta


def _profile_allows(name: str, meta: dict[str, Any], profile: dict[str, Any]) -> bool:
    categories = set(profile.get("categories", []))
    tools = set(profile.get("tools", []))
    disabled = set(profile.get("disabled", []))
    category = meta.get("category", "other")

    if name in CONTROL_TOOLS:
        return True
    if name in disabled:
        return False
    if name in tools:
        return True
    if "*" in categories:
        return True
    return category in categories


def is_tool_enabled(name: str, tool_def: dict | None = None, profile_name: str | None = None) -> bool:
    state = load_tool_state()
    active_profile = profile_name or state["activeProfile"]
    profile = state["profiles"].get(active_profile, state["profiles"]["coding"])
    override = state.get("tools", {}).get(name, {}).get("enabled")
    if override is not None:
        return bool(override) or name in CONTROL_TOOLS
    return _profile_allows(name, tool_meta(name, tool_def), profile)


def filter_tools_and_handlers(tools: list[dict], handlers: dict[str, Any]) -> tuple[list[dict], dict[str, Any]]:
    enabled_tools = []
    enabled_handlers = {}
    for tool_def in tools:
        name = tool_def["name"]
        if is_tool_enabled(name, tool_def):
            enabled_tools.append(tool_def)
            if name in handlers:
                enabled_handlers[name] = handlers[name]
    return enabled_tools, enabled_handlers


def list_tool_status(tool_defs: list[dict] | None = None) -> str:
    state = load_tool_state()
    active = state["activeProfile"]
    lines = [
        f"Active profile: {active}",
        "Profiles:",
    ]
    for name, profile in state["profiles"].items():
        marker = "*" if name == active else " "
        lines.append(f"  {marker} {name}: {profile.get('description', '')}")

    if tool_defs is None:
        return "\n".join(lines)

    rows = []
    for tool_def in tool_defs:
        name = tool_def["name"]
        meta = tool_meta(name, tool_def)
        status = "on" if is_tool_enabled(name, tool_def) else "off"
        rows.append((status, meta["category"], meta["risk"], name))
    rows.sort(key=lambda item: (item[0] != "on", item[1], item[3]))

    lines.extend(["", "Tools:"])
    for status, category, risk, name in rows:
        lines.append(f"  {status:3} {category:10} {risk:6} {name}")
    return "\n".join(lines)


def set_tool_enabled(name: str, enabled: bool) -> str:
    state = load_tool_state()
    state.setdefault("tools", {}).setdefault(name, {})["enabled"] = enabled
    save_tool_state(state)
    return f"Tool '{name}' is now {'enabled' if enabled else 'disabled'}."


def set_active_profile(name: str | None = None) -> str:
    state = load_tool_state()
    if not name:
        return list_tool_status()
    if name not in state["profiles"]:
        return f"Unknown profile '{name}'. Available: {', '.join(state['profiles'].keys())}"
    state["activeProfile"] = name
    save_tool_state(state)
    return f"Active tool profile set to '{name}'."


def reload_tools() -> str:
    state = load_tool_state()
    return f"Reloaded tool config from {CONFIG_PATH} (active profile: {state['activeProfile']})."


def prompt_tool_summary() -> str:
    state = load_tool_state()
    profile = state["profiles"].get(state["activeProfile"], {})
    categories = ", ".join(profile.get("categories", [])) or "(none)"
    explicit = ", ".join(profile.get("tools", [])) or "(none)"
    disabled = ", ".join(profile.get("disabled", [])) or "(none)"
    return (
        f"Tool profile: {state['activeProfile']}\n"
        f"Enabled categories: {categories}\n"
        f"Explicit tools: {explicit}\n"
        f"Profile-disabled tools: {disabled}\n"
        "Control tools: tool_status, tool_enable, tool_disable, tool_profile, tool_reload."
    )
