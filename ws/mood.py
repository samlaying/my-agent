"""ws.mood — 情绪状态管理"""

from ws.protocol import MOODS, make_msg, MSG_MOOD

_ws_server = None  # 由 agent_server.py 注入
_current = {"mood": "idle", "detail": ""}


def init(server):
    """注入 WS server 实例"""
    global _ws_server
    _ws_server = server


def set_mood(mood: str, detail: str = "") -> str:
    """设置情绪并推送到前端。返回确认文本。"""
    _current["mood"] = mood if mood in MOODS else "idle"
    _current["detail"] = detail
    if _ws_server:
        _ws_server.send_sync(make_msg(MSG_MOOD, _current.copy()))
    return f"Mood → {mood}"


def get_mood() -> dict:
    return _current.copy()


def infer_mood(history: list) -> str:
    """从最后一条 assistant 消息启发式推断情绪"""
    if not history:
        return "idle"
    last = history[-1]
    if last.get("role") != "assistant":
        return "idle"

    text = ""
    for block in last.get("content", []):
        if hasattr(block, "text"):
            text += block.text
        elif isinstance(block, dict) and "text" in block:
            text += block["text"]

    t = text.lower()
    if any(w in t for w in ["error", "failed", "sorry", "cannot", "unable"]):
        return "sad"
    if any(w in t for w in ["done", "completed", "success", "great", "finished"]):
        return "happy"
    if any(w in t for w in ["warning", "attention", "careful", "note"]):
        return "alert"
    return "idle"
