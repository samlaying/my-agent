#!/usr/bin/env python3
"""
my-agent: 综合编码 agent（模块化版）
基于 learn-claude-code s20 架构，拆分为 10 个包。

Run:  cd my-agent && python3 agent.py
"""

import json
import subprocess

# ── 注册所有 handler ──
from tools.dispatch import register_all_handlers, assemble_all_tool_pool, assemble_tool_pool
register_all_handlers()

# ── 各模块导入 ──
import core.config as cfg
from core.config import WORKDIR
from core.state import CLI_ACTIVE
from tracing.turn_logger import (log_session_start, log_session_end,
                                 log_user_input, LOG_FILE)
from tools.hooks import trigger_hooks
from agents.loop import agent_loop, cron_autorun_loop, print_turn_assistants
from context.memory import update_context
from tasks.task import run_list_tasks
from scheduler.cron import run_list_crons
from teams.bus import BUS
from teams.protocol import consume_lead_inbox
from core.state import active_teammates


if __name__ == "__main__":
    CLI_ACTIVE = True
    tools, _ = assemble_tool_pool()
    print(f"my-agent: comprehensive coding agent (model: {cfg.MODEL})")
    print("Commands: q/exit, /tasks, /team, /inbox, /compact, /crons, /logs, /loop, /model, /tools, /profile")
    print(f"Working directory: {WORKDIR}")
    print(f"Turn log: {LOG_FILE}\n")

    if not (WORKDIR / ".git").exists():
        subprocess.run(["git", "init"], cwd=WORKDIR, capture_output=True)
        print("[init] Created git repo for worktree support\n")

    log_session_start(tools_count=len(tools))

    history = []
    context = update_context({}, [])
    import threading
    threading.Thread(target=cron_autorun_loop, args=(history, context), daemon=True).start()

    while True:
        try:
            query = input("\033[36magent >> \033[0m")
        except (EOFError, KeyboardInterrupt):
            break
        if query.strip().lower() in ("q", "exit"):
            break
        if not query.strip():
            continue

        if query.strip() == "/tasks":
            print(run_list_tasks()); continue
        if query.strip() == "/team":
            print(f"Active: {', '.join(active_teammates.keys()) or 'none'}"); continue
        if query.strip() == "/inbox":
            from teams.bus import run_check_inbox
            print(run_check_inbox()); continue
        if query.strip() == "/compact":
            from context.compaction import compact_history
            if history: print("[manual compact]"); history[:] = compact_history(history)
            continue
        if query.strip() == "/crons":
            print(run_list_crons()); continue
        if query.strip().startswith("/loop"):
            from agents.loop_state import run_loop_status, run_loop_triage, run_loop_fix, add_to_inbox
            parts = query.strip().split(maxsplit=1)
            subcmd = parts[1] if len(parts) > 1 else "status"
            if subcmd == "status":
                print(run_loop_status())
            elif subcmd == "triage":
                print(run_loop_triage())
            elif subcmd == "fix":
                print(run_loop_fix())
            elif subcmd.startswith("add "):
                print(add_to_inbox(subcmd[4:]))
            else:
                print("/loop [status|triage|fix|add <item>]")
            continue
        if query.strip().startswith("/model"):
            from core.config import list_providers, switch_model
            parts = query.strip().split(maxsplit=1)
            if len(parts) < 2:
                print(list_providers())
                print("\n用法: /model <供应商名>  切换模型")
                print("  e.g. /model xiaomi")
                print("  e.g. /model zhipu")
            else:
                result = switch_model(parts[1].strip())
                print(result)
                if not result.startswith("Error"):
                    tools, _ = assemble_tool_pool()
                    print(f"  工具池已刷新，共 {len(tools)} 个工具")
            continue
        if query.strip().startswith("/tools"):
            from tools.registry import list_tool_status, set_tool_enabled
            parts = query.strip().split(maxsplit=2)
            if len(parts) == 1:
                all_tools, _ = assemble_all_tool_pool()
                print(list_tool_status(all_tools))
            elif len(parts) == 3 and parts[1] in ("on", "off"):
                print(set_tool_enabled(parts[2], parts[1] == "on"))
                tools, _ = assemble_tool_pool()
                print(f"  工具池已刷新，共 {len(tools)} 个工具")
            else:
                print("/tools [on|off <tool_name>]")
            continue
        if query.strip().startswith("/profile"):
            from tools.registry import set_active_profile
            parts = query.strip().split(maxsplit=1)
            profile_name = parts[1].strip() if len(parts) > 1 else None
            print(set_active_profile(profile_name))
            tools, _ = assemble_tool_pool()
            print(f"  工具池已刷新，共 {len(tools)} 个工具")
            continue
        if query.strip() == "/logs":
            print(f"Log file: {LOG_FILE}")
            if LOG_FILE.exists():
                lines = LOG_FILE.read_text().strip().splitlines()
                print(f"Events: {len(lines)}")
                for line in lines[-20:]:
                    evt = json.loads(line)
                    e = evt.get("event", "?"); t = str(evt.get("turn", "-"))
                    ts = evt.get("time", "")
                    if e == "user_input":
                        print(f"  [{ts}] #{t} USER: {evt['content'][:80]}")
                    elif e == "llm_response":
                        tools_s = ", ".join(x["name"] for x in evt.get("tool_calls", []))
                        print(f"  [{ts}] #{t} LLM: {evt['stop_reason']} {evt['latency_ms']:.0f}ms | {tools_s or '(text)'}")
                    elif e == "tool_execution":
                        s = "BLOCKED" if evt.get("blocked") else "OK"
                        print(f"  [{ts}] #{t} TOOL: {evt['tool']} {s} {evt['latency_ms']:.0f}ms")
                    elif e == "error":
                        print(f"  [{ts}] #{t} ERROR: {evt['error_type']}")
            continue

        log_user_input(query)
        trigger_hooks("UserPromptSubmit", query)
        turn_start = len(history)
        history.append({"role": "user", "content": query})
        from agents.loop import agent_lock
        with agent_lock:
            agent_loop(history, context)
            context = update_context(context, history)
            print_turn_assistants(history, turn_start)

        inbox = consume_lead_inbox(route_protocol=True)
        if inbox:
            inbox_text = "\n".join(f"From {m['from']} [{m.get('type','message')}]: {m['content'][:200]}" for m in inbox)
            history.append({"role": "user", "content": f"[Inbox]\n{inbox_text}"})
        print()

    log_session_end()
