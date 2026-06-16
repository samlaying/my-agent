"""context.memory — profile-aware memory retrieval."""

from __future__ import annotations

import json
import re
from pathlib import Path

from agents.profile import DEFAULT_PROFILE, AgentProfile, MemoryPolicy
from core.config import MEMORY_DIR, MEMORY_INDEX


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in re.findall(r"[\w\u4e00-\u9fff]+", text)}


class MemoryService:
    def __init__(self, root: Path = MEMORY_DIR):
        self.root = root
        self.shared_dir = root / "shared"
        self.state_path = root / "state.json"
        self.shared_dir.mkdir(parents=True, exist_ok=True)

    def _namespace_files(self, namespace: str) -> list[Path]:
        files: list[Path] = []
        md_file = self.root / f"{namespace}.md"
        if md_file.exists():
            files.append(md_file)
        namespace_dir = self.root / namespace
        if namespace_dir.exists():
            files.extend(sorted(namespace_dir.glob("*.md")))
        return files

    def get_state(self) -> dict:
        """读取全局时空状态。不存在则返回空 dict。"""
        if not self.state_path.exists():
            return {}
        try:
            return json.loads(self.state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def set_state(self, key: str, value: str) -> None:
        """更新全局状态并持久化。"""
        state = self.get_state()
        state[key] = value
        self.state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def retrieve(self, query: str, policy: MemoryPolicy) -> str:
        query_tokens = _tokens(query)
        chunks: list[tuple[int, str, str]] = []

        for namespace in policy.namespaces:
            for path in self._namespace_files(namespace):
                try:
                    text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                score = len(query_tokens & _tokens(text)) if query_tokens else 0
                if namespace == "shared":
                    score *= 2  # shared namespace 加权
                chunks.append((score, namespace, text.strip()))

        if not chunks and MEMORY_INDEX.exists():
            chunks.append((0, "legacy", MEMORY_INDEX.read_text(encoding="utf-8").strip()))

        chunks.sort(key=lambda item: item[0], reverse=True)
        output: list[str] = []
        remaining = policy.max_chars
        for _, namespace, text in chunks:
            if remaining <= 0:
                break
            labeled = f"[{namespace}]\n{text}"
            output.append(labeled[:remaining])
            remaining -= len(output[-1])
        return "\n\n".join(output)


def _recent_query(messages: list, max_messages: int) -> str:
    recent = messages[-max_messages:] if messages else []
    parts: list[str] = []
    for msg in recent:
        content = msg.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    parts.append(str(block.get("text", block.get("content", ""))))
                else:
                    parts.append(str(getattr(block, "text", "")))
    return "\n".join(parts)


def update_context(context: dict, messages: list, profile: AgentProfile | None = None) -> dict:
    from core.state import mcp_clients, active_teammates

    active_profile = profile or DEFAULT_PROFILE
    query = _recent_query(messages, active_profile.memory.query_recent_messages)
    memories = MemoryService().retrieve(query, active_profile.memory)
    return {"memories": memories,
            "memory_namespaces": active_profile.memory.namespaces,
            "connected_mcp": list(mcp_clients.keys()),
            "active_teammates": list(active_teammates.keys())}
