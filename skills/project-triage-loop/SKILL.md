---
name: project-triage-loop
description: Use this skill to run recurring project triage: inspect git status, recent commits, test failures, issues in local notes, update LOOP_STATE.md, and report only actionable findings.
---

You are running a recurring project triage loop.

## Protocol

### Step 1 — Read State
Read `LOOP_STATE.md` first. Understand what is already known, in progress, done, or blocked.

### Step 2 — Inspect
Run only **lightweight** checks unless asked otherwise:
- `git status` — uncommitted changes, untracked files.
- `git log --oneline -10` — recent commits, spot anomalies.
- Check if `requirements.txt` / `package.json` / `pyproject.toml` exist and scan for outdated or conflicting deps (read only).
- Check if test runner is configured (`pytest`, `make test`, etc.) — note its existence but do **not** run it.
- Scan for TODO/FIXME/HACK comments in source files (light grep).
- Check for large files that should be gitignored.
- Verify `.gitignore` covers common patterns (`__pycache__`, `.env`, `node_modules`, etc.).

### Step 3 — Classify Findings
For each finding, classify into one of:
- **Inbox** — new actionable issue (e.g., stale dependency, missing test, gitignored leak).
- **Blocked** — needs human judgment (e.g., ambiguous API change, security decision).
- **Already known** — skip if already in Inbox/In Progress/Done.

### Step 4 — Update State
Update `LOOP_STATE.md`:
- Add new findings to **Inbox** with `- [ ] <description>` format.
- Move resolved items to **Done** with date prefix.
- Add any decisions to **Decisions** table (Date / Decision / Reason).
- Add risky/ambiguous items to **Blocked** with a brief reason.

### Step 5 — Report
Print a summary:
```
[Triage Summary]
New findings: N
Blocked items: N
Total inbox: N
```

## Hard Rules
- **Do NOT** make product/code changes.
- **Do NOT** create commits.
- **Do NOT** install packages.
- If something is risky or ambiguous, add to Blocked and stop.
- Stop condition: LOOP_STATE.md is updated or confirmed current.
