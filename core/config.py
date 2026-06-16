"""core.config — 环境变量、常量、client 初始化 + 模型供应商管理"""

import json
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

# ── 路径常量 ──
SKILLS_DIR = WORKDIR / "skills"
TRANSCRIPT_DIR = WORKDIR / ".transcripts"
TOOL_RESULTS_DIR = WORKDIR / ".task_outputs" / "tool-results"
TASKS_DIR = WORKDIR / ".tasks"
WORKTREES_DIR = WORKDIR / ".worktrees"
MEMORY_DIR = WORKDIR / ".memory"
MEMORY_INDEX = MEMORY_DIR / "MEMORY.md"
MEMORY_SHARED_DIR = MEMORY_DIR / "shared"
MEMORY_STATE_PATH = MEMORY_DIR / "state.json"
LOGS_DIR = WORKDIR / ".logs"
MAILBOX_DIR = WORKDIR / ".mailboxes"
DURABLE_PATH = WORKDIR / ".scheduled_tasks.json"

# ── Agent 持久化目录（工具配置 / 推荐 都在这里）──
AGENT_DIR = WORKDIR / ".agent"
RECOMMENDATIONS_PATH = AGENT_DIR / "recommendations.json"

TASKS_DIR.mkdir(exist_ok=True)
WORKTREES_DIR.mkdir(exist_ok=True)
LOGS_DIR.mkdir(exist_ok=True)
MAILBOX_DIR.mkdir(exist_ok=True)
AGENT_DIR.mkdir(exist_ok=True)
MEMORY_SHARED_DIR.mkdir(parents=True, exist_ok=True)

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

# ── 模型供应商管理 ──
PROVIDERS_PATH = WORKDIR / "model_providers.json"

_providers: list[dict] = []
_current_provider: dict = {}


def _load_providers():
    """从 model_providers.json 加载供应商配置"""
    global _providers, _current_provider

    if not PROVIDERS_PATH.exists():
        # 回退到 .env 单供应商模式
        _providers = [{
            "name": "env",
            "description": "From .env",
            "base_url": os.getenv("ANTHROPIC_BASE_URL", ""),
            "api_key": _api_key,
            "model_id": os.environ.get("MODEL_ID", "claude-sonnet-4-20250514"),
        }]
        _current_provider = _providers[0]
        return

    try:
        data = json.loads(PROVIDERS_PATH.read_text(encoding="utf-8"))
        _providers = data.get("providers", [])
        default_name = data.get("default", "")
        # 找默认供应商，找不到就用第一个
        _current_provider = next(
            (p for p in _providers if p["name"] == default_name),
            _providers[0] if _providers else {}
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Warning: model_providers.json 解析失败: {e}")
        _providers = []
        _current_provider = {}


def _make_client(provider: dict) -> Anthropic:
    """根据供应商配置创建 Anthropic client"""
    return Anthropic(
        api_key=provider["api_key"],
        base_url=provider.get("base_url", ""),
    )


def switch_model(provider_name: str) -> str:
    """切换到指定供应商，返回切换结果描述"""
    global client, MODEL, PRIMARY_MODEL, _current_provider

    target = next((p for p in _providers if p["name"] == provider_name), None)
    if not target:
        available = ", ".join(p["name"] for p in _providers)
        return f"Error: 供应商 '{provider_name}' 不存在。可用: {available}"

    _current_provider = target
    client = _make_client(target)
    MODEL = target["model_id"]
    PRIMARY_MODEL = MODEL

    return f"已切换到 {target['description']} ({target['model_id']})"


def list_providers() -> str:
    """列出所有可用供应商"""
    if not _providers:
        return "没有配置供应商。编辑 model_providers.json"

    lines = ["可用模型供应商："]
    for p in _providers:
        current = " ← 当前" if p["name"] == _current_provider.get("name") else ""
        lines.append(f"  {p['name']}: {p['description']} ({p['model_id']}){current}")
    return "\n".join(lines)


def get_current_provider() -> dict:
    return _current_provider.copy()


# 初始化：加载供应商 + 创建 client
_load_providers()

if _current_provider:
    client = _make_client(_current_provider)
    MODEL = _current_provider["model_id"]
else:
    client = Anthropic(api_key=_api_key, base_url=os.getenv("ANTHROPIC_BASE_URL"))
    MODEL = os.environ.get("MODEL_ID", "claude-sonnet-4-20250514")

PRIMARY_MODEL = MODEL
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL_ID")
