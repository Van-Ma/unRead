import { useState, useEffect } from "react";
import ContextManager from './ContextManager';
import { api } from "../api";

export default function ChatManager({
  folders,
  setFolders,
  setActiveTab,
  activeFolderId,
  setActiveFolderId,
}) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chatId, setChatId] = useState(null);
  const [rag, setRag] = useState(false);
  const [models, setModels] = useState([]);
  const [model, setModel] = useState("");
  const [files, setFiles] = useState([]);

  const folder = folders.find(f => f.id === activeFolderId);
  const snippets = folder?.snippets || [];

  useEffect(() => {
    api("/models")
      .then(data => { setModels(data.models); setModel(data.current); })
      .catch(err => console.error("Loading models failed:", err));
  }, []);

  // a different folder starts a new chat
  useEffect(() => {
    setChatId(null);
    setMessages([]);
    setFiles([]);
    if (activeFolderId !== null) {
      api(`/folders/${activeFolderId}/files`).then(setFiles).catch(() => {});
    }
  }, [activeFolderId]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const message = input;
    setMessages(prev => [...prev, { role: "user", content: message }]);
    setInput("");
    setLoading(true);

    try {
      const data = await api("/chat", {
        method: "POST",
        body: { chat_id: chatId, folder_id: activeFolderId, message, mode: rag ? "rag" : "context", model },
      });
      setChatId(data.chat_id);
      setMessages(prev => [...prev, { role: "assistant", content: data.response, sources: data.sources }]);
    } catch (err) {
      setMessages(prev => [...prev, { role: "assistant", content: `⚠️ ${err.message}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const changeModel = (e) => {
    setModel(e.target.value);
    api("/models", { method: "POST", body: { model: e.target.value } }).catch(console.error);
  };

  const attachFiles = async () => {
    const paths = await window.electronAPI.pickFiles();
    for (const path of paths || []) {
      try {
        await api(`/folders/${activeFolderId}/files`, { method: "POST", body: { path } });
      } catch (err) {
        alert(`Could not attach ${path}: ${err.message}`);
      }
    }
    setFiles(await api(`/folders/${activeFolderId}/files`));
  };

  const detachFile = async (path) => {
    await api(`/folders/${activeFolderId}/files?path=${encodeURIComponent(path)}`, { method: "DELETE" });
    setFiles(prev => prev.filter(f => f.path !== path));
  };

  const handleFolderClick = (_snippets, folderId) => {
    setActiveFolderId(folderId === activeFolderId ? null : folderId);
  };

  const handleEditFolder = (folderId) => {
    setActiveFolderId(folderId);
    setActiveTab("files");
  };

  const handleDeleteFolder = (folderId) => {
    setFolders(prev => prev.filter(f => f.id !== folderId));
    if (activeFolderId === folderId) setActiveFolderId(null);
  };

  const startNewSession = () => {
    setChatId(null);
    setMessages([]);
    setInput("");
  };

  return (
    <div className="chat-page">
      <div className="chat-container">
        <div className="chat-options">
          <select value={model} onChange={changeModel} title="model">
            {!models.includes(model) && <option value={model}>{model}</option>}
            {models.map(m => <option key={m} value={m}>{m}</option>)}
          </select>
          <label title="search the folder for relevant passages instead of sending all of it">
            <input type="checkbox" checked={rag} onChange={e => setRag(e.target.checked)} /> RAG
          </label>
        </div>

        <div className="chat-box">
          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              {msg.content}
              {msg.sources?.length > 0 && <div className="sources">sources: {msg.sources.join(", ")}</div>}
            </div>
          ))}
          {loading && <div className="message assistant">Thinking…</div>}
        </div>

        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message…"
          className="chat-textarea"
        />

        <button onClick={sendMessage} disabled={loading} className="chat-button">
          {loading ? "Sending…" : "Send"}
        </button>

        <button onClick={startNewSession} className="new-session-button">
          New Chat Session
        </button>
      </div>

      <div className="context-viewer">
        <ContextManager
          folders={folders}
          activeTab="chat"
          activeFolderId={activeFolderId}
          onFolderClick={handleFolderClick}
          onDeleteFolder={handleDeleteFolder}
          onEditFolder={handleEditFolder}
        />

        <div className="selected-context">
          {snippets.map((snippet, idx) => (
            <div key={idx} className="chat-context">{snippet}</div>
          ))}
          {files.map(f => (
            <div key={f.path} className="chat-context attached-file">
              📄 {f.name}
              <button className="close-snippet" onClick={() => detachFile(f.path)}>×</button>
            </div>
          ))}
          {activeFolderId !== null && (
            <button className="folder-controls-btn" onClick={attachFiles}>Attach files</button>
          )}
        </div>
      </div>
    </div>
  );
}
