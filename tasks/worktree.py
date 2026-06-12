"""tasks.worktree — Git worktree 隔离管理"""

import re
import subprocess
import json
import time
from pathlib import Path

from core.config import WORKTREES_DIR
from tasks.task import load_task, save_task
from utils.terminal import terminal_print

WORKTREES_DIR.mkdir(exist_ok=True)
VALID_WT_NAME = re.compile(r'^[A-Za-z0-9._-]{1,64}$')


def _validate(name: str) -> str | None:
    if not name: return "Worktree name cannot be empty"
    if name in (".", ".."): return f"'{name}' is not valid"
    if not VALID_WT_NAME.match(name): return f"Invalid name '{name}'"
    return None


def _run_git(args: list[str]) -> tuple[bool, str]:
    try:
        r = subprocess.run(["git"] + args, cwd=WORKTREES_DIR.parent,
                           capture_output=True, text=True, timeout=30)
        out = (r.stdout + r.stderr).strip()
        return r.returncode == 0, out[:5000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return False, "Error: git timeout"


def _log_event(event_type: str, name: str, task_id: str = ""):
    with open(WORKTREES_DIR / "events.jsonl", "a") as f:
        f.write(json.dumps({"type": event_type, "worktree": name, "task_id": task_id, "ts": time.time()}) + "\n")


def create_worktree(name: str, task_id: str = "") -> str:
    err = _validate(name)
    if err: return f"Error: {err}"
    if task_id:
        try: load_task(task_id)
        except FileNotFoundError: return f"Error: task {task_id} not found"
    path = WORKTREES_DIR / name
    if path.exists(): return f"Worktree '{name}' already exists at {path}"
    ok, result = _run_git(["worktree", "add", str(path), "-b", f"wt/{name}", "HEAD"])
    if not ok: return f"Git error: {result}"
    if task_id:
        task = load_task(task_id)
        task.worktree = name
        save_task(task)
    _log_event("create", name, task_id)
    terminal_print(f"  \033[33m[worktree] created: {name} at {path}\033[0m")
    return f"Worktree '{name}' created at {path}"


def remove_worktree(name: str, discard_changes: bool = False) -> str:
    err = _validate(name)
    if err: return err
    path = WORKTREES_DIR / name
    if not path.exists(): return f"Worktree '{name}' not found"
    if not discard_changes:
        try:
            r = subprocess.run(["git", "status", "--porcelain"],
                               cwd=path, capture_output=True, text=True, timeout=10)
            files = len([l for l in r.stdout.strip().splitlines() if l.strip()])
            if files > 0: return f"Worktree '{name}' has {files} change(s). Use discard_changes=true."
        except Exception: pass
    ok, _ = _run_git(["worktree", "remove", str(path), "--force"])
    if not ok: return f"Failed to remove worktree '{name}'"
    _run_git(["branch", "-D", f"wt/{name}"])
    _log_event("remove", name)
    return f"Worktree '{name}' removed"


def keep_worktree(name: str) -> str:
    err = _validate(name)
    if err: return err
    _log_event("keep", name)
    return f"Worktree '{name}' kept (branch: wt/{name})"
