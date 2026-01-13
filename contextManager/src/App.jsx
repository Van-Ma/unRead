import { useState } from "react";
import ChatManager from "./components/ChatManager";
import FileManager from "./components/FileManager";
import './styles/App.scss';

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");
  const [folders, setFolders] = useState([]);

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
        <div style={{ display: activeTab === "files" ? "block" : "none" }}>
          <FileManager folders={folders} setFolders={setFolders} activeTab={activeTab} />
        </div>
        <div style={{ display: activeTab === "chat" ? "block" : "none" }}>
          <ChatManager folders={folders} activeTab={activeTab} />
        </div>

      </div>
    </div>
  );
}
