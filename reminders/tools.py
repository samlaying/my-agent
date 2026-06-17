"""reminders.tools — Agent 工具 handler"""

from reminders.manager import (
    create_reminder, list_reminders, get_reminder,
    toggle_reminder, delete_reminder, snooze_reminder,
    disable_today, enable_all,
)


def run_create_reminder(message: str, cron: str, snooze_min: int = 30, enabled: bool = True) -> str:
    r = create_reminder(message, cron, snooze_min, enabled)
    if isinstance(r, str):
        return f"Error: {r}"
    return f"Created {r.id}: '{r.message}' cron='{r.cron}' snooze={r.snooze_min}min"


def run_list_reminders() -> str:
    rems = list_reminders()
    if not rems:
        return "No reminders."
    lines = []
    for r in rems:
        status = "✅" if r.enabled else "⏸️"
        lines.append(f"  {status} {r.id}: '{r.message}' cron='{r.cron}' snooze={r.snooze_min}min")
    return "\n".join(lines)


def run_manage_reminder(action: str, rem_id: str = "", minutes: int | None = None) -> str:
    if action == "delete":
        return delete_reminder(rem_id)
    elif action == "enable":
        r = toggle_reminder(rem_id, True)
        return f"Enabled {rem_id}" if not isinstance(r, str) else r
    elif action == "disable":
        r = toggle_reminder(rem_id, False)
        return f"Disabled {rem_id}" if not isinstance(r, str) else r
    elif action == "snooze":
        return snooze_reminder(rem_id, minutes)
    elif action == "disable_today":
        return disable_today(rem_id if rem_id else None)
    elif action == "enable_all":
        return enable_all()
    else:
        return f"Error: Unknown action '{action}'. Use: delete, enable, disable, snooze, disable_today, enable_all"
