"""agents.loop_state — LOOP_STATE.md 解析与更新"""

import re
from pathlib import Path
from datetime import date

from core.config import WORKDIR

LOOP_STATE_PATH = WORKDIR / "LOOP_STATE.md"

SECTIONS = ["Inbox", "In Progress", "Done", "Decisions", "Blocked"]

# ── 解析 ──

def read_loop_state() -> dict[str, list[str]]:
    """将 LOOP_STATE.md 解析为 {section_name: [lines]} 字典。"""
    if not LOOP_STATE_PATH.exists():
        return {s: [] for s in SECTIONS}

    text = LOOP_STATE_PATH.read_text()
    sections: dict[str, list[str]] = {}
    current = None

    for line in text.splitlines():
        header = re.match(r'^## (.+)', line)
        if header:
            current = header.group(1).strip()
            sections[current] = []
            continue
        if current is not None:
            sections.setdefault(current, []).append(line)

    # 确保所有标准 section 存在
    for s in SECTIONS:
        sections.setdefault(s, [])
    return sections


def write_loop_state(sections: dict[str, list[str]]):
    """将 sections 字典写回 LOOP_STATE.md，保持格式。"""
    lines = [
        "# Loop State",
        "",
        "> Auto-maintained by project-triage-loop / project-fix-loop.",
        "> Do not edit manually unless blocking an item for human review.",
        "",
    ]
    for section in SECTIONS:
        lines.append(f"## {section}")
        lines.append("")
        content = sections.get(section, [])
        if section == "Decisions" and content:
            # Decisions 表保留表头
            has_header = any("|" in l and "Date" in l for l in content)
            if not has_header:
                lines.append("| Date | Decision | Reason |")
                lines.append("|------|----------|--------|")
        for cl in content:
            lines.append(cl)
        lines.append("")

    LOOP_STATE_PATH.write_text("\n".join(lines) + "\n")


# ── 操作 ──

def add_to_inbox(item: str) -> str:
    sections = read_loop_state()
    inbox = sections["Inbox"]
    # 去重
    stripped = [l.strip("- [] \t") for l in inbox if l.strip()]
    if item in stripped:
        return f"Already in inbox: {item[:60]}"
    # 找到插入位置：在注释行之后
    insert_idx = 0
    for i, line in enumerate(inbox):
        if line.strip().startswith("<!--"):
            insert_idx = i + 1
    inbox.insert(insert_idx, f"- [ ] {item}")
    write_loop_state(sections)
    return f"Added to inbox: {item[:60]}"


def move_to_done(item_hint: str, note: str = "") -> str:
    sections = read_loop_state()
    inbox = sections["Inbox"]
    today = date.today().isoformat()
    removed = None
    for i, line in enumerate(inbox):
        if item_hint.lower() in line.lower():
            removed = inbox.pop(i)
            break
    if not removed:
        return f"Not found in inbox: {item_hint}"
    entry = f"- [x] [{today}] {removed.strip('- [] ')}"
    if note:
        entry += f" — {note}"
    sections["Done"].append(entry)
    write_loop_state(sections)
    return f"Moved to done: {removed.strip()[:60]}"


def move_to_blocked(item_hint: str, reason: str = "") -> str:
    sections = read_loop_state()
    # 在 inbox 和 in-progress 中搜索
    for section_name in ["Inbox", "In Progress"]:
        items = sections[section_name]
        for i, line in enumerate(items):
            if item_hint.lower() in line.lower():
                removed = items.pop(i)
                entry = f"- {removed.strip('- [] ')}"
                if reason:
                    entry += f" — **Blocked:** {reason}"
                sections["Blocked"].append(entry)
                write_loop_state(sections)
                return f"Moved to blocked: {removed.strip()[:60]}"
    return f"Not found: {item_hint}"


def add_decision(decision: str, reason: str) -> str:
    sections = read_loop_state()
    today = date.today().isoformat()
    sections["Decisions"].append(f"| {today} | {decision} | {reason} |")
    write_loop_state(sections)
    return f"Decision recorded: {decision[:60]}"


# ── 工具包装 ──

def run_loop_status() -> str:
    """供 /loop status 调用。"""
    sections = read_loop_state()
    lines = ["[Loop State Summary]"]
    for s in SECTIONS:
        content = [l for l in sections.get(s, []) if l.strip() and not l.strip().startswith("<!--")]
        if s == "Decisions":
            content = [l for l in content if "|" in l and "Date" not in l and "--" not in l]
        lines.append(f"  {s}: {len(content)} item(s)")
    return "\n".join(lines)


def run_loop_triage() -> str:
    """触发 triage：加载 skill 内容，让 agent 在下一轮对话中执行。"""
    from plugins.skills import load_skill
    skill_content = load_skill("project-triage-loop")
    if skill_content.startswith("Skill not found"):
        return skill_content
    # 返回 skill 内容作为注入指令
    return f"[Triage Loop Activated]\n\n{skill_content}"


def run_loop_fix() -> str:
    """触发 fix loop：加载 skill 内容。"""
    from plugins.skills import load_skill
    skill_content = load_skill("project-fix-loop")
    if skill_content.startswith("Skill not found"):
        return skill_content
    # 检查 inbox 是否有候选
    sections = read_loop_state()
    inbox_items = [l for l in sections["Inbox"] if l.strip() and "- [ ]" in l]
    if not inbox_items:
        return "[Fix Loop] No items in Inbox. Run triage first."
    return f"[Fix Loop Activated]\n\nInbox candidates: {len(inbox_items)}\n\n{skill_content}"


def run_loop_inbox_add(item: str) -> str:
    return add_to_inbox(item)


def run_loop_done(item_hint: str, note: str = "") -> str:
    return move_to_done(item_hint, note)


def run_loop_block(item_hint: str, reason: str = "") -> str:
    return move_to_blocked(item_hint, reason)
