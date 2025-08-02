import React, { useEffect, useRef, useState } from "react";
import axios from "axios";
import './chat.scss';

const API_BASE = "http://localhost:5000";

export default function Chat() {
  const [chatId, setChatId] = useState(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);        // for sending messages
  const [loadingChatId, setLoadingChatId] = useState(true);  // for creating chat id
  const textareaRef = useRef(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    async function startChat() {
      try {
        const res = await axios.post(`${API_BASE}/create_chat`, {
          modelParameters: {
            framework_type: "LangChain",
            backend: "HuggingFace",
            model_version: "Base",
            hf_params: {
              model_name: "meta-llama/Llama-3.2-1B-Instruct",
              use_kv_cache: false,
            },
          },
        });

        setChatId(res.data.chatId || res.data.chat_id); // just in case API uses different keys
        setMessages([{ role: "system", content: "Chat started." }]);
      } catch (err) {
        console.error("Failed to create chat:", err);
      } finally {
        setLoadingChatId(false); // hide spinner no matter what
      }
    }

    startChat();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

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
      console.error("Error sending message:", err);
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
      {loadingChatId ? (
        <div className="loading-spinner" />
      ) : (
        <>
          <div className="dashboard-chatoutput">
            {messages.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role}`}>
                <strong>
                  {msg.role === "user"
                    ? "You"
                    : msg.role === "assistant"
                    ? "AI"
                    : "System"}
                  :
                </strong>{" "}
                {msg.content}
              </div>
            ))}
            {loading && <div className="chat-message loading">Typing...</div>}
            <div ref={scrollRef} />
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
                disabled={loading || !chatId}
              />
              <button
                className="chat-send-btn"
                onClick={sendMessage}
                disabled={loading || !chatId}
              >
                <img src="send2.png" alt="Send" />
              </button>
            </div>
          </div>
        </>
      )}
    </>
  );
}
