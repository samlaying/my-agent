"""ws.bubble — 气泡消息发送"""

from ws.protocol import make_msg, MSG_BUBBLE, BUBBLE_MESSAGE

_ws_server = None  # 由 agent_server.py 注入


def init(server):
    global _ws_server
    _ws_server = server


def send_bubble(text: str, kind: str = BUBBLE_MESSAGE, duration: int = 0):
    """推送到前端的气泡。duration=0 表示常驻。"""
    if _ws_server:
        _ws_server.send_sync(make_msg(MSG_BUBBLE, {
            "text": text, "kind": kind, "duration": duration,
        }))
