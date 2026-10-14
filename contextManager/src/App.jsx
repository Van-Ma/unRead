import { useEffect, useRef, useState } from "react";
import ChatManager from "./components/ChatManager";
import FileManager from "./components/FileManager";
import { api } from "./api";

import './styles/App.scss';
import './styles/filemanager.scss';
import './styles/chatmanager.scss';
import './styles/contextmanager.scss';

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [folders, setFolders] = useState([]);
  const [activeFolderId, setActiveFolderId] = useState(null);
  const [loaded, setLoaded] = useState(false);
  const saved = useRef({}); // folder id -> last JSON sent to the backend

  // load folders from the backend
  useEffect(() => {
    api("/folders")
      .then(list => {
        saved.current = Object.fromEntries(list.map(f => [String(f.id), JSON.stringify(f)]));
        setFolders(list);
      })
      .catch(err => console.error("Loading folders failed:", err))
      .finally(() => setLoaded(true));
  }, []);

  // save changed folders, delete removed ones
  useEffect(() => {
    if (!loaded) return;
    const current = Object.fromEntries(folders.map(f => [String(f.id), f]));
    for (const [id, folder] of Object.entries(current)) {
      const json = JSON.stringify(folder);
      if (saved.current[id] === json) continue;
      saved.current[id] = json;
      api(`/folders/${id}`, { method: "PUT", body: folder }).catch(err => console.error("Saving folder failed:", err));
    }
    for (const id of Object.keys(saved.current)) {
      if (current[id]) continue;
      delete saved.current[id];
      api(`/folders/${id}`, { method: "DELETE" }).catch(err => console.error("Deleting folder failed:", err));
    }
  }, [folders, loaded]);

  return (
    <div className="app-container">
      <nav className="tab-bar">
        <button
          className={activeTab === "files" ? "active" : ""}
          onClick={() => setActiveTab("files")}
        >
          File Manager
        </button>
        <button
          className={activeTab === "chat" ? "active" : ""}
          onClick={() => setActiveTab("chat")}
        >
          Chat
        </button>
      </nav>

      <div className="tab-content">
        {/* File Manager */}
        <div style={{ display: activeTab === "files" ? "block" : "none" }}>
          <FileManager
            folders={folders}
            setFolders={setFolders}
            activeFolderId={activeFolderId}
            setActiveFolderId={setActiveFolderId}
          />
        </div>

        {/* Chat Manager */}
        <div style={{ display: activeTab === "chat" ? "block" : "none" }}>
          <ChatManager
            folders={folders}
            setFolders={setFolders}
            setActiveTab={setActiveTab}
            activeFolderId={activeFolderId}
            setActiveFolderId={setActiveFolderId}
          />
        </div>
      </div>
    </div>
  );
}
