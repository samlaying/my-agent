"""agents.loop — agent 主循环 + cron 自动运行"""

import json
import time
import threading

from core.config import (DEFAULT_MAX_TOKENS, ESCALATED_MAX_TOKENS, CONTINUATION_PROMPT,
                         CONTEXT_LIMIT, client)
from core.state import rounds_since_todo
from tools.dispatch import assemble_tool_pool
from tools.hooks import trigger_hooks
from tools.builtin import call_tool_handler
from context.compaction import (tool_result_budget, snip_compact, micro_compact,
                                estimate_size, compact_history, reactive_compact)
from context.system_prompt import assemble_system_prompt
from context.memory import update_context
from agents.recovery import RecoveryState, with_retry, is_prompt_too_long_error
from teams.background import should_run_background, start_background_task, collect_background_results
from scheduler.cron import consume_cron_queue
from tracing.turn_logger import log_llm_response, log_tool_execution, log_error
from utils.terminal import terminal_print


def _has_tool_use(content) -> bool:
    return any(getattr(b, "type", None) == "tool_use" for b in content)


agent_lock = threading.Lock()


def prepare_context(messages: list) -> list:
    messages[:] = tool_result_budget(messages)
    messages[:] = snip_compact(messages)
    messages[:] = micro_compact(messages)
    if estimate_size(messages) > CONTEXT_LIMIT:
        messages[:] = compact_history(messages)
    return messages


def build_user_content(results: list[dict]) -> list[dict]:
    content = [{"type": "text", "text": n} for n in collect_background_results()]
    content.extend(results)
    return content


def inject_background_notifications(messages: list):
    notes = collect_background_results()
    if notes:
        messages.append({"role": "user", "content": [{"type": "text", "text": n} for n in notes]})


def call_llm(messages: list, context: dict, tools: list, state, max_tokens: int):
    system = assemble_system_prompt(context)
    return with_retry(
        lambda: client.messages.create(model=state.current_model, system=system,
                                       messages=messages, tools=tools, max_tokens=max_tokens),
        state)


def agent_loop(messages: list, context: dict):
    global rounds_since_todo
    tools, handlers = assemble_tool_pool()
    state = RecoveryState()
    max_tokens = DEFAULT_MAX_TOKENS

    while True:
        for job in consume_cron_queue():
            messages.append({"role": "user", "content": f"[Scheduled] {job.prompt}"})
            terminal_print(f"  \033[35m[cron inject] {job.prompt[:60]}\033[0m")

        inject_background_notifications(messages)
        if rounds_since_todo >= 3:
            messages.append({"role": "user", "content": "<reminder>Update your todos.</reminder>"})
            rounds_since_todo = 0

        prepare_context(messages)
        context = update_context(context, messages)
        tools, handlers = assemble_tool_pool()

        t0 = time.time()
        try:
            response = call_llm(messages, context, tools, state, max_tokens)
        except Exception as e:
            log_error(type(e).__name__, str(e))
            if is_prompt_too_long_error(e) and not state.has_attempted_reactive_compact:
                messages[:] = reactive_compact(messages)
                state.has_attempted_reactive_compact = True
                continue
            messages.append({"role": "assistant", "content": [{"type": "text", "text": f"[Error] {type(e).__name__}: {e}"}]})
            return
        latency_ms = (time.time() - t0) * 1000

        if response.stop_reason == "max_tokens":
            if not state.has_escalated:
                max_tokens = ESCALATED_MAX_TOKENS; state.has_escalated = True; continue
            messages.append({"role": "assistant", "content": response.content})
            if state.recovery_count < 2:
                messages.append({"role": "user", "content": CONTINUATION_PROMPT})
                state.recovery_count += 1; continue
            return

        max_tokens = DEFAULT_MAX_TOKENS; state.has_escalated = False
        messages.append({"role": "assistant", "content": response.content})

        _tool_calls = [{"name": b.name, "input_preview": json.dumps(b.input, ensure_ascii=False)[:150]}
                       for b in response.content if b.type == "tool_use"]
        _text = "\n".join(getattr(b, "text", "") for b in response.content if getattr(b, "type", None) == "text")
        log_llm_response(response.stop_reason, _text, _tool_calls, latency_ms)

        if not _has_tool_use(response.content):
            trigger_hooks("Stop", messages); return

        results = []; compacted_now = False
        for block in response.content:
            if block.type != "tool_use": continue
            terminal_print(f"\033[36m> {block.name}\033[0m")

            if block.name == "compact":
                messages[:] = compact_history(messages)
                messages.append({"role": "user", "content": "[Compacted. Continue.]"})
                log_tool_execution("compact", {}, "[compacted]", (time.time() - t0) * 1000)
                compacted_now = True; break

            blocked = trigger_hooks("PreToolUse", block)
            if blocked:
                log_tool_execution(block.name, block.input, str(blocked), 0, blocked=True)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(blocked)})
                continue

            if should_run_background(block.name, block.input):
                bg_id = start_background_task(block, handlers)
                log_tool_execution(block.name, block.input, f"[bg:{bg_id}]", 0)
                results.append({"type": "tool_result", "tool_use_id": block.id,
                                "content": f"[Background task {bg_id} started.]"})
                continue

            t_tool = time.time()
            handler = handlers.get(block.name)
            output = call_tool_handler(handler, block.input, block.name)
            tool_latency = (time.time() - t_tool) * 1000
            log_tool_execution(block.name, block.input, output, tool_latency)
            trigger_hooks("PostToolUse", block, output)
            terminal_print(str(output)[:300])

            if block.name == "todo_write": rounds_since_todo = 0
            else: rounds_since_todo += 1
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})

        if compacted_now: continue
        messages.append({"role": "user", "content": build_user_content(results)})


def print_turn_assistants(messages: list, turn_start: int):
    for msg in messages[turn_start:]:
        if msg.get("role") != "assistant": continue
        for block in msg.get("content", []):
            if getattr(block, "type", None) == "text": terminal_print(block.text)


def cron_autorun_loop(history: list, context: dict):
    while True:
        time.sleep(1)
        fired = consume_cron_queue()
        if not fired: continue
        with agent_lock:
            turn_start = len(history)
            for job in fired:
                history.append({"role": "user", "content": f"[Scheduled] {job.prompt}"})
                terminal_print(f"  \033[35m[cron auto] {job.prompt[:60]}\033[0m")
            agent_loop(history, context)
            context.update(update_context(context, history))
            print_turn_assistants(history, turn_start)
