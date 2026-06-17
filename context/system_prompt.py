"""context.system_prompt — 运行时动态组装"""

from datetime import datetime
from agents.profile import DEFAULT_PROFILE, AgentProfile
from core.config import WORKDIR
from core.state import mcp_clients
from plugins.skills import list_skills
from tools.registry import prompt_tool_summary


def assemble_system_prompt(context: dict, profile: AgentProfile | None = None) -> str:
    active_profile = profile or DEFAULT_PROFILE
    sections = [
        f"Agent profile: {active_profile.id}",
        active_profile.soul,
        prompt_tool_summary(active_profile.tool_profile),
        f"Working directory: {WORKDIR}",
        f"Current time: {datetime.now().isoformat(timespec='seconds')}",
        "Skills catalog:\n" + list_skills() + "\nUse load_skill(name) when relevant.",
    ]
    if active_profile.skills:
        sections.append("Required skills: " + ", ".join(active_profile.skills))
    if active_profile.memory.namespaces:
        sections.append("Memory namespaces: " + ", ".join(active_profile.memory.namespaces))
    if active_profile.permissions:
        permissions = "\n".join(f"- {k}: {v}" for k, v in sorted(active_profile.permissions.items()))
        sections.append("Permission policy:\n" + permissions)
    if context.get("memories"):
        sections.append(f"Relevant memories:\n{context['memories']}")
    names = list(mcp_clients.keys())
    if names:
        sections.append(f"Connected MCP servers: {', '.join(names)}")
    return "\n\n".join(sections)
