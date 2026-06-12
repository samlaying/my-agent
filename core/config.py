"""core.config — 环境变量、常量、client 初始化"""

import os
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

# 使用自定义 base URL 时清除 session token
if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

_api_key = os.getenv("ANTHROPIC_API_KEY") or os.getenv("ANTHROPIC_AUTH_TOKEN")
if not _api_key:
    print("Error: ANTHROPIC_API_KEY not set. Edit .env file.")
    sys.exit(1)

WORKDIR = Path.cwd()
client = Anthropic(api_key=_api_key, base_url=os.getenv("ANTHROPIC_BASE_URL"))
MODEL = os.environ.get("MODEL_ID", "glm-5.1")
PRIMARY_MODEL = MODEL
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL_ID")

# ── 路径常量 ──
SKILLS_DIR = WORKDIR / "skills"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"
TASKS_DIR = WORKDIR / ".tasks"
WORKTREES_DIR = WORKDIR / ".worktrees"
MEMORY_DIR = WORKDIR / ".memory"
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
LOGS_DIR = WORKDIR / ".logs"
MAILBOX_DIR = WORKDIR / ".mailboxes"
DURABLE_PATH = WORKDIR / ".scheduled_tasks.json"

TASKS_DIR.mkdir(exist_ok=True)
WORKTREES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
MAILBOX_DIR.mkdir(exist_ok=True)

# ── 阈值常量 ──
DEFAULT_MAX_TOKENS = 8000
ESCALATED_MAX_TOKENS = 16000
MAX_RETRIES = 3
MAX_CONSECUTIVE_529 = 2
MAX_RECOVERY_RETRIES = 2
BASE_DELAY_MS = 500
CONTEXT_LIMIT = 50000
KEEP_RECENT_TOOL_RESULTS = 3
PERSIST_THRESHOLD = 30000
CONTINUATION_PROMPT = "Continue from the previous response. Do not repeat completed work."
IDLE_POLL_INTERVAL = 5
IDLE_TIMEOUT = 60
