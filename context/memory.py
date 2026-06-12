"""context.memory — 记忆读取"""

from core.config import MEMORY_INDEX


def update_context(context: dict, messages: list) -> dict:
    from core.state import mcp_clients, active_teammates
    memories = MEMORY_INDEX.read_text()[:2000] if MEMORY_INDEX.exists() else ""
    return {"memories": memories,
            "connected_mcp": list(mcp_clients.keys()),
            "active_teammates": list(active_teammates.keys())}
