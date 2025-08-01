import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import './chat.scss';

const API_BASE = "http://localhost:5000";

export default function Chat() {
  const [chatId, setChatId] = useState(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const textareaRef = useRef(null);

  useEffect(() => {
    // Initialize chat when component mounts
    createChat();
  }, []);

  const createChat = async () => {
    try {
      const res = await axios.post(`${API_BASE}/create_chat`, {
        modelParameters: {
          framework_type: "LangChain",
          backend: "HuggingFace",
          model_version: "Base",
          hf_params: {
            model_name: "meta-llama/Llama-3.2-1B-Instruct",
            use_kv_cache: false,
          }
        }
      });
      setChatId(res.data.chatId);
      setMessages([{ role: "system", content: "New chat created." }]);
    } catch (err) {
      console.error("Error creating chat", err);
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !chatId) return;

    const newMessages = [...messages, { role: "user", content: input }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/chat`, {
        chatId,
        message: input,
      });
      setMessages([
        ...newMessages,
        { role: "assistant", content: res.data.response },
      ]);
    } catch (err) {
      console.error("Chat error", err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const value = e.target.value;
    setInput(value);

    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 200) + "px";
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <>
      <div className="dashboard-chatoutput">
        {messages.map((msg, idx) => (
          <div key={idx} className={`chat-message ${msg.role}`}>
            <strong>{msg.role === "user" ? "You" : msg.role === "assistant" ? "AI" : "System"}:</strong> {msg.content}
          </div>
        ))}
        {loading && <div className="chat-message loading">Typing...</div>}
      </div>

      <div className="dashboard-controls">
        <div className="chat-input-wrapper">
          <textarea
            ref={textareaRef}
            placeholder="Ask AI anything..."
            rows={1}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
          />
          <button className="chat-send-btn" onClick={sendMessage} disabled={loading}>
            <img src="send2.png" alt="Send" />
          </button>
        </div>
      </div>
    </>
  );
}
