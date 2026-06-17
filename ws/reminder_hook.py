"""ws.reminder_hook — 提醒触发时推送到前端（全屏 overlay）"""

from ws.protocol import make_msg, MSG_REMINDER

_ws_server = None


def init(server):
    global _ws_server
    _ws_server = server


def on_reminder_fired(reminder):
    """reminders.manager 调用此函数。ws_server 为 None 时跳过。"""
    if _ws_server:
        _ws_server.send_sync(make_msg(MSG_REMINDER, {
            "id": reminder.id,
            "message": reminder.message,
            "snooze_min": reminder.snooze_min,
        }))
