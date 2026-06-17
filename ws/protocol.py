"""ws.protocol — WebSocket 消息类型常量与构建器"""

# ── 消息类型（Server → Client）──
MSG_ASSISTANT_TEXT = "assistant_text"  # {text: str}
MSG_BUBBLE = "bubble"                  # {text, kind, duration}
MSG_MOOD = "mood"                      # {mood, detail}
MSG_TOOL_ACTIVITY = "tool_activity"    # {tool, status}
MSG_REMINDER = "reminder"              # {id, message, snooze_min}
MSG_PONG = "pong"                      # {}

# ── 消息类型（Client → Server）──
MSG_USER_MESSAGE = "user_message"      # {text: str}
MSG_SNOOZE = "snooze"                  # {id, minutes}
MSG_PING = "ping"                      # {}

# ── 气泡种类 ──
BUBBLE_MESSAGE = "message"
BUBBLE_CRON = "cron"
BUBBLE_STATUS = "status"
BUBBLE_ERROR = "error"
BUBBLE_USER = "user"

# ── 情绪 ──
MOODS = ("idle", "thinking", "happy", "sad", "alert")


def make_msg(msg_type: str, data: dict) -> dict:
    """构建标准消息 envelope"""
    return {"type": msg_type, "data": data}
