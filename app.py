import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
CORS(app)

HF_API_TOKEN = os.getenv("HF_API_TOKEN")
# set LLM_BASE_URL to use any OpenAI-compatible server instead, e.g. local Ollama:
#   LLM_BASE_URL=http://localhost:11434/v1  LLM_MODEL=llama3.2:1b
LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_MODEL = os.getenv("LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")

if LLM_BASE_URL:
    client = InferenceClient(base_url=LLM_BASE_URL, api_key="unused")
else:
    client = InferenceClient(model=LLM_MODEL, token=HF_API_TOKEN)

# temporary in-memory storage of sessions
chat_sessions = {}

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    session_id = data.get("session_id", "default")
    messages = data.get("messages", [])
    end_session = data.get("end_session", False)

    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    chat_sessions[session_id].extend(messages)

    reply_content = ""
    if messages and not end_session:
        try:
            result = client.chat_completion(messages=messages, model=LLM_MODEL, max_tokens=200, temperature=0.7)
            reply_content = result.choices[0].message.content.strip()
        except Exception as e:
            reply_content = f"Error: {str(e)}"

    if reply_content:
        chat_sessions[session_id].append({"role": "assistant", "content": reply_content})

    response_data = {
        "response": reply_content,
        "chat_log": chat_sessions[session_id] if end_session else []
    }

    if end_session:
        chat_sessions.pop(session_id, None)

    return jsonify(response_data)

if __name__ == "__main__":
    app.run(port=5000, debug=True)
