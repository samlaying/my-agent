"""context.system_prompt — 运行时动态组装"""

from datetime import datetime
from core.config import WORKDIR
from core.state import mcp_clients
from plugins.skills import list_skills


def assemble_system_prompt(context: dict) -> str:
    sections = [
        "You are a coding agent. Act, don't explain. Use tools to complete tasks.",
        ("Available tools: bash, read_file, write_file, edit_file, glob, "
         "todo_write, task, load_skill, compact, "
         "create_task, list_tasks, get_task, claim_task, complete_task, "
         "schedule_cron, list_crons, cancel_cron, "
         "spawn_teammate, send_message, check_inbox, "
         "request_shutdown, request_plan, review_plan, "
         "create_worktree, remove_worktree, keep_worktree, "
         "connect_mcp. MCP tools: mcp__{server}__{tool}."),
        f"Working directory: {WORKDIR}",
        f"Current time: {datetime.now().isoformat(timespec='seconds')}",
        "Skills catalog:\n" + list_skills() + "\nUse load_skill(name) when relevant.",
    ]
    if context.get("memories"):
        sections.append(f"Relevant memories:\n{context['memories']}")
    names = list(mcp_clients.keys())
    if names:
        sections.append(f"Connected MCP servers: {', '.join(names)}")
    return "\n\n".join(sections)
