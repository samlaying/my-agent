"""tools.hooks — Hook 系统和权限检查"""

from utils.terminal import terminal_print, safe_path


HOOKS = {"UserPromptSubmit": [], "PreToolUse": [], "PostToolUse": [], "Stop": []}

def register_hook(event: str, callback): HOOKS[event].append(callback)

def trigger_hooks(event: str, *args):
    for cb in HOOKS[event]:
        result = cb(*args)
        if result is not None: return result
    return None

DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if="]
DESTRUCTIVE = ["rm ", "> /etc/", "chmod 777"]

def permission_hook(block):
    if block.name == "bash":
        command = block.input.get("command", "")
        for pattern in DENY_LIST:
            if pattern in command: return f"Permission denied: '{pattern}' is on the deny list"
        if any(t in command for t in DESTRUCTIVE):
            print(f"\n\033[33m[permission] destructive command\033[0m\n  {command}")
            if input("  Allow? [y/N] ").strip().lower() not in ("y", "yes"):
                return "Permission denied by user"
    if block.name in ("write_file", "edit_file"):
        try: safe_path(block.input.get("path", ""))
        except Exception: return "Permission denied: path escapes workspace"
    return None

def log_hook(block):
    terminal_print(f"\033[90m[HOOK] {block.name}\033[0m")
    return None

def large_output_hook(block, output):
    if len(str(output)) > 100000:
        terminal_print(f"\033[33m[HOOK] large output: {len(str(output))} chars\033[0m")
    return None

def user_prompt_hook(query: str):
    from core.config import WORKDIR
    terminal_print(f"\033[90m[HOOK] UserPromptSubmit: {WORKDIR}\033[0m")
    return None

def stop_hook(messages: list):
    tc = sum(1 for m in messages for i in (m.get("content"),)
             if isinstance(i, list) for b in i if isinstance(b, dict) and b.get("type") == "tool_result")
    terminal_print(f"\033[90m[HOOK] Stop: {tc} tool result(s)\033[0m")
    return None

register_hook("UserPromptSubmit", user_prompt_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", stop_hook)
