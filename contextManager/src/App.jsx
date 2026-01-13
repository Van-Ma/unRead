import { useState } from "react";
import ChatManager from "./components/ChatManager";
import FileManager from "./components/FileManager";
import './styles/App.scss';

export default function App() {
  const [activeTab, setActiveTab] = useState("chat");     
  const [folders, setFolders] = useState([]);         
  const [activeFolderId, setActiveFolderId] = useState(null); 

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
            activeTab={activeTab}
            activeFolderId={activeFolderId}
            setActiveFolderId={setActiveFolderId} 
          />
        </div>

        {/* Chat Manager */}
        <div style={{ display: activeTab === "chat" ? "block" : "none" }}>
          <ChatManager
            folders={folders}
            setFolders={setFolders}
            activeTab={activeTab}
            setActiveTab={setActiveTab}          
            activeFolderId={activeFolderId}
            setActiveFolderId={setActiveFolderId} 
          />
        </div>
      </div>
    </div>
  );
}
