"""Shared runtime atoms for all agent profiles."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import core.config as cfg
from agents.profile import DEFAULT_PROFILE, AgentProfile
from agents.recovery import with_retry
from context.memory import update_context
from context.system_prompt import assemble_system_prompt
from scheduler.cron import consume_cron_queue
from teams.background import collect_background_results


@dataclass
class RuntimeSession:
    messages: list
    context: dict = field(default_factory=dict)
    profile: AgentProfile = field(default_factory=lambda: DEFAULT_PROFILE)


class ContextBuilder:
    def build(self, session: RuntimeSession) -> dict:
        session.context = update_context(session.context, session.messages, session.profile)
        return session.context


class LLMGateway:
    def call(self, session: RuntimeSession, tools: list, state: Any, max_tokens: int):
        system = assemble_system_prompt(session.context, profile=session.profile)
        # OpenAI 兼容协议分支（Ollama 等）
        if cfg._current_provider.get("protocol") == "openai":
            return with_retry(
                lambda: self._call_openai(
                    cfg.client, session, tools, max_tokens, system,
                    model=cfg._current_provider.get("model_id", "default"),
                ),
                state,
            )
        # Anthropic 协议（默认）
        return with_retry(
            lambda: cfg.client.messages.create(
                model=state.current_model,
                system=system,
                messages=session.messages,
                tools=tools,
                max_tokens=max_tokens,
            ),
            state,
        )

    def _call_openai(self, client, session, tools, max_tokens, system, model="default"):
        """OpenAI 兼容协议调用（Ollama 等），返回 Anthropic 兼容响应对象"""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        for msg in session.messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                parts = []
                for block in content:
                    if hasattr(block, "text"):
                        parts.append(block.text)
                    elif isinstance(block, dict) and "text" in block:
                        parts.append(block["text"])
                content = "\n".join(parts)
            messages.append({"role": role, "content": content})

        openai_tools = []
        for t in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t.get("description", ""),
                    "parameters": t.get("input_schema", {}),
                },
            })

        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=openai_tools if openai_tools else None,
            max_tokens=max_tokens,
        )

        # 转换为与 Anthropic response 兼容的结构
        content_blocks = []
        choice = resp.choices[0]
        if choice.message.content:
            content_blocks.append(SimpleNamespace(type="text", text=choice.message.content))
        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                content_blocks.append(SimpleNamespace(
                    type="tool_use",
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments),
                ))
        return SimpleNamespace(
            content=content_blocks,
            stop_reason="end_turn" if choice.finish_reason == "stop" else choice.finish_reason,
        )


class SchedulerBridge:
    def inject_due_jobs(self, session: RuntimeSession) -> list:
        jobs = consume_cron_queue()
        for job in jobs:
            session.messages.append({"role": "user", "content": f"[Scheduled] {job.prompt}"})
        return jobs


class OutputCollector:
    def build_user_content(self, results: list[dict]) -> list[dict]:
        content = [{"type": "text", "text": n} for n in collect_background_results()]
        content.extend(results)
        return content

    def inject_background_notifications(self, session: RuntimeSession) -> list[str]:
        notes = collect_background_results()
        if notes:
            session.messages.append({"role": "user", "content": [{"type": "text", "text": n} for n in notes]})
        return notes
