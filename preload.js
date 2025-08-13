const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('secureStorage', {
  saveToken: (token) => ipcRenderer.invoke('save-token', token),
  getToken: () => ipcRenderer.invoke('get-token'),
  deleteToken: () => ipcRenderer.invoke('delete-token'),
});