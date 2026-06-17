// main.js — Electron 主进程：创建透明浮窗 + 全屏提醒 overlay
const { app, BrowserWindow, screen, ipcMain } = require('electron');
const path = require('path');

let mainWindow;
let overlayWindow = null;

function createWindow() {
  const { width: screenW, height: screenH } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 200,
    height: 280,
    x: screenW - 240,
    y: screenH - 320,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    hasShadow: false,
    resizable: false,
    skipTaskbar: true,
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadFile('renderer/index.html');
  mainWindow.setVisibleOnAllWorkspaces(true);
}

function createOverlay(reminderData) {
  // 防止重复弹出同一个提醒
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.focus();
    return;
  }

  const { width, height } = screen.getPrimaryDisplay().bounds;

  overlayWindow = new BrowserWindow({
    width,
    height,
    x: 0,
    y: 0,
    frame: false,
    alwaysOnTop: true,
    fullscreen: true,
    skipTaskbar: true,
    backgroundColor: '#ffffff',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const { id, message, snooze_min } = reminderData;
  const params = new URLSearchParams({
    id: id || '',
    message: message || 'Time to take a break!',
    snooze: String(snooze_min || 10),
  });

  overlayWindow.loadFile('renderer/overlay.html', { search: params.toString() });

  overlayWindow.on('closed', () => {
    overlayWindow = null;
  });
}

// ── IPC：来自 overlay 的操作 ──
ipcMain.on('reminder-dismiss', () => {
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.close();
  }
});

ipcMain.on('reminder-snooze', (_event, data) => {
  // data.minutes 可以是数字或 'today'
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send('ws-send', {
      type: 'snooze',
      data: { id: data.id, minutes: data.minutes },
    });
  }
  if (overlayWindow && !overlayWindow.isDestroyed()) {
    overlayWindow.close();
  }
});

// ── 来自 renderer 的 overlay 请求 ──
ipcMain.on('show-reminder-overlay', (_event, data) => {
  createOverlay(data);
});

app.whenReady().then(createWindow);
app.on('window-all-closed', () => app.quit());
