"""ws.output — terminal_print 替代品，输出到终端 + WS"""

from ws.protocol import make_msg, MSG_ASSISTANT_TEXT

_ws_server = None  # 由 agent_server.py 注入


def init(server):
    global _ws_server
    _ws_server = server


def ws_print(text: str):
    """替代 utils.terminal.terminal_print，同时推送到 WS"""
    print(text)  # 终端仍保留输出
    if _ws_server:
        _ws_server.send_sync(make_msg(MSG_ASSISTANT_TEXT, {"text": str(text)}))
