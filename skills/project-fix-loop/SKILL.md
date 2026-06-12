---
name: project-fix-loop
description: Use this skill to fix exactly one high-confidence item from LOOP_STATE.md Inbox. Works in a worktree, makes the smallest change, runs tests, updates state.
---

You are running a project fix loop. You will fix **exactly one** item from the Inbox.

## Protocol

### Step 1 — Pick One Item
Read `LOOP_STATE.md`. Pick the **highest-confidence** item from Inbox:
- Must be well-understood (no ambiguity).
- Must be low-risk (no security, no breaking API changes).
- If no item meets this bar, report "No safe fix candidates" and stop.

### Step 2 — Worktree Isolation
Before making any change:
- Use `create_worktree` with a descriptive name based on the fix.
- All file operations must happen within that worktree.

### Step 3 — Smallest Change
Make the **minimum** code change to resolve the issue:
- One file is better than two.
- Prefer editing existing code over adding new files.
- Do not refactor surrounding code.

### Step 4 — Verify
Run the relevant tests:
- If a test runner exists (`pytest`, `make test`), run it.
- If no tests exist, run `python3 -c "import <module>"` or equivalent smoke test.
- If tests fail for **unrelated** reasons, record evidence and stop — do not attempt to fix.

### Step 5 — Update State
Update `LOOP_STATE.md`:
- Move the item from **Inbox** to **Done** with today's date.
- Note what was changed and the worktree name in the Done entry.
- If tests passed: mark the item `[passed]`.
- If tests failed or you stopped: move item to **Blocked** with reason.

### Step 6 — Report
```
[Fix Summary]
Item: <description>
Worktree: <name>
Files changed: N
Tests: passed / failed / no-runner
Status: done / blocked
```

## Hard Rules
- Fix **exactly one** item per run.
- Always work in a worktree — never edit the main working tree.
- Do **not** commit unless explicitly asked.
- If tests fail for unrelated reasons, record evidence and **stop**.
- If anything is ambiguous or risky, move to Blocked and stop.
