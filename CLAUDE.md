# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A modular Python coding agent framework built on the Anthropic Messages API. It implements a REPL-based agent with 20+ mechanisms (tool use, subagents, teammate threads, cron scheduling, task management, context compaction, hook system, MCP plugin support, background execution, memory) across 10 packages. Based on the learn-claude-code s20 architecture.

## Running

```bash
cd my-agent && python3 agent.py
```

Requires `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_BASE_URL`, `MODEL_ID`) in `.env`. Dependencies: `anthropic>=0.25.0`, `python-dotenv>=1.0.0` (`pip install -r requirements.txt`).

Tests: `python3 -m pytest tests/ -v` (pytest). No linter configured.

## REPL Slash Commands

| Command | Action |
|---|---|
| `/tasks` | List file-backed tasks |
| `/team` | Show active teammate threads |
| `/inbox` | Consume lead agent inbox from mailbox bus |
| `/compact` | Force context compaction |
| `/crons` | List scheduled cron jobs |
| `/reco` | Refresh & show scheduled recommendations (定时推荐) |
| `/logs` | Tail the JSONL turn log |
| `/loop [status\|triage\|fix\|add <item>]` | Loop Engineering system |
| `/model [<provider>]` | List or switch model providers (from `model_providers.json`) |
| `/tools [on\|off <name>]` | List, enable, or disable tools by name |
| `/profile [<name>]` | List or switch active tool profile |

## Architecture

Entry point is `agent.py` — a REPL that registers handlers, starts a cron daemon thread, and runs `agent_loop` per user input. The 11 packages:

| Package | Purpose |
|---|---|
| `core/` | `config.py` — env vars, Anthropic client, path constants, thresholds. `state.py` — mutable global state (todos, teammates, MCP clients, background tasks). |
| `agents/` | `loop.py` — main agentic loop (LLM call → tool execution → context management → repeat). `recovery.py` — retry with exponential backoff, model fallback on 529s. `subagent.py` — isolated single-task agent with its own tool set. `teammate.py` — long-lived autonomous threads with inbox polling, plan approval protocol, auto-task-claiming. `loop_state.py` — parses and updates `LOOP_STATE.md` for the Loop Engineering system. `profile.py` — agent profile contract (soul, skills, tool_profile, memory policy, triggers). `runtime.py` — shared runtime atoms (RuntimeSession, ContextBuilder, LLMGateway, SchedulerBridge, OutputCollector). |
| `context/` | `system_prompt.py` — dynamic prompt assembly (tools, skills, memories, MCP). `compaction.py` — four-tier context compression: tool_result_budget → snip_compact → micro_compact → full LLM summarize. `memory.py` — reads `.memory/MEMORY.md` into context. |
| `tools/` | `dispatch.py` — tool schema definitions + handler registry (`register_all_handlers` wires everything at startup). `builtin.py` — bash, read/write/edit, glob, todo_write implementations. `hooks.py` — event hooks (UserPromptSubmit, PreToolUse, PostToolUse, Stop) with permission checking. `executor.py` — ToolExecutor class wrapping handler calls with pre/post hooks and logging. `contracts.py` — ToolSpec dataclass for typed tool definitions. `registry.py` — tool profiles (minimal/coding/research/learning/butler/digital_self/automation/full), runtime enable/disable switches, hot reload. |
| `tasks/` | `task.py` — file-backed task system (`.tasks/*.json`) with dependency graph (blockedBy). `worktree.py` — git worktree CRUD with branch `wt/{name}`. |
| `scheduler/` | `cron.py` — 5-field cron parser + persistent scheduler (`.scheduled_tasks.json`). Fires jobs into the cron queue consumed by agent_loop. |
| `recommendations/` | Scheduled recommendations (定时推荐). `contract.py` — `Recommendation` card + atomic `Recommender` base. `recommenders/` — one data source per file (task / loop / cron / tool / memory). `engine.py` — aggregate → dedupe → rank → persist, plus an idempotent daily refresh cron. `feed.py` — `.agent/recommendations.json` with status preservation across refreshes. `tools.py` — tool wrappers. |
| `teams/` | `bus.py` — JSONL mailbox message bus (`.mailboxes/{agent}.jsonl`). `protocol.py` — shutdown handshake and plan approval state machine. `background.py` — auto-detects slow bash commands, runs them in threads, collects results as notifications. |
| `plugins/` | `skills.py` — loads skill definitions from `skills/*/SKILL.md` with frontmatter parsing. `mcp.py` — MCP server client abstraction (currently mock servers: "docs", "deploy"). |
| `tracing/` | `turn_logger.py` — JSONL turn log (`.logs/turn_{timestamp}.jsonl`) recording user input, LLM responses, tool executions, errors. |
| `utils/` | `terminal.py` — thread-safe terminal printing (handles readline prompt restoration) and `safe_path` for workspace escape prevention. |

## Key Data Flow

1. User input → `agent_loop()` calls `client.messages.create()` with assembled system prompt + tool schemas
2. Response parsed — text blocks printed, tool_use blocks dispatched to handlers via registry
3. Tool results collected → appended as user message → loop repeats until no tool_use in response
4. Context grows → four-tier compaction kicks in (budget → snip → micro → full summarize)
5. Background bash commands detected by keyword (`install`, `build`, `test`, `deploy`, `compile`, `pytest`, `make`) and run in threads
6. Cron scheduler (daemon thread) matches jobs every second and injects them as `[Scheduled]` user messages
7. Teammates run independent agent loops in threads, communicating via the mailbox bus

## Subagent vs Teammate

These are the two concurrency models, and they serve fundamentally different purposes:

**Subagent** (`task` tool → `subagent.py`): Synchronous, short-lived, single-task. Gets 5 tools (bash, read, write, edit, glob). No retry, no compaction, max 30 iterations. Runs in the calling thread. Returns the last assistant message as a string. Used for "do this one thing and return."

**Teammate** (`spawn_teammate` tool → `teammate.py`): Asynchronous, long-lived, autonomous daemon thread. Gets 8 tools including messaging and task management. Polls its own inbox, auto-claims unclaimed tasks during idle, and follows a plan approval protocol (submit → wait for lead approval → execute). Exits after 60s idle. Communicates results back via the JSONL mailbox bus.

## Context Compaction (Four Tiers)

Applied in order by `prepare_context()` in `context/compaction.py`:

| Tier | Trigger | Action |
|---|---|---|
| 1. `tool_result_budget` | Last message's tool results > 200KB | Offload largest outputs to `.task_outputs/`, replace with `<persisted-output>` preview (2KB) |
| 2. `snip_compact` | Message count > 50 | Keep first 3 + last 47 messages, insert `[snipped N messages]` |
| 3. `micro_compact` | More than 3 tool results in history | Replace older results (beyond last 3) with `[Earlier tool result compacted.]` if >120 chars |
| 4. `compact_history` / `reactive_compact` | `estimate_size() > 50,000` chars after tiers 1–3 | Full LLM summarization. Writes transcript to `.transcripts/`, replaces history with `[Compacted]` summary. Reactive variant keeps last 5 messages. |

## Tool Catalog (47 Builtin)

Grouped by category — all defined in `tools/dispatch.py`:

| Category | Tools |
|---|---|
| File ops | `bash`, `read_file`, `write_file`, `edit_file`, `glob` |
| Todo | `todo_write` |
| Subagent | `task` |
| Skill | `load_skill` |
| Context | `compact` |
| Tasks | `create_task`, `list_tasks`, `get_task`, `claim_task`, `complete_task` |
| Cron | `schedule_cron`, `list_crons`, `cancel_cron` |
| Team | `spawn_teammate`, `send_message`, `check_inbox`, `request_shutdown`, `request_plan`, `review_plan` |
| Worktree | `create_worktree`, `remove_worktree`, `keep_worktree` |
| MCP | `connect_mcp` |
| Loop Engineering | `loop_triage`, `loop_fix`, `loop_status`, `loop_inbox_add`, `loop_done`, `loop_block`, `loop_decision` |
| Control plane | `tool_status`, `tool_enable`, `tool_disable`, `tool_profile`, `tool_reload` |
| Recommendations | `recommend`, `list_recommendations`, `dismiss_recommendation` |
| Shared Memory | `set_state` |
| Multimodal | `render_image`, `speak` |
| Routing | `route` |

MCP tools are added dynamically with naming `mcp__{server}__{tool}` via `assemble_tool_pool()` each turn.

## Key Thresholds (`core/config.py`)

| Constant | Value | Purpose |
|---|---|---|
| `DEFAULT_MAX_TOKENS` | 8,000 | Normal LLM response token limit |
| `ESCALATED_MAX_TOKENS` | 16,000 | Used when response hits token limit |
| `MAX_RETRIES` | 3 | API call retry attempts |
| `MAX_CONSECUTIVE_529` | 2 | Triggers fallback to `FALLBACK_MODEL` |
| `BASE_DELAY_MS` | 500 | Exponential backoff base (doubles, max 32s, +25% jitter) |
| `CONTEXT_LIMIT` | 50,000 chars | Triggers full LLM summarization (tier 4) |
| `KEEP_RECENT_TOOL_RESULTS` | 3 | Micro-compact preserves this many recent results |
| `PERSIST_THRESHOLD` | 30,000 chars | Tool output size triggering disk offload |
| `IDLE_TIMEOUT` | 60s | Teammate auto-exit on inactivity |
| `IDLE_POLL_INTERVAL` | 5s | Teammate inbox polling frequency |

## Multi-Provider Model System

`model_providers.json` defines multiple LLM providers. Each entry has `name`, `description`, `base_url`, `api_key`, `model_id`. The `default` field selects startup provider. Switch at runtime with `/model <name>` — this recreates the Anthropic client and updates `cfg.MODEL` / `cfg.PRIMARY_MODEL` globally.

## Tool Profiles & Control Plane

`tools/registry.py` implements a profile-based tool gating system. Profiles define which tool categories and explicit tools are enabled. Stored in `.agent/tools.json` (created on first use).

| Profile | Purpose |
|---|---|
| `coding` | Default — shell, files, tasks, skills, agents |
| `minimal` | Read-only + skill loading |
| `research` | Docs/search/read-only (no file writes) |
| `learning` | Read-only + scheduling + progress tracking |
| `butler` | Personal ops — no shell, no file writes |
| `digital_self` | Draft-first social — external actions need confirmation |
| `automation` | Full access for cron, teammates, worktrees |
| `full` | Everything registered |

Control tools (`tool_status`, `tool_enable`, `tool_disable`, `tool_profile`, `tool_reload`) are always enabled regardless of profile. Per-tool overrides stored in `.agent/tools.json` take precedence over profile defaults.

## Conventions

- All tool handlers are plain functions returning `str` (errors as `"Error: ..."` strings, not exceptions).
- File persistence uses JSONL for logs/mailboxes and JSON for tasks/cron state.
- Thread safety: `agent_lock` serializes main agent loop access; `cron_lock` for scheduler; `_log_lock` for logging.
- Paths are sandboxed to `WORKDIR` via `safe_path()` — never resolve outside the workspace.
- Hook callbacks returning non-`None` block the action (used for permission checks on destructive commands).
- The tool pool is re-assembled each turn via `assemble_tool_pool()` to pick up dynamically connected MCP tools.

## Loop Engineering System

The agent implements a phased Loop Engineering pattern for autonomous project maintenance, controlled by `LOOP_STATE.md` (state file) and two skills in `skills/`.

### REPL Command

`/loop [status|triage|fix|add <item>]` — interact with the loop system from the REPL.

### Loop Tools (7)

| Tool | Purpose |
|---|---|
| `loop_triage` | Loads `project-triage-loop` skill, triggers read-only inspection of git/commits/deps, updates `LOOP_STATE.md`. |
| `loop_fix` | Loads `project-fix-loop` skill, picks one inbox item, fixes in a worktree, runs tests, updates state. |
| `loop_status` | Shows section counts from `LOOP_STATE.md`. |
| `loop_inbox_add` | Adds an item to the Inbox section. |
| `loop_done` | Moves an inbox item to Done with date stamp. |
| `loop_block` | Moves an item to Blocked with a reason. |
| `loop_decision` | Appends a row to the Decisions table. |

### Phased Rollout

- **Phase 1 (triage)**: `loop_triage` — read-only, classify findings, update state, report. No code changes.
- **Phase 2 (fix)**: `loop_fix` — exactly one high-confidence fix per run, worktree-isolated, test-verified.
- **Phase 3 (future)**: Maker-checker — spawn worker subagent to implement, reviewer subagent to audit the diff.

### Recurring Execution

Use `schedule_cron` to automate triage:
```
schedule_cron("0 9 * * 1-5", "Use loop_triage tool to run project triage.", true, true)
```

### State File Sections (`LOOP_STATE.md`)

- **Inbox** — discovered issues (`- [ ] description`)
- **In Progress** — items being actively worked on
- **Done** — completed items (`- [x] [YYYY-MM-DD] description — note`)
- **Decisions** — table of `Date | Decision | Reason`
- **Blocked** — items needing human judgment, with reason

## Scheduled Recommendations (定时推荐)

A decoupled, atomic recommendation system. Independent **recommenders** each read one data source and emit `Recommendation` cards; the **engine** aggregates, dedupes (by stable id), ranks (by priority), and persists them. Backend is highly atomized — each recommender/engine unit is a single file with a pure-data interface, independently testable.

### Recommenders (`recommendations/recommenders/`)

| Source | Reads | Produces |
|---|---|
| `task` | `.tasks/*.json` | Pick up unclaimed tasks (P5 ready / P4 blocked); finish in-progress (P3) |
| `loop` | `LOOP_STATE.md` | Fix Inbox items (P4); Blocked items need decision (P3) |
| `cron` | `scheduled_jobs` | Triage-scheduling gap (P3); active recurring jobs (P2) |
| `tool` | tool registry | Enable useful disabled tools (P2); warn on high-risk tools enabled (P3) |
| `memory` | `.memory/*.md` | Follow-up notes containing TODO/should/pending markers (P2) |

### Lifecycle

- **Scheduled (定时):** `engine.ensure_scheduled()` registers one idempotent daily cron (`17 9 * * 1-5`, durable) at startup. When it fires, the injected prompt asks the agent to call `recommend`, refreshing the feed.
- **On demand:** `/reco` REPL command, or the `recommend` tool, refresh + summarize. `list_recommendations` is read-only.
- **Persistence:** `.agent/recommendations.json`. A refresh preserves user-set `dismissed`/`done` status (matched by id), so handled cards don't bounce back.
- **Failure isolation:** a single recommender raising is caught and turned into one low-priority card — it never breaks the rest of the feed.

## Auto-Writer System

A Make-Check writing loop that automatically writes, blind-evaluates, and revises articles until they score ≥ 8/10 on a 7-dimension rubric. Based on the Cheat on Content blind-evaluation pattern.

### Core Loop

```
/write <主题> → Make (write) → Check (blind critique) → Judge (≥ 8?) → Loop or Output
```

### Key Files

| File | Purpose |
|---|---|
| `agents/writer_loop.py` | Loop controller: Writer/Critic Sub-Agents, memory management, guardrails |
| `rubrics/content-rubric.md` | Full 7-dimension rubric (Writer sees this) |
| `rubrics/content-rubric-blind.md` | Blind rubric (Critic sees this — no intent leakage) |
| `skills/auto-writer/SKILL.md` | Skill definition for the writing workflow |
| `memory/goal.md` | Current task state (topic, round, best score) |
| `memory/patterns.md` | Accumulated writing patterns across tasks |
| `memory/feedback.md` | Per-round deduction feedback (overwritten each round) |
| `drafts/draft-{N}.md` | Draft per round |
| `final.md` | Final output |
| `sources/sources.md` | Research material (optional, pre-populated) |

### 7-Dimension Scoring (total 10)

| Dimension | Max | Weight |
|---|---|---|
| clarity (读者能看懂) | 2.0 | 每个术语有白话定义 |
| examples (概念有例子) | 2.0 | 每个核心概念有具体场景 |
| practice (可实操) | 2.0 | 每节有"怎么做"步骤 |
| facts (事实可靠) | 1.5 | 来源标注 |
| structure (结构递进) | 1.5 | A→B→C 递进 |
| tone (语言自然) | 0.5 | 不像 AI 写的 |
| stance (观点有立场) | 0.5 | 有明确主张 |

### Guardrails

- **Max 8 rounds** — stops and outputs highest-scoring version
- **Stall detection** — 2 consecutive rounds with same score → pause
- **Hard fails** — undefined concepts, no examples, no practice steps, unsourced facts, AI-tone → auto-fail regardless of score
- **Blind isolation** — Critic Sub-Agent never sees Writer's intent, target reader, or writing instructions

### Writer vs Critic

- **Writer** (`run_writer_round`): Has file tools (bash, read, write, edit, glob). Round 1 writes from scratch; round N only fixes deduction items. Outputs to `drafts/draft-{N}.md`.
- **Critic** (`run_critic`): Pure LLM call (no tools). Only receives draft text + blind rubric. Returns structured JSON with scores, deductions, hard-fail flags.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **my-agent** (855 symbols, 1470 relationships, 62 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> If any GitNexus tool warns the index is stale, run `npx gitnexus analyze` in terminal first.

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `gitnexus_impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `gitnexus_detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `gitnexus_query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `gitnexus_context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `gitnexus_impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `gitnexus_rename` which understands the call graph.
- NEVER commit changes without running `gitnexus_detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/my-agent/context` | Codebase overview, check index freshness |
| `gitnexus://repo/my-agent/clusters` | All functional areas |
| `gitnexus://repo/my-agent/processes` | All execution flows |
| `gitnexus://repo/my-agent/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
