"""agents.teammate — 自治队友线程"""

import json, time, threading
from core.config import client, MODEL, IDLE_POLL_INTERVAL, IDLE_TIMEOUT, WORKTREES_DIR
from core.state import active_teammates
from teams.bus import BUS
from teams.protocol import pending_requests, ProtocolState, new_request_id
from tasks.task import claim_task, complete_task, list_tasks, scan_unclaimed_tasks
from tools.builtin import run_bash, run_read, run_write, call_tool_handler
from utils.terminal import terminal_print

def _has_tool_use(content) -> bool:
    return any(getattr(b, "type", None) == "tool_use" for b in content)

def spawn_teammate_thread(name: str, role: str, prompt: str) -> str:
    if name in active_teammates: return f"Teammate '{name}' already exists"
    protocol_ctx = {"waiting_plan": None}
    system = f"You are '{name}', a {role}. Use tools to complete tasks."

    def run():
        wt_ctx = {"path": None}
        def _wt_cwd():
            from pathlib import Path
            return Path(wt_ctx["path"]) if wt_ctx["path"] else None

        messages = [{"role": "user", "content": prompt}]
        sub_tools = [
            {"name": "bash", "description": "Run shell.", "input_schema": {"type": "object", "properties": {"command": {"type": "string"}}, "required": ["command"]}},
            {"name": "read_file", "description": "Read.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
            {"name": "write_file", "description": "Write.", "input_schema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
            {"name": "send_message", "description": "Send msg.", "input_schema": {"type": "object", "properties": {"to": {"type": "string"}, "content": {"type": "string"}}, "required": ["to", "content"]}},
            {"name": "submit_plan", "description": "Submit plan.", "input_schema": {"type": "object", "properties": {"plan": {"type": "string"}}, "required": ["plan"]}},
            {"name": "list_tasks", "description": "List tasks.", "input_schema": {"type": "object", "properties": {}, "required": []}},
            {"name": "claim_task", "description": "Claim.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
            {"name": "complete_task", "description": "Complete.", "input_schema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
        ]
        sub_handlers = {
            "bash": lambda command: run_bash(command, cwd=_wt_cwd()),
            "read_file": lambda path: run_read(path, cwd=_wt_cwd()),
            "write_file": lambda path, content: run_write(path, content, cwd=_wt_cwd()),
            "send_message": lambda to, content: (BUS.send(name, to, content), "Sent")[1],
            "list_tasks": lambda: "\n".join(f"  {t.id}: {t.subject} [{t.status}]" for t in list_tasks()) or "No tasks.",
            "claim_task": lambda task_id: claim_task(task_id, owner=name),
            "complete_task": lambda task_id: complete_task(task_id),
        }

        while True:
            if len(messages) <= 3:
                messages.insert(0, {"role": "user", "content": f"<identity>You are '{name}', role: {role}.</identity>"})
            should_shutdown = False
            for _ in range(10):
                inbox = BUS.read_inbox(name)
                for msg in inbox:
                    if msg.get("type") == "shutdown_request":
                        req_id = msg.get("metadata", {}).get("request_id", "")
                        BUS.send(name, "lead", "Shutting down.", "shutdown_response", {"request_id": req_id, "approve": True})
                        should_shutdown = True; break
                    if msg.get("type") == "plan_approval_response":
                        meta = msg.get("metadata", {})
                        if meta.get("request_id") == protocol_ctx["waiting_plan"]: protocol_ctx["waiting_plan"] = None
                        messages.append({"role": "user", "content": "[Plan approved]" if meta.get("approve") else f"[Plan rejected] {msg['content']}"})
                if should_shutdown: break
                if protocol_ctx["waiting_plan"]: time.sleep(IDLE_POLL_INTERVAL); continue
                try:
                    response = client.messages.create(model=MODEL, system=system, messages=messages[-20:], tools=sub_tools, max_tokens=8000)
                except Exception: break
                messages.append({"role": "assistant", "content": response.content})
                if not _has_tool_use(response.content): break
                results = []
                for block in response.content:
                    if block.type != "tool_use": continue
                    if block.name == "submit_plan":
                        req_id = new_request_id()
                        pending_requests[req_id] = ProtocolState(req_id, "plan_approval", name, "lead", "pending", block.input.get("plan", ""))
                        BUS.send(name, "lead", block.input.get("plan", ""), "plan_approval_request", {"request_id": req_id})
                        output = f"Plan submitted ({req_id})"
                        protocol_ctx["waiting_plan"] = req_id
                    else:
                        handler = sub_handlers.get(block.name)
                        output = call_tool_handler(handler, block.input, block.name)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": str(output)})
                    if protocol_ctx["waiting_plan"]: break
                messages.append({"role": "user", "content": results})
                if protocol_ctx["waiting_plan"]: break
            if should_shutdown: break
            if protocol_ctx["waiting_plan"]: continue

            # idle poll
            for _ in range(IDLE_TIMEOUT // IDLE_POLL_INTERVAL):
                time.sleep(IDLE_POLL_INTERVAL)
                inbox = BUS.read_inbox(name)
                if inbox:
                    for msg in inbox:
                        if msg.get("type") == "shutdown_request":
                            req_id = msg.get("metadata", {}).get("request_id", "")
                            BUS.send(name, "lead", "Shutting down.", "shutdown_response", {"request_id": req_id, "approve": True})
                            should_shutdown = True; break
                    if should_shutdown: break
                    messages.append({"role": "user", "content": "<inbox>" + json.dumps(inbox) + "</inbox>"})
                    break
                unclaimed = scan_unclaimed_tasks()
                if unclaimed:
                    td = unclaimed[0]
                    result = claim_task(td["id"], name)
                    if "Claimed" in result:
                        wt_info = f"\nWork: {WORKTREES_DIR / td['worktree']}" if td.get("worktree") else ""
                        if td.get("worktree"): wt_ctx["path"] = str(WORKTREES_DIR / td["worktree"])
                        messages.append({"role": "user", "content": f"<auto-claimed>Task {td['id']}: {td['subject']}{wt_info}</auto-claimed>"})
                        break
            else:
                break

        summary = "Done."
        for msg in reversed(messages):
            if msg["role"] == "assistant" and isinstance(msg["content"], list):
                for b in msg["content"]:
                    if getattr(b, "type", None) == "text": summary = b.text; break
                else: continue
                break
        BUS.send(name, "lead", summary, "result")
        active_teammates.pop(name, None)

    active_teammates[name] = True
    threading.Thread(target=run, daemon=True).start()
    return f"Teammate '{name}' spawned as {role}"
