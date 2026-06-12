# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A modular Python coding agent framework built on the Anthropic Messages API. It implements a REPL-based agent with 20+ mechanisms (tool use, subagents, teammate threads, cron scheduling, task management, context compaction, hook system, MCP plugin support, background execution, memory) across 10 packages. Based on the learn-claude-code s20 architecture.

## Running

```bash
cd my-agent && python3 agent.py
```

Requires `ANTHROPIC_API_KEY` (and optionally `ANTHROPIC_BASE_URL`, `MODEL_ID`) in `.env`. Dependencies: `anthropic>=0.25.0`, `python-dotenv>=1.0.0` (`pip install -r requirements.txt`).

There are no tests or linter configured.

## REPL Slash Commands

| Command | Action |
|---|---|
| `/tasks` | List file-backed tasks |
| `/team` | Show active teammate threads |
| `/inbox` | Consume lead agent inbox from mailbox bus |
| `/compact` | Force context compaction |
| `/crons` | List scheduled cron jobs |
| `/logs` | Tail the JSONL turn log |
| `/loop [status\|triage\|fix\|add <item>]` | Loop Engineering system |

## Architecture

Entry point is `agent.py` — a REPL that registers handlers, starts a cron daemon thread, and runs `agent_loop` per user input. The 10 packages:

| Package | Purpose |
|---|---|
| `core/` | `config.py` — env vars, Anthropic client, path constants, thresholds. `state.py` — mutable global state (todos, teammates, MCP clients, background tasks). |
| `agents/` | `loop.py` — main agentic loop (LLM call → tool execution → context management → repeat). `recovery.py` — retry with exponential backoff, model fallback on 529s. `subagent.py` — isolated single-task agent with its own tool set. `teammate.py` — long-lived autonomous threads with inbox polling, plan approval protocol, auto-task-claiming. `loop_state.py` — parses and updates `LOOP_STATE.md` for the Loop Engineering system. |
| `context/` | `system_prompt.py` — dynamic prompt assembly (tools, skills, memories, MCP). `compaction.py` — four-tier context compression: tool_result_budget → snip_compact → micro_compact → full LLM summarize. `memory.py` — reads `.memory/MEMORY.md` into context. |
| `tools/` | `dispatch.py` — tool schema definitions + handler registry (`register_all_handlers` wires everything at startup). `builtin.py` — bash, read/write/edit, glob, todo_write implementations. `hooks.py` — event hooks (UserPromptSubmit, PreToolUse, PostToolUse, Stop) with permission checking. |
| `tasks/` | `task.py` — file-backed task system (`.tasks/*.json`) with dependency graph (blockedBy). `worktree.py` — git worktree CRUD with branch `wt/{name}`. |
| `scheduler/` | `cron.py` — 5-field cron parser + persistent scheduler (`.scheduled_tasks.json`). Fires jobs into the cron queue consumed by agent_loop. |
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

## Tool Catalog (35 Builtin)

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
