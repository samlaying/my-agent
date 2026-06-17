"""context.system_prompt — 运行时动态组装"""

from datetime import datetime
from agents.profile import DEFAULT_PROFILE, AgentProfile
from core.config import WORKDIR
from core.state import mcp_clients
from plugins.skills import list_skills
from tools.registry import prompt_tool_summary


def _reminder_guidance() -> str:
    return """Reminder system (全屏提醒):
- create_reminder(message, cron, snooze_min=30, enabled=true) — Beijing time cron. Examples:
  - 每30分钟喝水: create_reminder("💧 喝水", "*/30 * * * *")
  - 工作日10/14/17点站起来: create_reminder("🚶 站起来", "0 10,14,17 * * 1-5")
  - 每小时休息: create_reminder("👀 休息眼睛", "0 * * * *")
- list_reminders — 查看所有提醒及状态
- manage_reminder(action, rem_id?, minutes?): enable | disable | snooze | delete | disable_today | enable_all
  - disable_today(rem_id) — 今天不再提醒（午夜自动恢复）
  - enable_all — 重新启用所有提醒
- 用户可能说"今天不开了"/"关掉提醒"/"现在开始提醒"/"看看我有哪些提醒"，对应上述工具
- 提醒触发时全屏白屏覆盖，用户点"好的"进入30秒倒计时，点"稍后"可选30分钟/1小时/2小时/今天不再提醒
- 5秒无操作自动进入倒计时"""


def assemble_system_prompt(context: dict, profile: AgentProfile | None = None) -> str:
    active_profile = profile or DEFAULT_PROFILE
    sections = [
        f"Agent profile: {active_profile.id}",
        active_profile.soul,
        prompt_tool_summary(active_profile.tool_profile),
        f"Working directory: {WORKDIR}",
        f"Current time: {datetime.now().isoformat(timespec='seconds')}",
        "Skills catalog:\n" + list_skills() + "\nUse load_skill(name) when relevant.",
        _reminder_guidance(),
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
