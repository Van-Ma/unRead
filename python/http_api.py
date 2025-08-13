# http_api.py
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, redirect, url_for, session, jsonify
from flask_cors import CORS
import logging
import os
import secrets

from chat_manager import ChatManager
from file_manager import ingest_files, parse_file_to_text, ingest_text_to_vectorstore
from user_authentication import oauth, init_oauth
from database import db_connection, user_owns_chat


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    force=True
)

app = Flask(__name__)

app.secret_key = os.getenv('FLASK_SECRET_KEY') 



# Initialize OAuth with app
init_oauth(app)

CORS(app)
chat_manager = ChatManager() # TODO: make this distrubute across multiple servers / model APIs. Balance load.

@app.route('/create_chat', methods=['POST'])
def create_chat():
    model_parameters: ModelParameters = request.json.get('modelParameters', {})
    chat_id, message = chat_manager.create_chat(model_parameters)
    return jsonify({"status": "success", "chatId": chat_id, "message": message}), 200

@app.route('/open_chat', methods=['POST'])
def open_chat():
    user_id = request.headers.get('X-User-Id')
    data = request.json or {}
    chat_id = data.get('chatId')
    if not user_id or not chat_id:
        return jsonify({"status": "error", "message": "Missing user or chatId"}), 400
    if not user_owns_chat(user_id, chat_id):
        return jsonify({"status": "error", "message": "Access denied for this chat"}), 403
    result = chat_manager.open_chat(chat_id, user_id)
    return jsonify(result), (200 if result.get("status") == "success" else 403)

@app.route('/change_model', methods=['POST'])
def change_model():
    model_parameters: ModelParameters = request.json.get('modelParameters')
    if not model_parameters: return jsonify({"status": "error", "message": "'modelParameters' is required."}), 400
    success, msg = chat_manager.change_global_model(model_parameters)
    return jsonify({"status": "success", "message": msg}) if success else jsonify({"status": "error", "message": msg}), 500

@app.route('/chat', methods=['POST'])
def chat_message():
    user_id = request.headers.get('X-User-Id')
    # Support both multipart/form-data and application/json
    json_body = request.get_json(silent=True) or {}
    chat_id = request.form.get('chatId') or json_body.get('chatId')
    message = (request.form.get('message') if request.form else None) or json_body.get('message', '')
    files_payload = []
    if 'files' in request.files:
        files_payload = request.files.getlist('files')
    elif 'file' in request.files:
        files_payload = [request.files['file']]
    else:
        json_body = request.get_json(silent=True) or {}
        files_payload = json_body.get('files', [])
    if not chat_id:
        return jsonify({"status": "error", "message": "Chat ID is required"}), 400
    if not user_id or not user_owns_chat(user_id, chat_id):
        return jsonify({"status": "error", "message": "Access denied for this chat"}), 403
    response_data = chat_manager.chat(chat_id=chat_id, user_id=user_id, user_input=message, files=files_payload)
    return jsonify(response_data), (200 if response_data.get("status") == "success" else 500)

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

@app.route('/close_chat', methods=['POST'])
def close_chat():
    """Closes a chat, freeing up memory but keeping database history."""
    chat_id = request.json.get('chatId')
    if not chat_id:
        return jsonify({"status": "error", "message": "Chat ID is required."}), 400
    
    success, message = chat_manager.close_chat(chat_id)
    
    if success:
        return jsonify({"status": "success", "message": message}), 200
    else:
        return jsonify({"status": "error", "message": message}), 500

@app.route('/save_chat_context', methods=['POST'])
def save_chat_context_endpoint():
    chat_id = request.json.get('chatId')
    if not chat_id: return jsonify({"status": "error", "message": "chatId is required."}), 400
    success, message = chat_manager.save_chat_context(chat_id)
    return jsonify({"status": "success", "message": message}) if success else jsonify({"status": "error", "message": message}), 500
    

@app.route('/upload_context_file', methods=['POST'])
def upload_context_file():
    user_id = request.headers.get('X-User-Id')
    chat_id = request.form.get('chatId')
    if not chat_id:
        return jsonify({"status": "error", "message": "chatId is required"}), 400
    if 'file' not in request.files and 'files' not in request.files:
        return jsonify({"status": "error", "message": "No file part in request"}), 400
    files = request.files.getlist('files') if 'files' in request.files else [request.files['file']]
    try:
        if not user_id or not user_owns_chat(user_id, chat_id):
            return jsonify({"status": "error", "message": "Access denied for this chat"}), 403
        ingest_files(chat_id, files)
        return jsonify({"status": "success", "message": "File(s) uploaded and ingested"}), 201
    except Exception as e:
        return jsonify({"status": "error", "message": f"Ingestion failed: {e}"}), 500

@app.route('/login/google')
def login_google():
    google = oauth.create_client('google')
    nonce = secrets.token_urlsafe(16)
    session['nonce'] = nonce

    redirect_uri = url_for('authorize_google', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)


@app.route('/authorize/google')
def authorize_google():
    google = oauth.create_client('google')
    token = google.authorize_access_token()
    nonce = session.pop('nonce', None)

    user_info = google.parse_id_token(token, nonce=nonce)
    session['user'] = user_info
    
    return redirect(f"http://localhost:5000/?token={token['access_token']}")

if __name__ == '__main__':
    app.run(debug=True, port=5000)

