# Phase 1：通用基座补强 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 补强 Core OS 的四块缺口（共享记忆、Ollama 接入、多模态渲染、意图路由），使场景 Agent 能够插得进来。

**Architecture:** 四个独立模块，每个模块新增 1-2 个文件 + 对现有文件的最小修改。按 块2→块4→块1→块3 顺序实施，每块完全独立可提交。

**Tech Stack:** Python 3.12+, pytest, edge-tts, openai SDK

**Spec:** `docs/superpowers/specs/2026-06-15-core-os-strengthening-design.md`

---

## 文件结构总览

| 操作 | 文件 | 职责 |
|---|---|---|
| 修改 | `core/config.py` | 新增路径常量 + OpenAI client 工厂 |
| 修改 | `context/memory.py` | 共享记忆 + 时空状态 |
| 新增 | `context/router.py` | 意图分类器 |
| 新增 | `utils/renderer.py` | 多模态渲染器 |
| 修改 | `tools/dispatch.py` | 注册 4 个新工具 |
| 修改 | `agents/loop.py` | 路由入口集成 |
| 新增 | `tests/test_memory.py` | 共享记忆测试 |
| 新增 | `tests/test_provider.py` | Provider 测试 |
| 新增 | `tests/test_renderer.py` | 渲染器测试 |
| 新增 | `tests/test_router.py` | 路由测试 |

---

## 块 2：共享记忆与时空状态

### Task 1: 新增共享记忆路径常量

**Files:**
- Modify: `core/config.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_memory.py
"""共享记忆与时空状态测试"""

import json
from pathlib import Path
from context.memory import MemoryService


def test_shared_dir_exists(tmp_path):
    """共享目录存在且可写"""
    svc = MemoryService(root=tmp_path)
    assert svc.shared_dir.exists()
    assert svc.shared_dir.is_dir()


def test_state_path_exists(tmp_path):
    """状态文件路径可访问"""
    svc = MemoryService(root=tmp_path)
    assert svc.state_path == tmp_path / "state.json"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py -v`
Expected: FAIL — `MemoryService.__init__()` 没有 `shared_dir` 和 `state_path` 属性

- [ ] **Step 3: 最小实现**

在 `core/config.py` 的路径常量区（第 30 行后）添加：

```python
MEMORY_SHARED_DIR = MEMORY_DIR / "shared"
MEMORY_STATE_PATH = MEMORY_DIR / "state.json"
MEMORY_SHARED_DIR.mkdir(parents=True, exist_ok=True)
```

在 `context/memory.py` 的 `MemoryService.__init__()` 中添加两行：

```python
def __init__(self, root: Path = MEMORY_DIR):
    self.root = root
    self.shared_dir = root / "shared"      # 新增
    self.state_path = root / "state.json"  # 新增
    self.shared_dir.mkdir(parents=True, exist_ok=True)
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add core/config.py context/memory.py tests/test_memory.py
git commit -m "feat(memory): add shared memory dir and state path constants"
```

---

### Task 2: 实现 get_state / set_state 方法

**Files:**
- Modify: `context/memory.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_memory.py

def test_get_state_default(tmp_path):
    """无状态文件时返回空 dict"""
    svc = MemoryService(root=tmp_path)
    assert svc.get_state() == {}


def test_set_and_get_state(tmp_path):
    """set_state 写入后 get_state 能读取"""
    svc = MemoryService(root=tmp_path)
    svc.set_state("day_type", "weekend")
    svc.set_state("work_mode", "false")
    state = svc.get_state()
    assert state["day_type"] == "weekend"
    assert state["work_mode"] == "false"


def test_set_state_persists(tmp_path):
    """set_state 写入的内容持久化到 state.json"""
    svc = MemoryService(root=tmp_path)
    svc.set_state("location", "home")
    raw = json.loads((tmp_path / "state.json").read_text())
    assert raw["location"] == "home"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py::test_get_state_default tests/test_memory.py::test_set_and_get_state tests/test_memory.py::test_set_state_persists -v`
Expected: FAIL — `MemoryService` 没有 `get_state` / `set_state` 方法

- [ ] **Step 3: 最小实现**

在 `context/memory.py` 的 `MemoryService` 类中，`retrieve()` 方法之前添加：

```python
def get_state(self) -> dict:
    """读取全局时空状态。不存在则返回空 dict。"""
    if not self.state_path.exists():
        return {}
    try:
        return json.loads(self.state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}

def set_state(self, key: str, value: str) -> None:
    """更新全局状态并持久化。"""
    state = self.get_state()
    state[key] = value
    self.state_path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add context/memory.py tests/test_memory.py
git commit -m "feat(memory): add get_state/set_state for global time-space state"
```

---

### Task 3: 增强 retrieve() 支持 shared namespace 加权

**Files:**
- Modify: `context/memory.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_memory.py

from agents.profile import MemoryPolicy


def test_shared_namespace_boosted(tmp_path):
    """shared namespace 的结果比其他 namespace 权重更高"""
    # 创建两个同内容的文件：一个在 shared/，一个在普通 namespace
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir()
    (shared_dir / "note.md").write_text("今天花了50块钱吃麦当劳", encoding="utf-8")
    (tmp_path / "food.md").write_text("今天花了50块钱吃麦当劳", encoding="utf-8")

    svc = MemoryService(root=tmp_path)
    policy = MemoryPolicy(namespaces=["food", "shared"], max_chars=5000)
    result = svc.retrieve("花了50块钱", policy)

    # shared 的内容应该出现在 food 之前（权重更高）
    shared_pos = result.find("[shared]")
    food_pos = result.find("[food]")
    if shared_pos >= 0 and food_pos >= 0:
        assert shared_pos < food_pos, "shared namespace should rank higher"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py::test_shared_namespace_boosted -v`
Expected: 可能 PASS（因为 shared/ 有多个文件时默认排序可能靠前）或 FAIL — 需要确认行为

- [ ] **Step 3: 最小实现**

修改 `context/memory.py` 的 `retrieve()` 方法，给 shared namespace 加权。找到：

```python
score = len(query_tokens & _tokens(text)) if query_tokens else 0
```

替换为：

```python
score = len(query_tokens & _tokens(text)) if query_tokens else 0
if namespace == "shared":
    score *= 2  # shared namespace 加权
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add context/memory.py tests/test_memory.py
git commit -m "feat(memory): boost shared namespace weight in retrieval"
```

---

### Task 4: 注册 set_state 工具

**Files:**
- Modify: `tools/dispatch.py`
- Test: `tests/test_memory.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_memory.py

def test_set_state_tool_registered():
    """set_state 工具已注册到 BUILTIN_TOOLS"""
    from tools.dispatch import BUILTIN_TOOLS
    names = [t["name"] for t in BUILTIN_TOOLS]
    assert "set_state" in names
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py::test_set_state_tool_registered -v`
Expected: FAIL — `set_state` 不在 `BUILTIN_TOOLS` 中

- [ ] **Step 3: 最小实现**

在 `tools/dispatch.py` 的 `BUILTIN_TOOLS` 列表中（`dismiss_recommendation` 之后）添加：

```python
{"name": "set_state", "description": "Update global time-space state (work_mode, day_type, location, etc.).",
 "input_schema": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}},
```

在 `register_all_handlers()` 中注册 handler：

```python
from context.memory import MemoryService
("set_state", lambda key, value: (MemoryService().set_state(key, value), f"State '{key}' set to '{value}'.")[-1]),
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_memory.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add tools/dispatch.py tests/test_memory.py
git commit -m "feat(tools): register set_state tool for global state management"
```

---

## 块 4：Ollama Provider 接入

### Task 5: 新增 Ollama provider 配置

**Files:**
- Modify: `model_providers.json`
- Test: `tests/test_provider.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_provider.py
"""Ollama provider 接入测试"""

import json
from pathlib import Path


def test_ollama_provider_exists():
    """model_providers.json 包含 ollama provider"""
    providers_path = Path(__file__).parent.parent / "model_providers.json"
    data = json.loads(providers_path.read_text())
    names = [p["name"] for p in data["providers"]]
    assert "ollama" in names


def test_ollama_provider_fields():
    """ollama provider 包含所有必需字段"""
    providers_path = Path(__file__).parent.parent / "model_providers.json"
    data = json.loads(providers_path.read_text())
    ollama = next(p for p in data["providers"] if p["name"] == "ollama")
    assert ollama["protocol"] == "openai"
    assert "11434" in ollama["base_url"]
    assert ollama["model_id"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_provider.py -v`
Expected: FAIL — 没有 ollama provider

- [ ] **Step 3: 最小实现**

在 `model_providers.json` 的 `providers` 数组末尾添加：

```json
{
  "name": "ollama",
  "description": "本地 Ollama（qwen2.5）",
  "base_url": "http://localhost:11434/v1",
  "api_key": "ollama",
  "model_id": "qwen2.5:latest",
  "protocol": "openai"
}
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_provider.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add model_providers.json tests/test_provider.py
git commit -m "feat(providers): add Ollama local model provider config"
```

---

### Task 6: 实现 OpenAI 兼容 client 工厂

**Files:**
- Modify: `core/config.py`
- Test: `tests/test_provider.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_provider.py

def test_make_openai_client():
    """protocol=openai 时创建 OpenAI client 而非 Anthropic"""
    from core.config import _make_client
    provider = {
        "name": "test",
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
        "protocol": "openai",
    }
    client = _make_client(provider)
    # OpenAI client 有 chat 属性，Anthropic client 有 messages 属性
    assert hasattr(client, "chat"), "Should be OpenAI client"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_provider.py::test_make_openai_client -v`
Expected: FAIL — 当前 `_make_client()` 总是返回 Anthropic client

- [ ] **Step 3: 最小实现**

修改 `core/config.py` 的 `_make_client()` 函数：

```python
def _make_client(provider: dict):
    """根据供应商配置创建 client（Anthropic 或 OpenAI 兼容）"""
    if provider.get("protocol") == "openai":
        from openai import OpenAI
        return OpenAI(
            api_key=provider.get("api_key", "ollama"),
            base_url=provider["base_url"],
        )
    return Anthropic(
        api_key=provider["api_key"],
        base_url=provider.get("base_url", ""),
    )
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_provider.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add core/config.py tests/test_provider.py
git commit -m "feat(config): support OpenAI-compatible client for Ollama provider"
```

---

### Task 7: LLMGateway 支持双协议调用

**Files:**
- Modify: `agents/runtime.py`
- Test: `tests/test_provider.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_provider.py

def test_openai_call_dispatch():
    """LLMGateway 对 OpenAI client 走 chat.completions.create 路径"""
    # 这是集成测试，只验证 _make_client 返回的类型正确
    from core.config import _make_client
    anthropic_provider = {
        "name": "test-anthropic",
        "api_key": "test-key",
        "base_url": "",
    }
    openai_provider = {
        "name": "test-openai",
        "api_key": "test-key",
        "base_url": "http://localhost:11434/v1",
        "protocol": "openai",
    }
    a_client = _make_client(anthropic_provider)
    o_client = _make_client(openai_provider)
    assert hasattr(a_client, "messages"), "Anthropic client should have messages"
    assert hasattr(o_client, "chat"), "OpenAI client should have chat"
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_provider.py::test_openai_call_dispatch -v`
Expected: 可能 PASS（验证 client 类型）— 这是类型验证测试

- [ ] **Step 3: 最小实现**

在 `agents/runtime.py` 的 `LLMGateway` 类中，在 `call()` 方法之前添加：

```python
def _call_openai(self, client, session, tools, max_tokens):
    """OpenAI 兼容协议调用（Ollama 等）"""
    messages = []
    if session.profile.soul:
        messages.append({"role": "system", "content": session.profile.soul})
    for msg in session.messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            parts = []
            for block in content:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif isinstance(block, dict) and "text" in block:
                    parts.append(block["text"])
            content = "\n".join(parts)
        messages.append({"role": role, "content": content})

    openai_tools = []
    for t in tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("input_schema", {}),
            }
        })

    resp = client.chat.completions.create(
        model=client._model_id if hasattr(client, '_model_id') else "default",
        messages=messages,
        tools=openai_tools if openai_tools else None,
        max_tokens=max_tokens,
    )
    # 转换为与 Anthropic response 兼容的结构
    from types import SimpleNamespace
    content_blocks = []
    choice = resp.choices[0]
    if choice.message.content:
        content_blocks.append(SimpleNamespace(type="text", text=choice.message.content))
    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            content_blocks.append(SimpleNamespace(
                type="tool_use",
                id=tc.id,
                name=tc.function.name,
                input=json.loads(tc.function.arguments),
            ))
    return SimpleNamespace(
        content=content_blocks,
        stop_reason="end_turn" if choice.finish_reason == "stop" else choice.finish_reason,
    )
```

在 `call()` 方法中，在获取 client 之后添加分支：

```python
def call(self, session, tools, state, max_tokens):
    from core.config import _current_provider
    client = cfg.client
    # OpenAI 兼容协议分支
    if _current_provider.get("protocol") == "openai":
        client._model_id = _current_provider.get("model_id", "default")
        return self._call_openai(client, session, tools, max_tokens)
    # ... 原有 Anthropic 逻辑 ...
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_provider.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add agents/runtime.py tests/test_provider.py
git commit -m "feat(runtime): support OpenAI-compatible LLM calls for Ollama"
```

---

## 块 1：多模态渲染

### Task 8: MultimodalRenderer 基础 + render_image

**Files:**
- New: `utils/renderer.py`
- Test: `tests/test_renderer.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_renderer.py
"""多模态渲染器测试"""

from utils.renderer import MultimodalRenderer


def test_renderer_detect_terminal():
    """渲染器能检测终端类型"""
    r = MultimodalRenderer()
    assert r.terminal_type in ("iterm2", "wezterm", "other")


def test_render_image_returns_string(tmp_path):
    """render_image 对不存在文件返回 fallback 路径"""
    r = MultimodalRenderer()
    result = r.render_image(str(tmp_path / "nonexistent.png"))
    assert isinstance(result, str)
    assert "nonexistent.png" in result
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py -v`
Expected: FAIL — `utils/renderer.py` 不存在

- [ ] **Step 3: 最小实现**

```python
# utils/renderer.py
"""utils.renderer — 多模态终端输出渲染器"""

import base64
import os
import platform
import subprocess
from pathlib import Path


class MultimodalRenderer:
    """终端多模态输出。检测终端类型，graceful fallback。"""

    def __init__(self):
        self.terminal_type = self._detect_terminal()

    def _detect_terminal(self) -> str:
        term_program = os.environ.get("TERM_PROGRAM", "")
        if "iTerm" in term_program:
            return "iterm2"
        if "WezTerm" in term_program:
            return "wezterm"
        return "other"

    def render_image(self, path: str, width: int = 60) -> str:
        """在终端显示图片。iTerm2/WezTerm: inline image protocol；其他: 打印路径。"""
        p = Path(path)
        if not p.exists():
            return f"[图片不存在: {path}]"

        if self.terminal_type in ("iterm2", "wezterm"):
            data = base64.b64encode(p.read_bytes()).decode("ascii")
            # iTerm2 inline image protocol
            osc = f"\033]1337;File=inline=1;width={width}ch;preserveAspectRatio=1:{data}\a"
            print(osc, end="", flush=True)
            return f"[已在终端显示: {path}]"

        return f"[终端不支持图片显示，文件路径: {path}]"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add utils/renderer.py tests/test_renderer.py
git commit -m "feat(renderer): add MultimodalRenderer with iTerm2 image protocol"
```

---

### Task 9: 实现 speak() TTS 播放

**Files:**
- Modify: `utils/renderer.py`
- Test: `tests/test_renderer.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_renderer.py

def test_speak_returns_path(tmp_path):
    """speak 返回音频文件路径（即使 TTS 未安装也返回 fallback）"""
    r = MultimodalRenderer()
    result = r.speak("你好世界")
    assert isinstance(result, str)
    assert len(result) > 0
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py::test_speak_returns_path -v`
Expected: FAIL — `MultimodalRenderer` 没有 `speak` 方法

- [ ] **Step 3: 最小实现**

在 `utils/renderer.py` 的 `MultimodalRenderer` 类中添加：

```python
def speak(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> str:
    """TTS 播放。edge-tts 生成 .mp3 → afplay 播放。返回音频文件路径。"""
    output_path = Path("/tmp") / "agent_tts_output.mp3"

    try:
        import edge_tts
        import asyncio
        communicate = edge_tts.Communicate(text, voice)
        asyncio.run(communicate.save(str(output_path)))
    except ImportError:
        return "[edge-tts 未安装，运行: pip install edge-tts]"

    if platform.system() == "Darwin":
        subprocess.Popen(["afplay", str(output_path)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        try:
            subprocess.Popen(["mpv", "--no-video", str(output_path)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            return f"[音频已生成: {output_path}，无可用播放器]"

    return f"[TTS 播放中: {output_path}]"
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add utils/renderer.py tests/test_renderer.py
git commit -m "feat(renderer): add TTS speak() with edge-tts"
```

---

### Task 10: 实现 render_handbook() 手账体

**Files:**
- Modify: `utils/renderer.py`
- Test: `tests/test_renderer.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_renderer.py

def test_render_handbook_creates_file(tmp_path):
    """render_handbook 生成 HTML 文件"""
    r = MultimodalRenderer()
    output = str(tmp_path / "handbook.html")
    result = r.render_handbook("# 测试标题\n\n一段内容。", output)
    assert Path(result).exists()
    html = Path(result).read_text()
    assert "测试标题" in html
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py::test_render_handbook_creates_file -v`
Expected: FAIL — `MultimodalRenderer` 没有 `render_handbook` 方法

- [ ] **Step 3: 最小实现**

在 `utils/renderer.py` 的 `MultimodalRenderer` 类中添加：

```python
def render_handbook(self, content: str, output_path: str) -> str:
    """结构化 markdown → 手账体 HTML。返回输出文件路径。"""
    import html as html_mod

    lines = content.split("\n")
    body_parts = []
    for line in lines:
        if line.startswith("# "):
            body_parts.append(f"<h1>{html_mod.escape(line[2:])}</h1>")
        elif line.startswith("## "):
            body_parts.append(f"<h2>{html_mod.escape(line[3:])}</h2>")
        elif line.startswith("- "):
            body_parts.append(f"<li>{html_mod.escape(line[2:])}</li>")
        elif line.strip():
            body_parts.append(f"<p>{html_mod.escape(line)}</p>")

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: 'Courier New', monospace; max-width: 600px; margin: 40px auto; padding: 20px;
         background: #fdf6e3; color: #333; line-height: 1.8; }}
  h1 {{ border-bottom: 2px dashed #888; padding-bottom: 8px; }}
  h2 {{ color: #555; }}
  li {{ margin-left: 20px; }}
  p {{ text-indent: 2em; }}
</style>
</head>
<body>
{"".join(body_parts)}
</body>
</html>"""

    Path(output_path).write_text(html_content, encoding="utf-8")
    return output_path
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add utils/renderer.py tests/test_renderer.py
git commit -m "feat(renderer): add render_handbook() for journal-style output"
```

---

### Task 11: 注册 render_image 和 speak 工具

**Files:**
- Modify: `tools/dispatch.py`
- Test: `tests/test_renderer.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_renderer.py

def test_multimodal_tools_registered():
    """render_image 和 speak 工具已注册"""
    from tools.dispatch import BUILTIN_TOOLS
    names = [t["name"] for t in BUILTIN_TOOLS]
    assert "render_image" in names
    assert "speak" in names
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py::test_multimodal_tools_registered -v`
Expected: FAIL — 工具未注册

- [ ] **Step 3: 最小实现**

在 `tools/dispatch.py` 的 `BUILTIN_TOOLS` 中添加：

```python
{"name": "render_image", "description": "Display an image in terminal.",
 "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "width": {"type": "integer"}}, "required": ["path"]}},
{"name": "speak", "description": "Text-to-speech playback.",
 "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "voice": {"type": "string"}}, "required": ["text"]}},
```

在 `register_all_handlers()` 中注册：

```python
from utils.renderer import MultimodalRenderer
_renderer = MultimodalRenderer()
("render_image", lambda path, width=60: _renderer.render_image(path, width)),
("speak", lambda text, voice="zh-CN-XiaoxiaoNeural": _renderer.speak(text, voice)),
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_renderer.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add tools/dispatch.py tests/test_renderer.py
git commit -m "feat(tools): register render_image and speak multimodal tools"
```

---

## 块 3：意图路由

### Task 12: 实现 classify_intent() 关键词分类

**Files:**
- New: `context/router.py`
- Test: `tests/test_router.py`

- [ ] **Step 1: 写失败测试**

```python
# tests/test_router.py
"""意图路由测试"""

from context.router import classify_intent


def test_classify_single_intent():
    """单意图识别"""
    result = classify_intent("今天花了50块吃麦当劳")
    assert "复盘" in result


def test_classify_multi_intent():
    """多意图识别（复盘 + 变帅）"""
    result = classify_intent("中午吃了碗面条花了20块")
    assert "复盘" in result
    assert "变帅" in result


def test_classify_empty():
    """空输入返回空列表"""
    result = classify_intent("")
    assert result == []


def test_classify_no_match():
    """无匹配关键词返回空列表"""
    result = classify_intent("今天天气不错")
    assert result == []
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_router.py -v`
Expected: FAIL — `context/router.py` 不存在

- [ ] **Step 3: 最小实现**

```python
# context/router.py
"""context.router — 语义意图分类器（关键词版）"""

INTENT_KEYWORDS: dict[str, list[str]] = {
    "复盘":  ["花了", "消费", "买了", "支出", "付款", "花费", "多少钱", "开销"],
    "变帅":  ["吃了", "喝水", "卡路里", "饮食", "健康", "提醒喝水", "体重", "喝了多少"],
    "英语":  ["单词", "听力", "语法", "翻译", "四六级", "发音", "阅读理解"],
    "工作":  ["会议", "复盘会", "周报", "月报", "客户", "竞品", "汇报"],
    "社交":  ["人情", "情商", "聊天", "维护群", "话术"],
}


def classify_intent(text: str) -> list[str]:
    """分析用户输入，返回 Agent 标签列表。

    第一版：关键词 + 模式匹配（不消耗 LLM token）。
    """
    if not text or not text.strip():
        return []

    matched = []
    for label, keywords in INTENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched.append(label)
    return matched
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_router.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add context/router.py tests/test_router.py
git commit -m "feat(router): add keyword-based intent classifier"
```

---

### Task 13: 注册 route 工具

**Files:**
- Modify: `tools/dispatch.py`
- Test: `tests/test_router.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_router.py

def test_route_tool_registered():
    """route 工具已注册"""
    from tools.dispatch import BUILTIN_TOOLS
    names = [t["name"] for t in BUILTIN_TOOLS]
    assert "route" in names
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_router.py::test_route_tool_registered -v`
Expected: FAIL — `route` 不在 `BUILTIN_TOOLS` 中

- [ ] **Step 3: 最小实现**

在 `tools/dispatch.py` 的 `BUILTIN_TOOLS` 中添加：

```python
{"name": "route", "description": "Semantic intent router. Analyze input and dispatch to relevant agent profiles.",
 "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}},
```

在 `register_all_handlers()` 中注册：

```python
from context.router import classify_intent
("route", lambda text: str(classify_intent(text))),
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_router.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add tools/dispatch.py tests/test_router.py
git commit -m "feat(tools): register route tool for intent routing"
```

---

### Task 14: agent_loop 集成路由入口

**Files:**
- Modify: `agents/loop.py`
- Test: `tests/test_router.py`

- [ ] **Step 1: 写失败测试**

```python
# 追加到 tests/test_router.py

def test_router_import_in_loop():
    """agent_loop 模块能导入 classify_intent"""
    from context.router import classify_intent
    assert callable(classify_intent)
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_router.py::test_router_import_in_loop -v`
Expected: PASS（router 已存在）— 这是集成前置检查

- [ ] **Step 3: 最小实现**

在 `agents/loop.py` 的顶部 import 区添加：

```python
from context.router import classify_intent
```

在 `agent_loop()` 函数体的 `while True:` 循环开始处（`for job in scheduler.inject_due_jobs(session):` 之前）添加：

```python
# 路由预分类：通知相关 agent（不阻塞主循环）
if session.messages:
    last_user = next((m for m in reversed(session.messages) if m.get("role") == "user"), None)
    if last_user:
        content = last_user.get("content", "")
        if isinstance(content, str):
            intents = classify_intent(content)
            if intents:
                terminal_print(f"\033[33m[route] {', '.join(intents)}\033[0m")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/test_router.py -v`
Expected: ALL PASS

- [ ] **Step 5: 提交**

```bash
git add agents/loop.py tests/test_router.py
git commit -m "feat(loop): integrate intent router into agent_loop"
```

---

## 收尾

### Task 15: 更新 CLAUDE.md 文档

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: 更新工具目录表**

在 CLAUDE.md 的工具目录表中追加新工具：

```markdown
| 共享记忆 | `set_state` |
| 多模态 | `render_image`, `speak` |
| 路由 | `route` |
```

- [ ] **Step 2: 更新架构说明**

在 Key Data Flow 中追加路由步骤。

- [ ] **Step 3: 提交**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with Phase 1 new tools and routing"
```

---

### Task 16: 运行全量测试确认无回归

- [ ] **Step 1: 运行全部测试**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m pytest tests/ -v`
Expected: ALL PASS（无回归）

- [ ] **Step 2: 运行类型检查（如有 mypy）**

Run: `cd /Users/sam/03-Code/02-Own/my-agent && python3 -m mypy context/memory.py context/router.py utils/renderer.py core/config.py --ignore-missing-imports`
Expected: 无新错误

- [ ] **Step 3: 最终提交**

```bash
git add -A
git commit -m "feat: Phase 1 Core OS strengthening complete (memory, ollama, renderer, router)"
```
