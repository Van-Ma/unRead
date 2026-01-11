import { useState } from "react";
import '../styles/chatmanager.scss';

export default function ChatManager() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // send message 
  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage = { role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:5000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });

      const data = await res.json();

      const botMessage = {
        role: "assistant",
        content: data.response || "No response from model.",
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Error connecting to server." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  // enter key to send
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="chat-page">
      <div className="context-viewer">
        <p>current context in chat</p>
      </div>
      <div className="chat-container">
        {/* chat box */}
        <div className="chat-box">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`message ${msg.role}`}
            >
              {msg.content}
            </div>
          ))}
          {loading && (
            <div className="message assistant">Thinking…</div>
          )}
        </div>

        {/* prompt input box */}
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message…"
          className="chat-textarea"
        />

        {/* send button */}
        <button
          onClick={sendMessage}
          disabled={loading}
          className="chat-button"
        >
          {loading ? "Sending…" : "Send"}
        </button>
      </div>
    </div>

  );
}
