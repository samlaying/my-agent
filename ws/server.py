"""ws.server — 纯 WebSocket 服务器，不知道 agent 的存在"""

import asyncio
import json
import threading


class WSServer:
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.clients: set = set()
        self.loop: asyncio.AbstractEventLoop | None = None
        self.on_message = None  # async def on_message(msg: dict, ws) -> None

    async def _handler(self, websocket):
        self.clients.add(websocket)
        try:
            async for raw in websocket:
                try:
                    msg = json.loads(raw)
                    if self.on_message:
                        await self.on_message(msg, websocket)
                except json.JSONDecodeError:
                    pass
        finally:
            self.clients.discard(websocket)

    async def _run_server(self):
        import websockets.asyncio.server as ws_server
        server = await ws_server.serve(self._handler, self.host, self.port)
        print(f"[ws] listening on ws://{self.host}:{self.port}")
        await server.wait_closed()

    async def broadcast(self, message: dict):
        """广播消息到所有客户端"""
        payload = json.dumps(message, ensure_ascii=False)
        for ws in list(self.clients):
            try:
                await ws.send(payload)
            except Exception:
                self.clients.discard(ws)

    def send_sync(self, message: dict):
        """线程安全广播（从 agent 同步线程调用）"""
        if self.loop:
            asyncio.run_coroutine_threadsafe(self.broadcast(message), self.loop)

    def start(self):
        """在守护线程中启动 WS 服务器"""
        def _run():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self._run_server())

        t = threading.Thread(target=_run, daemon=True)
        t.start()
