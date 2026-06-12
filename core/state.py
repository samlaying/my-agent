"""core.state — 全局可变状态，集中管理"""

CURRENT_TODOS: list[dict] = []
CLI_ACTIVE = False
mcp_clients: dict = {}
active_teammates: dict[str, bool] = {}
rounds_since_todo = 0
_bg_counter = 0
background_tasks: dict[str, dict] = {}
background_results: dict[str, str] = {}
