import { app, BrowserWindow, ipcMain, dialog, Menu } from "electron";
import path from "path";
import { fileURLToPath } from "url";
import fs from "fs/promises";
import mammoth from "mammoth"; 

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 500,
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

// open file explorer, accept file types
ipcMain.handle("dialog:openFile", async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog(mainWindow, {
    properties: ["openFile", "multiSelections"],
    filters: [
      { name: "Text Files", extensions: ["txt"] },
      { name: "Word Documents", extensions: ["doc", "docx"] },
    ]
  });

  if (canceled) return null;

  const filesWithContent = [];

  for (const filePath of filePaths) {
    const ext = path.extname(filePath).toLowerCase();
    let content = "";

    try {
      if (ext === ".txt") {
        content = await fs.readFile(filePath, "utf-8");
      } else if (ext === ".docx") {
        const result = await mammoth.extractRawText({ path: filePath });
        content = result.value;
      } else if (ext === ".doc") {
        content = `[DOC file not supported yet]`;
      }
    } catch (err) {
      content = `[Error reading file]`;
    }

    filesWithContent.push({ path: filePath, content });
  }

  return filesWithContent;
});


app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
