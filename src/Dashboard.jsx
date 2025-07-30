import './dashboard.scss';
import { useEffect, useRef, useState } from "react";

function Dashboard({ section, onBack }) {
     const textareaRef = useRef(null);
  const chatOutputRef = useRef(null);
  const chatIdRef = useRef(null);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [currentModel, setCurrentModel] = useState("LangChainKVCache/meta-llama/Llama-3.2-1B-Instruct");
  const baseUrl = "http://127.0.0.1:5000";

  const modelOptions = [
    "LangChainKVCache/meta-llama/Llama-3.1-8B-Instruct",
    "HuggingFaceNoCache/meta-llama/Llama-3.1-8B-Instruct",
    "LangChainKVCache/meta-llama/Llama-3.2-1B-Instruct",
    "HuggingFaceNoCache/meta-llama/Llama-3.2-1B-Instruct",
    "LangChainKVCache/TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "HuggingFaceNoCache/TinyLlama/TinyLlama-1.1B-Chat-v1.0"
  ];

  useEffect(() => {
    initializeChat(currentModel);
  }, []);

  const initializeChat = async (modelName) => {
    const payload = {
      modelParameters: {
        framework_type: "LangChain",
        backend: "HuggingFace",
        model_version: "Base",
        hf_params: {
          model_name: modelName,
          use_kv_cache: false
        }
      }
    };

    try {
      const res = await fetch(`${baseUrl}/create_chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await res.json();
      if (res.ok) {
        chatIdRef.current = data.chatId;
        setMessages([]);
        console.log("Chat initialized with:", modelName);
      } else {
        throw new Error(data.message || "Failed to start chat");
      }
    } catch (err) {
      alert("Failed to initialize chat: " + err.message);
    }
  };

  const handleModelChange = async (e) => {
    const newModel = e.target.value;

    const confirmSwitch = window.confirm(
      `Switch to model "${newModel}"?\n\nThis will start a new chat and clear history.`
    );

    if (!confirmSwitch) return;

    setCurrentModel(newModel);
    await initializeChat(newModel);
  };

  const handleSend = async () => {
    const prompt = input.trim();
    if (!prompt || !chatIdRef.current) return;

    const userMessage = { sender: 'user', text: prompt, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMessage]);
    setInput('');

    const thinkingMessage = { sender: 'ai', text: '🤖 Thinking...', timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, thinkingMessage]);

    try {
      const res = await fetch(`${baseUrl}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chatId: chatIdRef.current,
          message: prompt
        })
      });

      const data = await res.json();
      const aiMessage = {
        sender: 'ai',
        text: data.response,
        timestamp: new Date().toISOString()
      };

      setMessages(prev => [...prev.slice(0, -1), aiMessage]);

      await fetch(`${baseUrl}/save_chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: [...messages, userMessage, aiMessage] })
      });
    } catch (err) {
      setMessages(prev => [...prev.slice(0, -1), { sender: 'ai', text: `Error: ${err.message}` }]);
    }
  };

  const handleInput = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 300) + "px";
    }
  };
    return (
       <div className="dashboard-page">
      <button id="back-btn" onClick={onBack}>Back</button>

      {section === 'new' && (
        <div className="dashboard-layout">
          <div className="dashboard-left">
            <div className="dashboard-droparea">
              <p>drag and drop or click to upload files.</p>
              <img id="brain-logo" src="brain.png" alt="brain logo" />
            </div>
            <div className="dashboard-fileoutput"></div>
          </div>

          <div className="dashboard-right">
            <div className="model-container">
              <select value={currentModel} onChange={handleModelChange}>
                {modelOptions.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            </div>

            <div className="dashboard-chatoutput" ref={chatOutputRef}>
              {messages.map((msg, index) => (
                <div key={index} className={msg.sender === 'user' ? 'user' : 'bot'}>
                  <b>{msg.sender === 'user' ? 'You:' : 'AI:'}</b> {msg.text}
                </div>
              ))}
            </div>

            <div className="dashboard-controls">
              <textarea
                ref={textareaRef}
                id="chat-inputbox"
                placeholder="Ask AI anything..."
                value={input}
                onChange={e => setInput(e.target.value)}
                onInput={handleInput}
                rows={1}
              />
              <button id="chat-send-btn" onClick={handleSend}>Send</button>
            </div>
          </div>
        </div>
      )}
    </div>
    );
}

export default Dashboard;
