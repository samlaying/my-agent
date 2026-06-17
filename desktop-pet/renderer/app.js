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
  // 可选：在气泡里显示工具状态
  if (data.status === 'start') {
    appendBubble(`\n⚙ ${data.tool}...`);
  }
});
