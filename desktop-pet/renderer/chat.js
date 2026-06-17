// chat.js — 聊天输入（一个职责：发消息）

(function() {
  const input = document.getElementById('chat-input');
  if (!input) return;

  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      wsSend('user_message', { text });
      showBubble(text, 'user', 0);
      input.value = '';
    }
  });

  // 失焦后自动收起（延迟，避免点按钮时立即收起）
  input.addEventListener('blur', () => {
    setTimeout(() => { input.value = ''; }, 200);
  });
})();
