import { useState, useEffect } from "react";
import '../styles/chatmanager.scss';
import ContextManager from './ContextManager';

export default function ChatManager({
  folders,
  setFolders,      
  setActiveTab,     
  activeFolderId,   
  setActiveFolderId 
}) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [selectedSnippets, setSelectedSnippets] = useState([]);

  // send message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });

      const data = await res.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.response || "No response from model." }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "⚠️ Error connecting to server." }]);
    } finally {
      setLoading(false);
    }
  };

  // folder selection
 const handleFolderClick = (snippets, folderId) => {

  if (folderId === activeFolderId) {
    setActiveFolderId(null);
    setSelectedSnippets([]);
    return;
  }
  setActiveFolderId(folderId);
};

  // switch to file tab and set active folder centrally
  const handleEditFolder = (folderId) => {
    setActiveFolderId(folderId);
    setActiveTab("files");       
  };

  // delete folder
  const handleDeleteFolder = (folderId) => {
    setFolders(prev => prev.filter(f => f.id !== folderId));
    if (activeFolderId === folderId) {
      setActiveFolderId(null);
      setSelectedSnippets([]);
    }
  };

  // enter key to send message
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

// sync selected text
  useEffect(() => {
  if (activeFolderId !== null) {
    const folder = folders.find(f => f.id === activeFolderId);
    setSelectedSnippets(folder?.snippets || []);
  } else {
    setSelectedSnippets([]);
  }
}, [activeFolderId, folders]);

  return (
    <div className="chat-page">
      <div className="chat-container">
        {/* chat messages */}
        <div className="chat-box">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>{msg.content}</div>
          ))}
          {loading && <div className="message assistant">Thinking…</div>}
        </div>

        {/* input box */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message…"
          className="chat-textarea"
        />

        {/* send button */}
        <button onClick={sendMessage} disabled={loading} className="chat-button">
          {loading ? "Sending…" : "Send"}
        </button>
      </div>

      {/* context manager */}
      <div className="context-viewer">
        <ContextManager
          folders={folders}
          activeTab="chat"
          activeFolderId={activeFolderId}
          onFolderClick={handleFolderClick}
          onDeleteFolder={handleDeleteFolder}
          onEditFolder={handleEditFolder}
          
        />
        
        {/* context */}
        <div className="selected-context">
          {selectedSnippets.map((snippet, idx) => (
            <div key={idx} className="chat-context">{snippet}</div>
          ))}
        </div>

      </div>
    </div>
  );
}
