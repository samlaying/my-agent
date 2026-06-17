"""Tool execution boundary."""

from __future__ import annotations

import time
from typing import Any, Callable

from tools.builtin import call_tool_handler


class ToolExecutor:
    def __init__(
        self,
        handlers: dict[str, Callable[..., str]],
        pre_hook: Callable[[Any], str | None] | None = None,
        post_hook: Callable[[Any, str], Any] | None = None,
        logger: Callable[[str, dict, str, float, bool], Any] | None = None,
    ):
        self.handlers = handlers
        self.pre_hook = pre_hook
        self.post_hook = post_hook
        self.logger = logger

    def execute(self, block) -> dict:
        blocked = self.pre_hook(block) if self.pre_hook else None
        if blocked:
            output = str(blocked)
            if self.logger:
                self.logger(block.name, block.input, output, 0, True)
            return {"type": "tool_result", "tool_use_id": block.id, "content": output}

        started = time.time()
        handler = self.handlers.get(block.name)
        output = call_tool_handler(handler, block.input, block.name)
        latency_ms = (time.time() - started) * 1000

        if self.logger:
            self.logger(block.name, block.input, output, latency_ms, False)
        if self.post_hook:
            self.post_hook(block, output)
        return {"type": "tool_result", "tool_use_id": block.id, "content": output}
