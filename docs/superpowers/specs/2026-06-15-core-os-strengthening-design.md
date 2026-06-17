# Phase 1 设计：通用基座补强（Core OS Strengthening）

> **日期**：2026-06-15
> **状态**：Approved
> **父蓝图**：`docs/PROJECT_BLUEPRINT.md`
> **目标**：补强 Core OS 的四块缺口（I/O 多模态、共享记忆、意图路由、本地模型接入），使场景 Agent 能够插得进来。

---

## 背景

`my-agent` 已经是一个功能完整的 Core OS（11 包、43 工具、四层压缩、Skill 注册表、teammate/subagent、cron、memory、recommendations）。但场景 Agent 矩阵（英语、变帅、每日复盘等）落地时，遇到四块架构缺口：

| 缺口 | 卡住哪些 Agent |
|---|---|
| I/O 纯文本 | 英语（音频）、人情世故（录音）、变帅（手机推送）、手账体渲染 |
| 记忆不共享 | 变帅（读消费）、复盘（读饮食）、数字分身（读知识库） |
| 无意图路由 | "今天花 50 吃麦当劳"无法同时触发复盘+变帅 |
| 无本地模型 | 期末/编程学习、会议（实时低延迟场景） |

Phase 1 补这四块，不涉及任何具体场景 Agent 的实现。

---

## 块 1 — 多模态渲染（I/O 层）

### 新增文件

`utils/renderer.py` — 多模态输出渲染器，与 `terminal_print()` 并列，不侵入现有代码。

### 公共接口

```python
class MultimodalRenderer:
    """终端多模态输出。检测终端类型，graceful fallback。"""

    def render_image(self, path: str, width: int = 60) -> str:
        """在终端显示图片。iTerm2/WezTerm: inline image protocol；其他: 打印路径。"""
        ...

    def speak(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural") -> str:
        """TTS 播放。edge-tts 生成 .mp3 → afplay/mpv 播放。返回音频文件路径。"""
        ...

    def render_handbook(self, content: str, output_path: str) -> str:
        """结构化 markdown → 手账体 PDF/HTML。返回输出文件路径。"""
        ...
```

### 终端兼容性

| 终端 | 图片 | 声音 |
|---|---|---|
| iTerm2 | ✅ inline image protocol (`\033]1337;File=...`) | ✅ afplay |
| WezTerm | ✅ inline image protocol | ✅ afplay/mpv |
| 其他 | fallback: 打印文件路径 | fallback: 打印文件路径 |

### 新增 LLM 工具（2 个）

```python
# tools/dispatch.py BUILTIN_TOOLS 新增：
{"name": "render_image", "description": "Display an image in terminal.",
 "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "width": {"type": "integer"}}, "required": ["path"]}}
{"name": "speak", "description": "Text-to-speech playback.",
 "input_schema": {"type": "object", "properties": {"text": {"type": "string"}, "voice": {"type": "string"}}, "required": ["text"]}}
```

### 依赖

- `edge-tts`（pip install，免费 TTS）
- macOS `afplay`（原生）或 `mpv`（Linux）

### 不做的事

- 不做全功能图像处理（不做 resize/crop/filter）——那是场景 Agent 的事
- 不做实时音频流——Phase 1 只做离线 TTS → 文件 → 播放
- 不做手机/微信入口——那是 Phase 2+ 的 Hermes 集成

---

## 块 2 — 共享记忆与时空状态（Memory 层）

### 修改文件

`context/memory.py` — 增强 `MemoryService`，不替换现有逻辑。

### 共享目录

`.memory/shared/` — 跨 Agent 共享数据目录。任何 Agent 写入的文件，其他 Agent 通过 namespace `"shared"` 可读。

用途：消费记录、饮食日志、日程数据、知识沉淀。复盘 Agent 写入 → 变帅 Agent 读取。

### 时空状态标签

`.memory/state.json` — 全局状态对象：

```json
{
  "work_mode": true,
  "day_type": "weekday",
  "location": "office",
  "last_activity": "2026-06-15T14:30:00"
}
```

Agent 在 `soul` 或 `skill` 中读取此状态，决定行为（周末变帅 Agent 不推桌面任务，工作日复盘 Agent 聚焦消费数据等）。

### `MemoryService` 增强

```python
class MemoryService:
    def __init__(self, root: Path = MEMORY_DIR):
        self.root = root
        self.shared_dir = root / "shared"   # 新增
        self.state_path = root / "state.json"  # 新增

    def get_state(self) -> dict:
        """读取全局时空状态。不存在则返回默认。"""
        ...

    def set_state(self, key: str, value: str) -> None:
        """更新全局状态并持久化。"""
        ...

    def retrieve(self, query: str, policy: MemoryPolicy) -> str:
        """增强：shared namespace 结果权重提升（×2 加分）。"""
        ...  # 原逻辑 + shared 加权
```

### 检索增强

在 `_tokens()` 的基础上，当 namespace 为 `"shared"` 时，score `*= 2`。这让跨 Agent 共享的数据在检索时优先命中。

### 新增 LLM 工具（1 个）

```python
{"name": "set_state", "description": "Update global time-space state (work_mode, day_type, location, etc.).",
 "input_schema": {"type": "object", "properties": {"key": {"type": "string"}, "value": {"type": "string"}}, "required": ["key", "value"]}}
```

### 新增配置路径

`core/config.py`：

```python
MEMORY_SHARED_DIR = MEMORY_DIR / "shared"
MEMORY_STATE_PATH = MEMORY_DIR / "state.json"
MEMORY_SHARED_DIR.mkdir(parents=True, exist_ok=True)
```

### 不做的事

- 不做向量数据库（chromadb/faiss）——Phase 1 用 token 交集 + 权重，够用
- 不做自动记忆提取/总结——那是 `compact_history` 的事，已经实现
- 不做跨机器同步——那是 Hermes/云端的事

---

## 块 3 — 意图路由（Router 层）

### 新增文件

`context/router.py` — 语义意图分类器。

### 接口

```python
def classify_intent(text: str) -> list[str]:
    """分析用户输入，返回 Agent 标签列表。
    
    第一版：关键词 + 模式匹配（不消耗 LLM token）。
    后期可升级为 LLM-based 分类。
    
    返回值示例：["复盘"] 或 ["复盘", "变帅"] 或 ["英语"]
    """
    ...
```

### 关键词映射表（初版）

```python
INTENT_KEYWORDS = {
    "复盘":  ["花了", "消费", "买了", "支出", "付款", "花费", "多少钱"],
    "变帅":  ["吃了", "喝水", "卡路里", "饮食", "健康", "提醒", "体重"],
    "英语":  ["单词", "听力", "语法", "翻译", "四六级", "发音"],
    "工作":  ["会议", "复盘", "周报", "月报", "客户", "竞品"],
    "社交":  ["人情", "情商", "聊天", "维护群"],
}
```

### 路由入口

在 `agent_loop()` 入口处（`agents/loop.py`），调用 `classify_intent()` 做预分类。当返回多个标签时，把消息分发给对应的 profile/skill 组合（复用 `assemble_tool_pool(profile_name)`）。

### 新增 LLM 工具（1 个）

```python
{"name": "route", "description": "Semantic intent router. Analyze input text and dispatch to relevant agent profiles.",
 "input_schema": {"type": "object", "properties": {"text": {"type": "string"}}, "required": ["text"]}}
```

### 不做的事

- 不做 LLM-based 分类（Phase 1 用关键词，后期再升级）
- 不做自动 profile 切换——路由只做"通知"，不改 active profile
- 不做消息队列/异步分发——Phase 1 同步调用

---

## 块 4 — Ollama Provider 接入（模型层）

### 修改文件

- `model_providers.json` — 新增 ollama 条目
- `core/config.py` — `_make_client()` 支持 OpenAI 兼容协议

### Provider 配置

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

### Client 适配

当前 `config.py:_make_client()` 只创建 `Anthropic()` client。Ollama 用 OpenAI 兼容 API，需要分支：

```python
def _make_client(provider: dict):
    if provider.get("protocol") == "openai":
        from openai import OpenAI
        return OpenAI(
            api_key=provider["api_key"],
            base_url=provider["base_url"],
        )
    return Anthropic(
        api_key=provider["api_key"],
        base_url=provider.get("base_url", ""),
    )
```

### 调用适配

`LLMGateway.call()`（`agents/runtime.py`）需要支持两种 client：
- `Anthropic` client：`client.messages.create()`
- `OpenAI` client：`client.chat.completions.create()`

通过 `hasattr(client, 'messages')` 或 `provider.protocol` 判断，分支调用。

### 依赖

- `openai`（pip install openai）

### 切换方式

`/model ollama` — 与现有 `/model` 热切换完全一致。

### 不做的事

- 不做自动模型选择/降级——那是后期的事
- 不做本地模型量化/部署脚本——用户自己 `ollama pull qwen2.5`

---

## 块间依赖 & 实施顺序

```
块 4（Ollama）      块 2（共享记忆）         ← 无依赖，可并行
       ↓                       ↓
块 1（多模态）      块 3（意图路由）         ← 块 3 需要知道"复盘 Agent"用什么 namespace
```

**推荐顺序**：块 2 → 块 4 → 块 1 → 块 3

理由：
1. 块 2（共享记忆）是最底层的数据基础，其他三块都间接依赖它
2. 块 4（Ollama）独立于其他三块，可穿插做
3. 块 1（多模态）不依赖其他块，但依赖 edge-tts pip 安装
4. 块 3（路由）需要知道各 Agent 的 namespace 配置，依赖块 2 的 shared 目录结构

---

## 关键决策记录

| 决策 | 选择 | 理由 |
|---|---|---|
| 图片协议 | iTerm2 inline image protocol | macOS 最常用终端，协议简单，fallback 到路径 |
| TTS 引擎 | edge-tts（免费） | 不需要 API key，中文支持好，离线生成 .mp3 |
| 手账体渲染 | markdown → HTML/PDF | 终端无法直接渲染复杂排版，输出文件最实用 |
| 记忆共享方式 | 文件系统（`.memory/shared/`） | 与现有 `.memory/*.md` 风格一致，不引入新依赖 |
| 状态存储 | JSON 文件（`.memory/state.json`） | 简单、可编辑、与 `.scheduled_tasks.json` 风格一致 |
| 路由实现 | 关键词匹配（非 LLM） | 不消耗 token，Phase 1 够用，后期可升级 |
| Ollama 协议 | OpenAI 兼容（`/v1`） | Ollama 原生支持，`openai` 包成熟 |
