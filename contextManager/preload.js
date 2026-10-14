const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  openFile: () => ipcRenderer.invoke("dialog:openFile"),
  pickFiles: () => ipcRenderer.invoke("dialog:pickFiles"),
  readFile: (filePath) => ipcRenderer.invoke("file:read", filePath),
});
