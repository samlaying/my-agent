"""tools.builtin — 基础工具实现"""

import subprocess
from utils.terminal import terminal_print, safe_path


def run_bash(command: str, cwd=None, run_in_background: bool = False) -> str:
    from core.config import WORKDIR
    try:
        r = subprocess.run(command, shell=True, cwd=cwd or WORKDIR,
                           capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def run_read(path: str, limit: int | None = None, offset: int = 0, cwd=None) -> str:
    try:
        lines = safe_path(path, cwd).read_text().splitlines()
        offset = max(int(offset or 0), 0)
        lines = lines[offset:]
        limit = int(limit) if limit is not None else None
        if limit is not None and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str, cwd=None) -> str:
    try:
        fp = safe_path(path, cwd)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str, cwd=None) -> str:
    try:
        fp = safe_path(path, cwd)
        text = fp.read_text()
        if old_text not in text: return f"Error: text not found in {path}"
        fp.write_text(text.replace(old_text, new_text, 1))
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


def run_glob(pattern: str, cwd=None) -> str:
    import glob as g
    from core.config import WORKDIR
    try:
        base = cwd or WORKDIR
        results = [m for m in g.glob(pattern, root_dir=base)
                   if (base / m).resolve().is_relative_to(base)]
        return "\n".join(results) if results else "(no matches)"
    except Exception as e:
        return f"Error: {e}"


def run_todo_write(todos: list) -> str:
    import core.state as state
    for i, todo in enumerate(todos):
        if "content" not in todo or "status" not in todo:
            return f"Error: todos[{i}] missing 'content' or 'status'"
        if todo["status"] not in ("pending", "in_progress", "completed"):
            return f"Error: todos[{i}] invalid status '{todo['status']}'"
    state.CURRENT_TODOS = todos
    terminal_print(f"  \033[33m[todo] updated {len(todos)} item(s)\033[0m")
    return f"Updated {len(todos)} todos"


def call_tool_handler(handler, args: dict, name: str) -> str:
    if not handler: return f"Unknown: {name}"
    try: return handler(**(args or {}))
    except TypeError as e: return f"Error: {e}"
