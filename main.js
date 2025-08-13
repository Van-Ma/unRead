// Auto-reload for development
require('electron-reload')(__dirname, {
  electron: require(`${__dirname}/node_modules/electron`),
});

const { app, BrowserWindow, ipcMain, Menu } = require('electron');
const path = require('path');
const keytar = require('keytar');

const SERVICE_NAME = 'Unread';
const ACCOUNT_NAME = 'oauth_token';

function createWindow() {
  const win = new BrowserWindow({
    width: 1000,
    height: 700,
    minWidth: 800,
    minHeight: 600,
    icon: path.join(__dirname, 'images/logoicon.ico'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadURL('http://localhost:5173');

  Menu.setApplicationMenu(null);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

// IPC handlers for secure token storage
ipcMain.handle('save-token', async (event, token) => {
  await keytar.setPassword(SERVICE_NAME, ACCOUNT_NAME, token);
  return true;
});

ipcMain.handle('get-token', async () => {
  const token = await keytar.getPassword(SERVICE_NAME, ACCOUNT_NAME);
  return token;
});

ipcMain.handle('delete-token', async () => {
  await keytar.deletePassword(SERVICE_NAME, ACCOUNT_NAME);
  return true;
});
