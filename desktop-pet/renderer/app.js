// app.js — 薄粘合层（连接 ws-client、bubble、mood）

// ── 情绪切换 ──
function setMood(mood) {
  const pet = document.getElementById('pet');
  if (pet) pet.className = `pet mood-${mood}`;
}

// ── WS 事件绑定 ──
onMsg('_open',  () => setMood('idle'));
onMsg('_close', () => setMood('sad'));

onMsg('mood', (data) => setMood(data.mood || 'idle'));

onMsg('bubble', (data) => {
  showBubble(data.text, data.kind, data.duration);
});

onMsg('assistant_text', (data) => {
  appendBubble(data.text);
});

onMsg('tool_activity', (data) => {
  if (data.status === 'start') {
    appendBubble(`\n⚙ ${data.tool}...`);
  }
});

// ── 全屏提醒 ──
onMsg('reminder', (data) => {
  // 通知主进程创建全屏 overlay
  if (window.reminderAPI) {
    window.reminderAPI.showOverlay(data);
  }
});

// ── 主进程转发 WS 消息（snooze 等）──
if (window.reminderAPI && window.reminderAPI.onWSSend) {
  window.reminderAPI.onWSSend((msg) => {
    wsSend(msg.type, msg.data);
  });
}
