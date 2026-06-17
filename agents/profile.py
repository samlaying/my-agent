"""Agent profile contracts.

A profile is the scene-specific part of an agent. The runtime stays shared;
the profile supplies soul, skills, tool set, triggers, and memory policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MemoryPolicy:
    namespaces: list[str] = field(default_factory=lambda: ["global"])
    max_chars: int = 2000
    query_recent_messages: int = 6


@dataclass(frozen=True)
class Trigger:
    type: str
    value: str = ""
    prompt: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class AgentProfile:
    id: str = "common"
    soul: str = "You are a helpful agent. Act, don't explain unless explanation is useful."
    skills: list[str] = field(default_factory=list)
    tool_profile: str = "coding"
    memory: MemoryPolicy = field(default_factory=MemoryPolicy)
    permissions: dict[str, str] = field(default_factory=dict)
    triggers: list[Trigger] = field(default_factory=list)


DEFAULT_PROFILE = AgentProfile()


def _coerce_memory(raw: dict[str, Any] | None) -> MemoryPolicy:
    if not raw:
        return MemoryPolicy()
    return MemoryPolicy(
        namespaces=list(raw.get("namespaces", ["global"])),
        max_chars=int(raw.get("max_chars", raw.get("maxChars", 2000))),
        query_recent_messages=int(raw.get("query_recent_messages", raw.get("queryRecentMessages", 6))),
    )


def _coerce_triggers(raw: list[dict[str, Any]] | None) -> list[Trigger]:
    return [
        Trigger(
            type=str(item.get("type", "")),
            value=str(item.get("value", item.get("cron", ""))),
            prompt=str(item.get("prompt", "")),
            enabled=bool(item.get("enabled", True)),
        )
        for item in (raw or [])
        if isinstance(item, dict)
    ]


def profile_from_dict(data: dict[str, Any]) -> AgentProfile:
    return AgentProfile(
        id=str(data.get("id", "common")),
        soul=str(data.get("soul", DEFAULT_PROFILE.soul)),
        skills=list(data.get("skills", [])),
        tool_profile=str(data.get("tool_profile", data.get("toolProfile", "coding"))),
        memory=_coerce_memory(data.get("memory")),
        permissions=dict(data.get("permissions", {})),
        triggers=_coerce_triggers(data.get("triggers")),
    )


def load_profile(path: str | Path) -> AgentProfile:
    """Load a profile from JSON.

    YAML can be added later, but JSON keeps the first contract dependency-free.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Agent profile must be a JSON object")
    return profile_from_dict(data)
