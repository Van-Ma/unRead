import { app, BrowserWindow, ipcMain, dialog, Menu } from "electron";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs/promises";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 600,
    minHeight: 500,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  mainWindow.loadURL("http://localhost:5173");
  Menu.setApplicationMenu(null);
}

app.whenReady().then(createWindow);

const API_URL = "http://localhost:5000";
const FILE_FILTERS = [{ name: "Documents", extensions: ["txt", "docx", "pdf", "xlsx"] }];

// .txt is read directly; other formats are parsed by the backend
async function readContent(filePath) {
  try {
    if (path.extname(filePath).toLowerCase() === ".txt") return await fs.readFile(filePath, "utf-8");
    const res = await fetch(`${API_URL}/parse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: filePath }),
    });
    const data = await res.json();
    return res.ok ? data.text : `[Error reading file: ${data.error}]`;
  } catch (err) {
    return `[Error reading file: ${err.message}]`;
  }
}

async function pickFiles() {
  const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile", "multiSelections"],
    filters: FILE_FILTERS,
  });
  return canceled ? [] : filePaths;
}

ipcMain.handle("dialog:openFile", async () => {
  const filePaths = await pickFiles();
  if (filePaths.length === 0) return null;
  return Promise.all(filePaths.map(async p => ({ path: p, content: await readContent(p) })));
});

ipcMain.handle("dialog:pickFiles", pickFiles);
ipcMain.handle("file:read", (_event, filePath) => readContent(filePath));

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
