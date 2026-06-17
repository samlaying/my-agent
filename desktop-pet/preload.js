// preload.js — contextBridge（当前最小化，后续扩展用）
const { contextBridge } = require('electron');

contextBridge.exposeInMainWorld('petAPI', {
  // 预留：设置、快捷键等
});
