"""Tool contracts shared by registries and executors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


ToolHandler = Callable[..., str]


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler | None = None
    output_schema: dict[str, Any] = field(default_factory=dict)
    category: str = "other"
    risk: str = "medium"
    permissions: dict[str, str] = field(default_factory=dict)

    def to_anthropic_tool(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
