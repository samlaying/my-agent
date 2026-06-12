"""tools.dispatch — 工具 schema + handler 注册表 + 工具池组装"""

from core.state import mcp_clients
from plugins.mcp import normalize_mcp_name
from tools.registry import (filter_tools_and_handlers, list_tool_status, reload_tools,
                            set_active_profile, set_tool_enabled)

BUILTIN_TOOLS = [
    {"name": "bash", "description": "Run a shell command.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}, "run_in_background": {"type": "boolean"}}, "required": ["command"]}},
    {"name": "read_file", "description": "Read file contents.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "limit": {"type": "integer"}, "offset": {"type": "integer"}}, "required": ["path"]}},
    {"name": "write_file", "description": "Write content to a file.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "edit_file", "description": "Replace exact text.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}}, "required": ["path", "old_text", "new_text"]}},
    {"name": "glob", "description": "Find files.", "input_schema": {"type": "object", "properties": {"pattern": {"type": "string"}}, "required": ["pattern"]}},
    {"name": "todo_write", "description": "Update todo list.", "input_schema": {"type": "object", "properties": {"todos": {"type": "array", "items": {"type": "object", "properties": {"content": {"type": "string"}, "status": {"type": "string", "enum": ["pending", "in_progress", "completed"]}}, "required": ["content", "status"]}}}, "required": ["todos"]}},
    {"name": "task", "description": "Launch a subagent.", "input_schema": {"type": "object", "properties": {"description": {"type": "string"}}, "required": ["description"]}},
    {"name": "load_skill", "description": "Load skill by name.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "compact", "description": "Compress context.", "input_schema": {"type": "object", "properties": {"focus": {"type": "string"}}, "required": []}},
    {"name": "create_task", "description": "Create a task.", "input_schema": {"type": "object", "properties": {"subject": {"type": "string"}, "description": {"type": "string"}, "blockedBy": {"type": "array", "items": {"type": "string"}}}, "required": ["subject"]}},
    {"name": "list_tasks", "description": "List all tasks.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "get_task", "description": "Get task details.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "claim_task", "description": "Claim a pending task.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "complete_task", "description": "Complete a task.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "schedule_cron", "description": "Schedule cron (5-field).", "input_schema": {"type": "object", "properties": {"cron": {"type": "string"}, "prompt": {"type": "string"}, "recurring": {"type": "boolean"}, "durable": {"type": "boolean"}}, "required": ["cron", "prompt"]}},
    {"name": "list_crons", "description": "List cron jobs.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "cancel_cron", "description": "Cancel cron.", "input_schema": {"type": "object", "properties": {"job_id": {"type": "string"}}, "required": ["job_id"]}},
    {"name": "spawn_teammate", "description": "Spawn teammate.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "role": {"type": "string"}, "prompt": {"type": "string"}}, "required": ["name", "role", "prompt"]}},
    {"name": "send_message", "description": "Send message.", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}}, "required": ["to", "content"]}},
    {"name": "check_inbox", "description": "Check inbox.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "request_shutdown", "description": "Request shutdown.", "input_schema": {"type": "object", "properties": {"teammate": {"type": "string"}}, "required": ["teammate"]}},
    {"name": "request_plan", "description": "Request plan.", "input_schema": {"type": "object", "properties": {"teammate": {"type": "string"}, "task": {"type": "string"}}, "required": ["teammate", "task"]}},
    {"name": "review_plan", "description": "Review plan.", "input_schema": {"type": "object", "properties": {"request_id": {"type": "string"}, "approve": {"type": "boolean"}, "feedback": {"type": "string"}}, "required": ["request_id", "approve"]}},
    {"name": "create_worktree", "description": "Create worktree.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "task_id": {"type": "string"}}, "required": ["name"]}},
    {"name": "remove_worktree", "description": "Remove worktree.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "discard_changes": {"type": "boolean"}}, "required": ["name"]}},
    {"name": "keep_worktree", "description": "Keep worktree.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "connect_mcp", "description": "Connect MCP server.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    # ── Tool control plane ──
    {"name": "tool_status", "description": "Show active tool profile and enabled/disabled tools.", "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "tool_enable", "description": "Enable a tool by name in the local tool config.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "tool_disable", "description": "Disable a tool by name in the local tool config.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "tool_profile", "description": "List profiles or switch active tool profile.", "input_schema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": []}},
    {"name": "tool_reload", "description": "Reload local tool configuration.", "input_schema": {"type": "object", "properties": {}, "required": []}},
]

_handler_registry: dict[str, callable] = {}

def register_handler(name: str, handler: callable):
    _handler_registry[name] = handler

def get_handler(name: str) -> callable | None:
    return _handler_registry.get(name)

def register_all_handlers():
    from tools.builtin import run_bash, run_read, run_write, run_edit, run_glob, run_todo_write
    from tasks.task import run_create_task, run_list_tasks, run_get_task, run_claim_task, run_complete_task
    from scheduler.cron import run_schedule_cron, run_list_crons, run_cancel_cron
    from agents.subagent import spawn_subagent
    from agents.teammate import spawn_teammate_thread
    from teams.protocol import run_request_shutdown, run_request_plan, run_review_plan
    from teams.bus import run_send_message, run_check_inbox
    from tasks.worktree import create_worktree, remove_worktree, keep_worktree
    from plugins.skills import load_skill
    from plugins.mcp import connect_mcp
    for name, handler in [
        ("bash", run_bash), ("read_file", run_read), ("write_file", run_write),
        ("edit_file", run_edit), ("glob", run_glob), ("todo_write", run_todo_write),
        ("task", spawn_subagent), ("load_skill", load_skill),
        ("create_task", run_create_task), ("list_tasks", run_list_tasks),
        ("get_task", run_get_task), ("claim_task", run_claim_task),
        ("complete_task", run_complete_task),
        ("schedule_cron", run_schedule_cron), ("list_crons", run_list_crons),
        ("cancel_cron", run_cancel_cron),
        ("spawn_teammate", spawn_teammate_thread),
        ("send_message", run_send_message), ("check_inbox", run_check_inbox),
        ("request_shutdown", run_request_shutdown),
        ("request_plan", run_request_plan), ("review_plan", run_review_plan),
        ("create_worktree", lambda name, task_id="": create_worktree(name, task_id)),
        ("remove_worktree", lambda name, discard_changes=False: remove_worktree(name, discard_changes)),
        ("keep_worktree", keep_worktree), ("connect_mcp", connect_mcp),
        ("tool_status", lambda: list_tool_status(_assemble_raw_tool_pool()[0])),
        ("tool_enable", lambda name: set_tool_enabled(name, True)),
        ("tool_disable", lambda name: set_tool_enabled(name, False)),
        ("tool_profile", lambda name=None: set_active_profile(name)),
        ("tool_reload", reload_tools),
    ]:
        register_handler(name, handler)

def _assemble_raw_tool_pool() -> tuple[list[dict], dict]:
    tools = list(BUILTIN_TOOLS)
    handlers = dict(_handler_registry)
    for server_name, mcp_client in mcp_clients.items():
        safe_server = normalize_mcp_name(server_name)
        for tool_def in mcp_client.tools:
            safe_tool = normalize_mcp_name(tool_def["name"])
            prefixed = f"mcp__{safe_server}__{safe_tool}"
            tools.append({"name": prefixed, "description": tool_def.get("description", ""),
                          "input_schema": tool_def.get("inputSchema", {})})
            handlers[prefixed] = lambda *, c=mcp_client, t=tool_def["name"], **kw: c.call_tool(t, kw)
    return tools, handlers

def assemble_all_tool_pool() -> tuple[list[dict], dict]:
    return _assemble_raw_tool_pool()

def assemble_tool_pool() -> tuple[list[dict], dict]:
    return filter_tools_and_handlers(*_assemble_raw_tool_pool())
