"""plugins.mcp — MCP 外部工具服务器"""

import re
from utils.terminal import terminal_print
from core.state import mcp_clients


class MCPClient:
    def __init__(self, name: str):
        self.name = name; self.tools: list[dict] = []; self._handlers: dict = {}
    def register(self, tool_defs: list[dict], handlers: dict):
        self.tools = tool_defs; self._handlers = handlers
    def call_tool(self, tool_name: str, args: dict) -> str:
        handler = self._handlers.get(tool_name)
        if not handler: return f"MCP error: unknown tool '{tool_name}'"
        try: return handler(**args)
        except Exception as e: return f"MCP error: {e}"

_DISALLOWED_CHARS = re.compile(r'[^a-zA-Z0-9_-]')

def normalize_mcp_name(name: str) -> str:
    return _DISALLOWED_CHARS.sub('_', name)

def _mock_server_docs():
    c = MCPClient("docs")
    c.register(
        [{"name": "search", "description": "Search docs.", "inputSchema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
         {"name": "get_version", "description": "Get API version.", "inputSchema": {"type": "object", "properties": {}, "required": []}}],
        {"search": lambda query: f"[docs] Found 3 results for '{query}'", "get_version": lambda: "[docs] API v2.1.0"})
    return c

def _mock_server_deploy():
    c = MCPClient("deploy")
    c.register(
        [{"name": "trigger", "description": "Trigger deployment.", "inputSchema": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}},
         {"name": "status", "description": "Check deployment status.", "inputSchema": {"type": "object", "properties": {"service": {"type": "string"}}, "required": ["service"]}}],
        {"trigger": lambda service: f"[deploy] Triggered: {service}", "status": lambda service: f"[deploy] {service}: running (v1.4.2)"})
    return c

MOCK_SERVERS = {"docs": _mock_server_docs, "deploy": _mock_server_deploy}

def connect_mcp(name: str) -> str:
    if name in mcp_clients: return f"MCP server '{name}' already connected"
    factory = MOCK_SERVERS.get(name)
    if not factory: return f"Unknown server '{name}'. Available: {', '.join(MOCK_SERVERS.keys())}"
    mcp_client = factory()
    mcp_clients[name] = mcp_client
    tool_names = [t["name"] for t in mcp_client.tools]
    terminal_print(f"  \033[31m[mcp] connected: {name} -> {tool_names}\033[0m")
    return f"Connected to MCP server '{name}'. Tools: {', '.join(tool_names)}"
