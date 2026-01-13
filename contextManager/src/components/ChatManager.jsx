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
  const [conversationHistory, setConversationHistory] = useState([]);

  // sync selected text when folder changes
  useEffect(() => {
    if (activeFolderId !== null) {
      const folder = folders.find(f => f.id === activeFolderId);
      const snippets = folder?.snippets || [];
      setSelectedSnippets(snippets);

      // system prompt only gets answers directly from text
      setConversationHistory([
        {
          role: "system",
          content: `You must answer questions using ONLY the context provided below.
Do NOT assume or invent any information outside the context.
You MAY reason and infer answers directly from the context, for example if the context says 
"funnel-shaped," you can answer "No, it is funnel-shaped" to a yes/no question.
If the answer cannot be derived at all from the context, respond with "I cannot answer based on the provided context."


Folder context:
${snippets.map((s, i) => `${i + 1}. ${s}`).join("\n")}`
        }
      ]);

      setMessages([]);
    } else {
      setSelectedSnippets([]);
      setConversationHistory([
        {
          role: "system",
          content: `You must answer questions using ONLY the context provided below.
Do NOT assume or invent any information outside the context.
You MAY reason and infer answers directly from the context, for example if the context says 
"funnel-shaped," you can answer "No, it is funnel-shaped" to a yes/no question.
If the answer cannot be derived at all from the context, respond with "I cannot answer based on the provided context."`
        }
      ]);
      setMessages([]);
    }
  }, [activeFolderId, folders]);

  // send message
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: "user", content: input };
    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    // build messages for API: folder context + last 10 conversation turns
    const messagesToSend = [...conversationHistory, userMessage];

    try {
      const res = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: messagesToSend }),
      });

      const data = await res.json();
      const aiMessage = { role: "assistant", content: data.response || "No response from model." };

      // update conversation history, keep last 10 messages only
      setConversationHistory(prev => {
        const combined = [...prev, userMessage, aiMessage];
        return combined.slice(-10);
      });

      setMessages(prev => [...prev, aiMessage]);
    } catch {
      const errorMsg = { role: "assistant", content: "⚠️ Error connecting to server." };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  // enter key to send message
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
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

  // switch to file tab
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

  // start new chat session manually
  const startNewSession = () => {
    setConversationHistory([
      {
        role: "system",
        content: `You must answer questions using ONLY the context provided below.
Do NOT assume or invent any information outside the context.
You MAY reason and infer answers directly from the context, for example if the context says 
"funnel-shaped," you can answer "No, it is funnel-shaped" to a yes/no question.
If the answer cannot be derived at all from the context, respond with "I cannot answer based on the provided context."

Folder context:
${selectedSnippets.map((s, i) => `${i + 1}. ${s}`).join("\n")}`
      }
    ]);
    setMessages([]);
    setInput("");
    setActiveFolderId(null);
    setSelectedSnippets([]);
  };

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

        {/* new session button */}
        <button onClick={startNewSession} className="new-session-button">
          New Chat Session
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

        {/* context display */}
        <div className="selected-context">
          {selectedSnippets.map((snippet, idx) => (
            <div key={idx} className="chat-context">{snippet}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
