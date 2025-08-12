# http_api.py
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging

from context_manager import ContextManager
from chat_manager import ChatManager
from user_authentication import UserAuthentication
from models.model_parameters import ModelParameters


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] - %(message)s',
    force=True
)

app = Flask(__name__)
CORS(app)
chat_manager = ChatManager()
context_manager = ContextManager()

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
    # Assume user_id is fetched from authentication (e.g., JWT/session)
    user_id = request.headers.get('X-User-Id')
    if not user_id:
        return jsonify({"status": "error", "message": "User authentication required"}), 401

    chat_id = request.form.get('chatId')
    if not chat_id:
        return jsonify({"status": "error", "message": "chatId is required"}), 400

    if 'file' not in request.files:
        return jsonify({"status": "error", "message": "No file part in request"}), 400

    uploaded_file = request.files['file']

    # Parse and create ContextFile object
    context_file = context_manager.parse_and_create_context_file(user_id, chat_id, uploaded_file)
    if not context_file:
        return jsonify({"status": "error", "message": "File parsing failed or empty content"}), 400

    # Save to DB
    success = context_manager.save_context_file(user_id, context_file)
    if success:
        return jsonify({"status": "success", "message": "File uploaded and saved"}), 201
    else:
        return jsonify({"status": "error", "message": "Project validation failed or DB error"}), 403


auth = UserAuthentication(
    jwt_secret=os.environ.get("JWT_SECRET", "dev-secret-change-me"),
    issuer="your-api",
    audience=None,  # set if you want aud checks
    access_ttl_seconds=3600,
    cookie_name="session",
    cookie_secure=True,        # True in prod (HTTPS); can set False for local dev over http
    cookie_samesite="Lax",
    cookie_http_only=True,
)

# Example: POST /login (JSON: { "email": "...", "password": "...", "useCookie": true|false })
@app.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    # replace this with your real DB lookup (PostgreSQL)
    def user_lookup_fn(eml):
        # Example shape returned from DB:
        # return {"id": 123, "email": eml, "password_hash": "...", "hash_algo": "bcrypt", "role": "user"}
        return chat_manager.user_lookup(eml)  # <- implement on your side

    use_cookie = bool(data.get("useCookie", False))

    ok, result = auth.perform_login_issue_token(
        email=email,
        password=password,
        user_lookup_fn=user_lookup_fn,
        extra_claims_fn=lambda user: {"chat": "allowed"},  # optional
        set_cookie=use_cookie,
        flask_response_factory=lambda payload, status: jsonify(payload),  # your response factory
    )
    if ok and hasattr(result, "status_code"):
        return result, result.status_code
    return (jsonify(result), 200) if ok else (jsonify(result), 401)

# Example: protected route (accepts either Authorization: Bearer <JWT> or session cookie)
@app.route('/me', methods=['GET'])
def me():
    try:
        payload = auth.require_auth(request)
        return jsonify({"status": "success", "claims": payload}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 401

# Example: logout (clear cookie if you're using cookie transport)
@app.route('/logout', methods=['POST'])
def logout():
    resp = jsonify({"status": "success"})
    auth.clear_session_cookie(resp)
    return resp, 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)