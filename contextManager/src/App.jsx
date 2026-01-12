import { useState } from "react";
import ChatManager from "./components/ChatManager";
import FileManager from "./components/FileManager";
import ContextManager from "./components/ContextManager";
import './styles/App.scss';

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");

  const [folders, setFolders] = useState([]);

  return (
    <div className="app-container">
      <nav className="tab-bar">
        <button
          className={activeTab === "chat" ? "active" : ""}
          onClick={() => setActiveTab("chat")}
        >
          Chat
        </button>
        <button
          className={activeTab === "files" ? "active" : ""}
          onClick={() => setActiveTab("files")}
        >
          File Manager
        </button>
        <button
          className={activeTab === "context" ? "active" : ""}
          onClick={() => setActiveTab("context")}
        >
          Context Manager
        </button>
      </nav>

      <div className="tab-content">
        <div style={{ display: activeTab === "chat" ? "block" : "none" }}>
          <ChatManager />
        </div>
        <div style={{ display: activeTab === "files" ? "block" : "none" }}>
          <FileManager folders={folders} setFolders={setFolders} />
        </div>
        <div style={{ display: activeTab === "context" ? "block" : "none" }}>
          <ContextManager folders={folders} setFolders={setFolders} />
        </div>
      </div>
    </div>
  );
}
