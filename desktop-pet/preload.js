// preload.js — contextBridge
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('petAPI', {
  // 预留：设置、快捷键等
});

// 提醒 overlay 相关 API（overlay.html 和主渲染进程共用）
contextBridge.exposeInMainWorld('reminderAPI', {
  dismiss: () => ipcRenderer.send('reminder-dismiss'),
  snooze: (id, minutes) => ipcRenderer.send('reminder-snooze', { id, minutes }),
  showOverlay: (data) => ipcRenderer.send('show-reminder-overlay', data),
  onWSSend: (callback) => ipcRenderer.on('ws-send', (_event, data) => callback(data)),
});
