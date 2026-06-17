# 🤖 my-agent — Personal AI Agent Framework + Desktop Pet

一个模块化的 Python AI Agent 框架，带可定制的 macOS 桌面宠物前端。

> Agent 不会有脾气，归纳和提醒，顺便更改。

---

## 这是什么

**my-agent** 是一个 Personal AI OS——你自己的 AI 操作系统。它由两部分组成：

1. **Python Agent 后端** — 一个完整的 Agent 框架，47 个内置工具，支持多模型切换、记忆系统、定时任务、子 Agent、队友协作等
2. **Electron 桌面宠物** — 一个常驻屏幕的小人，能冒泡说话、能打字对话、有情绪反馈、会主动提醒

两者通过 WebSocket 通信，完全解耦。你可以只用后端（终端 REPL），也可以加上桌面宠物获得更好的体验。

---

## 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Python Agent 后端                         │
│                                                             │
│  agent.py (终端 REPL)    agent_server.py (WS 服务器)         │
│       │                        │                            │
│       └────────┬───────────────┘                            │
│                │                                            │
│  ┌─────────────┴─────────────┐                              │
│  │      agent_loop()          │                              │
│  │  LLM 调用 → 工具执行 → 循环  │                              │
│  └─────────────┬─────────────┘                              │
│                │                                            │
│  ┌──────┬──────┼──────┬──────┬──────┐                       │
│  │ 文件 │ 任务 │ 定时 │ 队友 │ 记忆 │ ... (47 工具)           │
│  └──────┴──────┴──────┴──────┴──────┘                       │
└─────────────────────────────────────────────────────────────┘
                    │ WebSocket (ws://localhost:8765)
                    │ JSON 消息协议
┌─────────────────────────────────────────────────────────────┐
│                  Electron 桌面宠物                           │
│                                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ CSS 小人 │  │ 气泡系统 │  │ 聊天输入 │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                     │
│  │ 情绪动画 │  │ 主动提醒 │  │ 拖拽移动 │                     │
│  └─────────┘  └─────────┘  └─────────┘                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent 后端核心功能

### 📦 11 个包、47 个工具

| 包 | 功能 | 关键工具 |
|---|---|---|
| `core/` | 配置、状态管理 | 多模型切换 (`/model`) |
| `agents/` | Agent 主循环、子 Agent、队友 | `task`, `spawn_teammate` |
| `context/` | 系统提示、记忆、压缩、路由 | `compact`, `set_state`, `route` |
| `tools/` | 工具注册、执行、Hook | 47 个内置工具 |
| `tasks/` | 文件化任务系统 | `create_task`, `complete_task` |
| `scheduler/` | Cron 定时调度 | `schedule_cron`, `list_crons` |
| `teams/` | 消息总线、协议、后台任务 | `send_message`, `check_inbox` |
| `plugins/` | Skill 加载、MCP 插件 | `load_skill`, `connect_mcp` |
| `recommendations/` | 定时推荐系统 | `recommend`, `dismiss_recommendation` |
| `tracing/` | JSONL 日志 | 自动记录每轮对话 |
| `utils/` | 终端输出、路径安全 | `terminal_print`, `safe_path` |

### 🔄 多模型支持

```json
{
  "providers": [
    { "name": "xiaomi", "description": "小米 MiMo", "model_id": "mimo-v2.5-pro" },
    { "name": "zhipu", "description": "智谱 GLM", "model_id": "glm-5.1" },
    { "name": "ollama", "description": "本地 Ollama", "protocol": "openai" }
  ]
}
```

运行时切换：`/model ollama`、`/model xiaomi`

### 🧠 四层上下文压缩

| 层 | 触发条件 | 动作 |
|---|---|---|
| 1. 工具输出预算 | 单条 > 200KB | 落盘到 `.task_outputs/` |
| 2. 消息截断 | > 50 条消息 | 保留首 3 + 尾 47 |
| 3. 微压缩 | > 3 个历史工具结果 | 旧结果替换为摘要 |
| 4. 全量压缩 | > 50,000 字符 | LLM 总结整段对话 |

### 🛠️ 工具 Profile 系统

8 个预设 Profile，按场景切换：

| Profile | 用途 | 启用的工具 |
|---|---|---|
| `coding` | 默认编码 | Shell、文件、任务、技能 |
| `minimal` | 只读 | 读取 + 搜索 + 技能加载 |
| `research` | 调研 | 文档/搜索/只读 |
| `learning` | 学习 | 只读 + 定时 + 进度跟踪 |
| `butler` | 生活管家 | 提醒、记录、报告 |
| `digital_self` | 数字分身 | 草稿优先，外部操作需确认 |
| `automation` | 自动化 | 全部（定时、队友、工作树） |
| `full` | 完整 | 一切 |

切换：`/profile butler`

### 📋 定时推荐系统

独立的原子化推荐器，各自读一个数据源：

- **任务推荐器** — 发现未认领的任务
- **Loop 推荐器** — Inbox 里待修的问题
- **Cron 推荐器** — 缺少定期 triage 的警告
- **工具推荐器** — 建议启用/禁用的工具
- **记忆推荐器** — 带 TODO 标记的笔记

查看：`/reco` 或 `recommend` 工具

### 🔁 Loop Engineering

自动化的项目维护循环：

```
/loop triage  → 只读检查，分类问题
/loop fix     → 挑一个高置信度问题修
/loop status  → 查看状态
```

状态文件 `LOOP_STATE.md`：Inbox → In Progress → Done / Blocked

---

## 🐾 桌面宠物功能

### 可定制的 CSS 小人

纯 CSS 绘制，无外部图片，改 `character.css` 即可换外观：

```
desktop-pet/renderer/
  character.css   ← 小人外观（头、眼、嘴、身体、尾巴）
  mood.css        ← 情绪动画（呼吸、弹跳、摇头、耷拉）
  style.css       ← 布局 + 气泡 + 聊天栏
```

**5 种情绪状态**，自动切换：

| 情绪 | 触发条件 | 视觉效果 |
|---|---|---|
| 🟢 `idle` | 空闲 | 缓慢呼吸 + 眨眼 + 摇尾巴 |
| 🟡 `thinking` | 处理中 | 头倾斜 + 头顶省略号 |
| 😊 `happy` | 完成任务/成功 | 弹跳 + 笑脸 + 举手 |
| 😢 `sad` | 错误/断连 | 耷拉 + 撇嘴 + 眯眼 |
| 🔴 `alert` | 定时提醒/警告 | 抖动 + 瞪大眼 + 感叹号 |

### 气泡系统

Agent 的回复以气泡形式显示在小人头上：

- **消息气泡** — 正常对话回复
- **用户气泡** — 你发的消息（蓝色）
- **定时气泡** — Cron 触发的提醒（红色左边框，10 秒自动消失）
- **状态气泡** — "Thinking..." 等临时状态

气泡支持长文本滚动，新消息替换旧消息。

### 聊天输入

底部聊天栏，点击展开，Enter 发送，失焦自动收起。

### 拖拽移动

小人可拖拽到屏幕任意位置（CSS `-webkit-app-region: drag`）。

### 主动提醒

Cron 任务触发时，小人自动变为 `alert` 状态并弹出提醒气泡：

```
⏰ 该喝水了！
⏰ 每日复盘时间到了
```

### 情绪反馈

Agent 可以通过 `set_mood` 工具主动控制小人表情：

```
# Agent 完成任务后
set_mood("happy", "任务完成")

# Agent 遇到错误
set_mood("sad", "API 调用失败")
```

也支持自动推断——根据回复内容中的关键词（"done"/"error"/"warning"）自动切换情绪。

### 断线重连

后端重启时，小人自动变为 `sad` 状态，3 秒后自动重连。连上后恢复 `idle`。

---

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/samlaying/my-agent.git
cd my-agent
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env，填入 ANTHROPIC_API_KEY
```

或使用 `model_providers.json` 配置多模型（小米 MiMo、智谱、Ollama 等）。

### 3. 安装依赖

```bash
# Python 依赖
uv venv .venv
source .venv/bin/activate
uv pip install anthropic python-dotenv websockets openai

# Electron 依赖（可选，仅桌面宠物需要）
cd ../desktop-pet
npm install
```

### 4. 启动

**终端模式（纯 CLI）：**

```bash
python3 agent.py
```

**桌面宠物模式：**

```bash
# 终端 1：启动后端
python3 agent_server.py

# 终端 2：启动桌面宠物
cd ../desktop-pet
npx electron .
```

### 5. 常用命令

| 命令 | 功能 |
|---|---|
| `/model` | 查看/切换模型 |
| `/tools` | 查看工具状态 |
| `/profile` | 切换工具 Profile |
| `/tasks` | 查看任务列表 |
| `/crons` | 查看定时任务 |
| `/reco` | 查看推荐 |
| `/loop status` | 查看 Loop 状态 |
| `/compact` | 手动压缩上下文 |
| `/logs` | 查看日志 |

---

## 定制桌面宠物

### 换外观

编辑 `desktop-pet/renderer/character.css`：

```css
/* 换颜色 */
.pet-head { background: #FFE4B5; }  /* 肤色 */
.pet-body { background: #87CEEB; }  /* 衣服色 */

/* 换大小 */
.pet { transform: scale(1.5); }     /* 放大 1.5 倍 */

/* 换形状 */
.pet-head { border-radius: 30%; }   /* 方形头 */
```

### 换情绪动画

编辑 `desktop-pet/renderer/mood.css`：

```css
/* happy 从弹跳改成旋转 */
.mood-happy .pet {
  animation: spin 1s ease infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}
```

### 换气泡样式

编辑 `desktop-pet/renderer/style.css`：

```css
/* 暗色气泡 */
.bubble {
  background: #1e1e1e;
  color: #eee;
  border-radius: 16px;
}
.bubble::after {
  border-top-color: #1e1e1e;
}
```

### 加新情绪

1. 在 `ws/protocol.py` 的 `MOODS` 元组里加新情绪名
2. 在 `renderer/mood.css` 里加对应的 CSS 动画
3. Agent 就能通过 `set_mood("新情绪")` 控制小人

### 换窗口位置/大小

编辑 `desktop-pet/main.js`：

```javascript
mainWindow = new BrowserWindow({
  width: 300,        // 更大
  height: 400,
  x: 100,            // 左上角
  y: 100,
  // ...
});
```

---

## 项目结构

```
my-agent/                          # Python Agent 后端
├── agent.py                       # 终端 REPL 入口
├── agent_server.py                # WebSocket 服务器入口
├── core/                          # 配置、状态
├── agents/                        # Agent 循环、子 Agent、队友
├── context/                       # 提示、记忆、压缩、路由
├── tools/                         # 工具注册、执行、Hook
├── tasks/                         # 任务系统
├── scheduler/                     # Cron 调度
├── teams/                         # 消息总线、协议
├── plugins/                       # Skill、MCP
├── recommendations/               # 定时推荐
├── tracing/                       # 日志
├── utils/                         # 终端、路径
├── ws/                            # WebSocket 桥接层
│   ├── protocol.py                #   消息类型常量
│   ├── server.py                  #   纯 WS 服务器
│   ├── mood.py                    #   情绪状态管理
│   ├── bubble.py                  #   气泡发送
│   ├── output.py                  #   terminal_print 替代
│   └── cron_hook.py               #   cron 通知钩子
├── docs/                          # 设计文档
│   ├── PROJECT_BLUEPRINT.md       #   项目蓝图
│   └── superpowers/               #   Spec + 实现计划
└── model_providers.json           # 多模型配置

desktop-pet/                       # Electron 桌面宠物
├── main.js                        # Electron 主进程
├── preload.js                     # Context Bridge
└── renderer/
    ├── index.html                 # 页面结构
    ├── style.css                  # 布局 + 气泡
    ├── character.css              # 小人外观
    ├── mood.css                   # 情绪动画
    ├── ws-client.js               # WebSocket 连接
    ├── bubble.js                  # 气泡渲染
    ├── chat.js                    # 聊天输入
    └── app.js                     # 粘合层
```

---

## WebSocket 协议

所有消息格式：`{"type": "<类型>", "data": { ... }}`

### Client → Server

| type | data | 用途 |
|---|---|---|
| `user_message` | `{text: string}` | 用户输入 |

### Server → Client

| type | data | 用途 |
|---|---|---|
| `assistant_text` | `{text: string}` | Agent 输出文本 |
| `bubble` | `{text, kind, duration}` | 显示气泡 |
| `mood` | `{mood, detail}` | 切换情绪 |
| `tool_activity` | `{tool, status}` | 工具执行状态 |

---

## 测试

```bash
python3 -m pytest tests/ -v
```

56 个测试，覆盖：记忆系统、Provider 切换、多模态渲染、意图路由。

---

## License

MIT
