"""utils.terminal — 线程安全的终端输出"""

import threading
from pathlib import Path

READLINE_AVAILABLE = False
try:
    import readline
    readline.parse_and_bind('set bind-tty-special-chars off')
    READLINE_AVAILABLE = True
except ImportError:
    pass

PROMPT = "\033[36magent >> \033[0m"


def terminal_print(text: str):
    from core.state import CLI_ACTIVE
    if threading.current_thread() is threading.main_thread() or not CLI_ACTIVE:
        print(text)
        return
    line = ""
    if READLINE_AVAILABLE:
        try:
            line = readline.get_line_buffer()
        except Exception:
            pass
    print(f"\r\033[K{text}")
    print(PROMPT + line, end="", flush=True)


def safe_path(p: str, cwd: Path = None) -> Path:
    from core.config import WORKDIR
    base = cwd or WORKDIR
    path = (base / p).resolve()
    if not path.is_relative_to(base):
        raise ValueError(f"Path escapes workspace: {p}")
    return path
