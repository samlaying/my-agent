# Scheduled Recommendations (定时推荐) — Design

**Date:** 2026-06-15  ·  **Status:** Implemented  ·  **Branch:** `main`

## Goal

Add a **scheduled recommendations** system to the agent: on a schedule, the agent
surfaces actionable cards drawn from across its own state (tasks, the project loop,
cron jobs, the tool profile, memory). The backend must be **highly atomized and
decoupled** — every producer is a single file with a pure-data interface.

> Note: an initial plan also included a web frontend + theming layer. That was
> dropped mid-build ("把 web 相关的都删掉"). This spec covers only the backend
> recommendation system that survived.

## Architecture

```
recommenders/ (atomic, one source each)      engine                feed              UI
  task_recommender    ─┐
  loop_recommender    ─┤                       collect()
  cron_recommender    ─┼──► list[Recommendation] ──► dedupe ──► rank ──► persist ──► .agent/recommendations.json
  tool_recommender    ─┤      (try/except per source;           (replace_all,     /reco, recommend tool
  memory_recommender  ─┘       failure → one low-pri card)       preserves status)
```

### `Recommendation` card (`contract.py`)
`id, source, kind, title, reason, priority(1–5), action, created_at, status`.
- `id` uses `stable_id()` (md5, 10 chars) so it survives across processes/refreshes —
  this is what lets the feed dedupe and preserve `dismissed`/`done` status.
- `action` is a pure dict: `{"type": "tool"|"none", "name"?, "args"?}`. No code, no closures.

### Recommenders (`recommenders/*.py`)
Each subclasses `Recommender`, sets `source`, implements `recommend() -> list[Recommendation]`.
They read existing system state via the existing readers (`list_tasks`, `read_loop_state`,
`scheduled_jobs`, `is_tool_enabled`, `MEMORY_DIR`) — no new sources of truth, no coupling
to each other. Adding a recommender = one file + one line in `engine.REGISTERED`.

### Engine (`engine.py`)
- `collect()` runs every registered recommender, each wrapped in try/except (isolation).
  Dedupes by id keeping the higher priority; sorts by `(-priority, source, title)`.
- `run_all()` = `collect()` + `feed.replace_all()` (persist, preserving user status).
- `ensure_scheduled()` registers one idempotent daily cron (durable) if none exists.

### Feed (`feed.py`)
`.agent/recommendations.json`. `replace_all` keeps `dismissed`/`done` cards in their
user-chosen state across refreshes. `set_status` is the single mutation path.

## Integration

- **Tools** (`tools/dispatch.py` + `registry.py`): `recommend`, `list_recommendations`,
  `dismiss_recommendation`. Category `context` → broadly available across profiles.
  Impact on `register_all_handlers`: LOW (0 upstream callers; additive).
- **REPL** (`agent.py`): `/reco` refreshes + summarizes; startup calls `ensure_scheduled()`.
- **Scheduling** reuses the existing cron → `cron_autorun_loop` → `agent_loop` path: the
  daily job injects a prompt that asks the agent to call `recommend`.

## Tests (`tests/test_recommendations.py`)
Contract round-trip, stable-id determinism, feed status preservation & validation,
each recommender (with patched sources), engine dedupe/ranking + failure isolation,
and tool-registration integration. 16 new tests, all green alongside the 4 existing.

## Decisions
- **No new dependencies.** Pure stdlib + existing readers.
- **No web layer.** Removed per user direction.
- **Category `context`** for the tools (like `compact`) rather than `automation`, so they
  reach coding/learning/butler/research profiles without profile churn.
