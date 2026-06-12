"""teams.background — 后台任务管理"""

import threading
import core.state as state
from tools.builtin import call_tool_handler
from tools.hooks import trigger_hooks
from utils.terminal import terminal_print

def is_slow_operation(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "bash": return False
    command = tool_input.get("command", "").lower()
    return any(k in command for k in ["install", "build", "test", "deploy", "compile", "pytest", "make"])

def should_run_background(tool_name: str, tool_input: dict) -> bool:
    if tool_name != "bash": return False
    return bool(tool_input.get("run_in_background")) or is_slow_operation(tool_name, tool_input)

def start_background_task(block, handlers: dict) -> str:
    state._bg_counter += 1
    bg_id = f"bg_{state._bg_counter:04d}"
    command = block.input.get("command", block.name)
    def worker():
        handler = handlers.get(block.name)
        result = call_tool_handler(handler, block.input, block.name)
        trigger_hooks("PostToolUse", block, result)
        state.background_tasks[bg_id]["status"] = "completed"
        state.background_results[bg_id] = str(result)
    state.background_tasks[bg_id] = {"tool_use_id": block.id, "command": command, "status": "running"}
    threading.Thread(target=worker, daemon=True).start()
    terminal_print(f"  \033[33m[background] {bg_id}: {str(command)[:60]}\033[0m")
    return bg_id

def collect_background_results() -> list[str]:
    ready = [bg_id for bg_id, task in state.background_tasks.items() if task["status"] == "completed"]
    notifications = []
    for bg_id in ready:
        task = state.background_tasks.pop(bg_id)
        output = state.background_results.pop(bg_id, "")
        notifications.append(
            f"<task_notification>\n  <task_id>{bg_id}</task_id>\n  <status>completed</status>\n"
            f"  <command>{task['command']}</command>\n  <summary>{output[:200]}</summary>\n</task_notification>")
    return notifications
