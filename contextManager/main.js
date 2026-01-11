import { app, BrowserWindow } from "electron";
import path from "path";

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 500,    
    minHeight: 300,   
    webPreferences: {
      preload: path.join(process.cwd(), "preload.js"), 
      nodeIntegration: true,
      contextIsolation: false,
    },
  });


  mainWindow.loadURL("http://localhost:5173");
}

app.whenReady().then(createWindow);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
