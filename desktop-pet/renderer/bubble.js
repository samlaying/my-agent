// bubble.js — 气泡渲染（一个职责：显示/消失气泡）

let currentBubble = null;
let bubbleTimer = null;

function showBubble(text, kind, duration) {
  const container = document.getElementById('bubble-container');
  if (!container) return;

  // 移除旧气泡
  if (currentBubble) {
    currentBubble.classList.add('bubble-exit');
    const old = currentBubble;
    setTimeout(() => old.remove(), 200);
    currentBubble = null;
    clearTimeout(bubbleTimer);
  }

  const el = document.createElement('div');
  el.className = `bubble ${kind || 'message'}`;
  el.textContent = text;
  container.appendChild(el);
  currentBubble = el;

  // 自动消失
  if (duration > 0) {
    bubbleTimer = setTimeout(() => {
      el.classList.add('bubble-exit');
      setTimeout(() => { el.remove(); currentBubble = null; }, 200);
    }, duration);
  }
}

function appendBubble(text) {
  if (!currentBubble) showBubble('', 'message', 0);
  currentBubble.textContent += text;
  currentBubble.scrollTop = currentBubble.scrollHeight;
}
