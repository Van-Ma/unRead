# http_api.py
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

from chat_manager import ChatManager
from models.model_parameters import ModelParameters

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    force=True
)

app = Flask(__name__)
CORS(app)
chat_manager = ChatManager()
print("test! test!")

@app.route('/create_chat', methods=['POST'])
def create_chat():
    model_parameters: ModelParameters = request.json.get('modelParameters', {})
    chat_id, message = chat_manager.create_chat(model_parameters)
    return jsonify({"status": "success", "chatId": chat_id, "message": message}), 200

@app.route('/change_model', methods=['POST'])
def change_model():
    model_parameters: ModelParameters = request.json.get('modelParameters')
    if not model_parameters: return jsonify({"status": "error", "message": "'modelParameters' is required."}), 400
    success, msg = chat_manager.change_global_model(model_parameters)
    return jsonify({"status": "success", "message": msg}) if success else jsonify({"status": "error", "message": msg}), 500

@app.route('/chat', methods=['POST'])
def chat_message():
    data = request.json or {}
    chat_id, message, files = data.get('chatId'), data.get('message', ''), data.get('files', [])
    if not chat_id: return jsonify({"status": "error", "message": "Chat ID is required"}), 400
    response_data = chat_manager.chat(chat_id=chat_id, user_input=message, files=files)
    return jsonify(response_data), 200 if response_data["status"] == "success" else 500

@app.route('/chat_context/<chat_id>', methods=['GET', 'POST'])
def chat_context(chat_id):
    if request.method == 'GET':
        return jsonify({"status": "success", "history": chat_manager.get_context(chat_id)}), 200
    elif request.method == 'POST':
        new_context = request.json.get('context')
        if new_context is None: return jsonify({"status": "error", "message": "A 'context' list is required"}), 400
        chat_manager.update_context(chat_id, new_context)
        return jsonify({"status": "success", "message": "Chat context updated"}), 200

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    chat_id = request.json.get('chatId')
    if not chat_id: return jsonify({"status": "error", "message": "Chat ID is required."}), 400
    success, message = chat_manager.delete_chat(chat_id)
    return jsonify({"status": "success", "message": message}) if success else jsonify({"status": "error", "message": message}), 500

@app.route('/save_chat_context', methods=['POST'])
def save_chat_context_endpoint():
    chat_id = request.json.get('chatId')
    if not chat_id: return jsonify({"status": "error", "message": "chatId is required."}), 400
    success, message = chat_manager.save_chat_context(chat_id)
    return jsonify({"status": "success", "message": message}) if success else jsonify({"status": "error", "message": message}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)