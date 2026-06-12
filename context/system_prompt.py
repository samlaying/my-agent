"""context.system_prompt — 运行时动态组装"""

from datetime import datetime
from core.config import WORKDIR
from core.state import mcp_clients
from plugins.skills import list_skills
from tools.registry import prompt_tool_summary


def assemble_system_prompt(context: dict) -> str:
    sections = [
        "You are a coding agent. Act, don't explain. Use tools to complete tasks.",
        prompt_tool_summary(),
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
