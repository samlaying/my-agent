"""context.compaction — 四层上下文压缩"""

import json
import time
from pathlib import Path

from core.config import (TRANSCRIPT_DIR, TOOL_RESULTS_DIR, CONTEXT_LIMIT,
                         KEEP_RECENT_TOOL_RESULTS, PERSIST_THRESHOLD, client, MODEL)
from utils.terminal import terminal_print


def estimate_size(messages: list) -> int:
    return len(json.dumps(messages, default=str))

def collect_tool_results(messages: list):
    found = []
    for mi, msg in enumerate(messages):
        content = msg.get("content")
        if msg.get("role") != "user" or not isinstance(content, list): continue
        for bi, block in enumerate(content):
            if isinstance(block, dict) and block.get("type") == "tool_result":
                found.append((mi, bi, block))
    return found

def persist_large_output(tool_use_id: str, output: str) -> str:
    if len(output) <= PERSIST_THRESHOLD: return output
    TOOL_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    path = TOOL_RESULTS_DIR / f"{tool_use_id}.txt"
    if not path.exists(): path.write_text(output)
    return f"<persisted-output>\nFull output: {path}\nPreview:\n{output[:2000]}\n</persisted-output>"

def tool_result_budget(messages: list, max_bytes: int = 200_000) -> list:
    if not messages: return messages
    last = messages[-1]; content = last.get("content")
    if last.get("role") != "user" or not isinstance(content, list): return messages
    blocks = [(i, b) for i, b in enumerate(content) if isinstance(b, dict) and b.get("type") == "tool_result"]
    total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    if total <= max_bytes: return messages
    for _, block in sorted(blocks, key=lambda p: len(str(p[1].get("content", ""))), reverse=True):
        if total <= max_bytes: break
        text = str(block.get("content", ""))
        block["content"] = persist_large_output(block.get("tool_use_id", "unknown"), text)
        total = sum(len(str(b.get("content", ""))) for _, b in blocks)
    return messages

def snip_compact(messages: list, max_messages: int = 50) -> list:
    if len(messages) <= max_messages: return messages
    keep_tail = max_messages - 3; snipped = len(messages) - 3 - keep_tail
    return messages[:3] + [{"role": "user", "content": f"[snipped {snipped} messages]"}] + messages[-keep_tail:]

def micro_compact(messages: list) -> list:
    tool_results = collect_tool_results(messages)
    if len(tool_results) <= KEEP_RECENT_TOOL_RESULTS: return messages
    for _, _, block in tool_results[:-KEEP_RECENT_TOOL_RESULTS]:
        if len(str(block.get("content", ""))) > 120:
            block["content"] = "[Earlier tool result compacted.]"
    return messages

def write_transcript(messages: list) -> Path:
    TRANSCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    path = TRANSCRIPT_DIR / f"transcript_{int(time.time())}.jsonl"
    with path.open("w") as f:
        for msg in messages: f.write(json.dumps(msg, default=str) + "\n")
    return path

def _extract_text(content) -> str:
    if not isinstance(content, list): return str(content)
    return "\n".join(getattr(b, "text", "") for b in content if getattr(b, "type", None) == "text").strip()

def summarize_history(messages: list) -> str:
    conversation = json.dumps(messages, default=str)[:80000]
    response = client.messages.create(model=MODEL,
        messages=[{"role": "user", "content":
            f"Summarize this coding-agent conversation for continuity. "
            f"Preserve: goal, findings, changed files, remaining work.\n\n{conversation}"}],
        max_tokens=2000)
    return _extract_text(response.content) or "(empty summary)"

def compact_history(messages: list) -> list:
    transcript = write_transcript(messages)
    terminal_print(f"  \033[36m[compact] transcript: {transcript}\033[0m")
    summary = summarize_history(messages)
    return [{"role": "user", "content": f"[Compacted]\n\n{summary}"}]

def reactive_compact(messages: list) -> list:
    transcript = write_transcript(messages)
    terminal_print(f"  \033[31m[reactive compact] transcript: {transcript}\033[0m")
    try: summary = summarize_history(messages)
    except: summary = "Earlier conversation was trimmed."
    return [{"role": "user", "content": f"[Reactive compact]\n\n{summary}"}] + messages[-5:]
