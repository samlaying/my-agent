// ws-client.js — WebSocket 连接管理（一个职责：连上、收消息、断线重连）

const WS_URL = 'ws://localhost:8765';
const RECONNECT_MS = 3000;

let ws = null;
let handlers = {};  // {type: [fn, ...]}

function wsConnect() {
  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    console.log('[ws] connected');
    emit('_open', {});
  };

  ws.onmessage = (e) => {
    try {
      const msg = JSON.parse(e.data);
      emit(msg.type, msg.data || {});
    } catch (_) {}
  };

  ws.onclose = () => {
    console.log('[ws] disconnected');
    emit('_close', {});
    setTimeout(wsConnect, RECONNECT_MS);
  };

  ws.onerror = () => {};  // onclose 会触发
}

function wsSend(type, data) {
  if (ws?.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type, data }));
  }
}

function onMsg(type, fn) {
  (handlers[type] ??= []).push(fn);
}

function emit(type, data) {
  (handlers[type] || []).forEach(fn => fn(data));
}

// 启动连接
wsConnect();
