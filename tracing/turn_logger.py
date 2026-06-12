"""tracing.turn_logger — 对话打点"""

import json
import time
import threading
from datetime import datetime

from core.config import LOGS_DIR, MODEL, WORKDIR
from utils.terminal import terminal_print

LOGS_DIR.mkdir(exist_ok=True)

_session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOGS_DIR / f"turn_{_session_id}.jsonl"
_turn_counter = 0
_log_lock = threading.Lock()


def _write_log(event: dict):
    with _log_lock:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


def log_user_input(query: str):
    global _turn_counter
    _turn_counter += 1
    _write_log({
        "event": "user_input", "turn": _turn_counter,
        "ts": time.time(), "time": datetime.now().isoformat(timespec="seconds"),
        "content": query,
    })
    terminal_print(f"  \033[90m[log] turn #{_turn_counter} | user: {query[:60]}\033[0m")


def log_llm_response(stop_reason: str, text: str, tool_calls: list[dict], latency_ms: float):
    _write_log({
        "event": "llm_response", "turn": _turn_counter,
        "ts": time.time(), "time": datetime.now().isoformat(timespec="seconds"),
        "stop_reason": stop_reason, "latency_ms": round(latency_ms, 1),
        "text_preview": text[:200] if text else "",
        "tool_calls": tool_calls,
    })
    tool_summary = ", ".join(t["name"] for t in tool_calls) if tool_calls else "(text only)"
    terminal_print(f"  \033[90m[log] LLM: {stop_reason} | {latency_ms:.0f}ms | tools: {tool_summary}\033[0m")


def log_tool_execution(tool_name: str, tool_input: dict, output: str, latency_ms: float, blocked: bool = False):
    _write_log({
        "event": "tool_execution", "turn": _turn_counter,
        "ts": time.time(), "time": datetime.now().isoformat(timespec="seconds"),
        "tool": tool_name,
        "input_preview": json.dumps(tool_input, ensure_ascii=False)[:300],
        "output_preview": output[:300], "output_len": len(output),
        "latency_ms": round(latency_ms, 1), "blocked": blocked,
    })
    status = "BLOCKED" if blocked else "OK"
    terminal_print(f"  \033[90m[log] tool: {tool_name} | {status} | {latency_ms:.0f}ms | out: {len(output)} chars\033[0m")


def log_session_start(tools_count: int = 0):
    _write_log({
        "event": "session_start", "ts": time.time(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "session_id": _session_id, "model": MODEL,
        "workdir": str(WORKDIR), "tools_count": tools_count,
    })


def log_session_end():
    _write_log({
        "event": "session_end", "ts": time.time(),
        "time": datetime.now().isoformat(timespec="seconds"),
        "session_id": _session_id, "total_turns": _turn_counter,
        "log_file": str(LOG_FILE),
    })
    terminal_print(f"  \033[90m[log] session ended | {_turn_counter} turns | log: {LOG_FILE.name}\033[0m")


def log_error(error_type: str, error_msg: str):
    _write_log({
        "event": "error", "turn": _turn_counter,
        "ts": time.time(), "time": datetime.now().isoformat(timespec="seconds"),
        "error_type": error_type, "error_msg": error_msg[:300],
    })
