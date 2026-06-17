#!/usr/bin/env python3
"""agent_server.py — 带 WebSocket 的 agent 入口

Run: python3 agent_server.py
原有 REPL: python3 agent.py（不受影响）
"""

import threading
import time

# ── 注册工具 handler（同 agent.py）──
from tools.dispatch import register_all_handlers, assemble_tool_pool
register_all_handlers()

import core.config as cfg
from core.config import WORKDIR
from core.state import CLI_ACTIVE
from tracing.turn_logger import log_session_start, log_user_input
from tools.hooks import trigger_hooks
from agents.loop import agent_loop, cron_autorun_loop, agent_lock
from context.memory import update_context

# ── WS 模块 ──
from ws.server import WSServer
from ws.mood import init as mood_init, set_mood, infer_mood
from ws.bubble import init as bubble_init, send_bubble
from ws.output import init as output_init, ws_print
from ws.protocol import BUBBLE_STATUS, MSG_SNOOZE
from ws.reminder_hook import init as reminder_hook_init, on_reminder_fired

# ── 消息队列（WS → agent 主循环）──
message_queue: list[str] = []
queue_lock = threading.Lock()
ws_server: WSServer = None  # 由 main() 注入


async def on_ws_message(msg: dict, websocket):
    """WS 消息回调"""
    msg_type = msg.get("type")
    if msg_type == "user_message":
        text = msg.get("data", {}).get("text", "")
        if text:
            with queue_lock:
                message_queue.append(text)
    elif msg_type == "snooze":
        data = msg.get("data", {})
        rem_id = data.get("id", "")
        minutes = data.get("minutes")
        if rem_id:
            from reminders.manager import snooze_reminder, disable_today
            if minutes == "today":
                result = disable_today(rem_id)
            else:
                result = snooze_reminder(rem_id, minutes)
            print(f"[reminder] {result}")
    else:
        # 其他消息类型（bubble/reminder 等）广播给所有客户端
        await ws_server.broadcast(msg)


def main():
    global ws_server
    CLI_ACTIVE = False
    tools, _ = assemble_tool_pool()

    # ── 启动 WS 服务器 ──
    ws = WSServer(host="localhost", port=8765)
    ws.on_message = on_ws_message
    ws_server = ws
    ws.start()

    # ── 注入 WS 实例到各模块 ──
    mood_init(ws)
    bubble_init(ws)
    output_init(ws)
    reminder_hook_init(ws)

    # ── 提醒系统：触发 → WS 推送 ──
    from reminders.manager import set_fire_callback
    set_fire_callback(on_reminder_fired)

    # ── 替换 terminal_print ──
    import utils.terminal as terminal_module
    terminal_module.terminal_print = ws_print

    print(f"my-agent server (model: {cfg.MODEL})")
    print(f"Working directory: {WORKDIR}")

    log_session_start(tools_count=len(tools))

    history = []
    context = update_context({}, [])

    # ── cron 后台线程 ──
    threading.Thread(target=cron_autorun_loop, args=(history, context), daemon=True).start()

    set_mood("idle")

    # ── 主循环：轮询消息队列 ──
    while True:
        time.sleep(0.1)
        with queue_lock:
            if not message_queue:
                continue
            query = message_queue.pop(0)

        if not query.strip():
            continue

        log_user_input(query)
        trigger_hooks("UserPromptSubmit", query)
        set_mood("thinking")
        send_bubble("Thinking...", kind=BUBBLE_STATUS, duration=0)

        turn_start = len(history)
        history.append({"role": "user", "content": query})

        with agent_lock:
            agent_loop(history, context)
            context = update_context(context, history)

        # 提取 assistant 回复文本，直接发气泡
        _send_response(history, turn_start)

        # 推断情绪
        mood = infer_mood(history)
        set_mood(mood)


def _send_response(history: list, turn_start: int):
    """从 history 提取 assistant 文本，通过 WS 发气泡"""
    for msg in history[turn_start:]:
        if msg.get("role") != "assistant":
            continue
        for block in msg.get("content", []):
            text = ""
            if hasattr(block, "type") and block.type == "text":
                text = getattr(block, "text", "")
            elif isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text", "")
            if text:
                send_bubble(text)


if __name__ == "__main__":
    main()
