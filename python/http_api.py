# http_api.py
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import os

from context_manager import ContextManager
from chat_manager import ChatManager
from user_authentication import UserAuthentication
from database_connect import db_connection


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

# Helper to lookup user by email from DB
def user_lookup(email: str):
    with conn.cursor() as cur:
        cur.execute("SELECT user_id, email, password_hash, hash_algo, 'user' AS role FROM users WHERE email = %s", (email,))
        row = cur.fetchone()
        if not row:
            return None
        user_id, email, pw_hash, algo, role = row
        return {
            "id": user_id,
            "email": email,
            "password_hash": pw_hash,
            "hash_algo": algo,
            "role": role,
        }

# Helper to create user in DB
def create_user(username: str, email: str, password: str):
    # Check if exists
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE email = %s", (email,))
        if cur.fetchone():
            return False, "Email already registered"

    pw_hash, algo = auth.hash_password(password)

    user_id = str(uuid.uuid4())
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (user_id, username, email, password_hash, hash_algo) VALUES (%s, %s, %s, %s, %s)",
            (user_id, username, email, pw_hash, algo)
        )
    conn.commit()
    return True, user_id


@app.route('/signup', methods=['POST'])
def signup():
    data = request.json or {}
    username = data.get("username", "").strip()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    confirm_password = data.get("confirm_password", "")

    if not username or not email or not password or not confirm_password:
        return jsonify({"status": "error", "message": "Missing required fields"}), 400

    if password != confirm_password:
        return jsonify({"status": "error", "message": "Passwords do not match"}), 400

    success, result = create_user(username, email, password)
    if not success:
        return jsonify({"status": "error", "message": result}), 409

    token = auth.generate_jwt(sub=result, claims={"role": "user"})
    return jsonify({"status": "success", "token": token}), 201


@app.route('/login', methods=['POST'])
def login():
    data = request.json or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    ok, result = auth.perform_login_issue_token(
        email=email,
        password=password,
        user_lookup_fn=user_lookup,
        extra_claims_fn=lambda u: {"role": u.get("role", "user")},
        set_cookie=False,
        flask_response_factory=lambda data, status: jsonify(data),
    )
    if ok and hasattr(result, "status_code"):
        return result, result.status_code
    return (jsonify(result), 200) if ok else (jsonify(result), 401)


@app.route('/me', methods=['GET'])
def me():
    try:
        payload = auth.require_auth(request)
        return jsonify({"status": "success", "claims": payload}), 200
    except ValueError as e:
        return jsonify({"status": "error", "message": str(e)}), 401


@app.route('/logout', methods=['POST'])
def logout():
    resp = jsonify({"status": "success"})
    auth.clear_session_cookie(resp)
    return resp, 200



@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.json or {}
    token = data.get("token")
    new_password = data.get("new_password")

    if not token or not new_password:
        return jsonify({"status": "error", "message": "Missing token or new password"}), 400

    try:
        payload = auth.verify_jwt(token)
        if not payload.get("reset"):
            raise ValueError("Invalid reset token")
        user_id = payload["sub"]
    except Exception as e:
        return jsonify({"status": "error", "message": "Invalid or expired token"}), 401

    pw_hash, algo = auth.hash_password(new_password)
    chat_manager.update_user_password(user_id, pw_hash, algo)

    return jsonify({"status": "success", "message": "Password updated"}), 200


@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.json or {}
    email = data.get("email", "").strip().lower()

    user = chat_manager.user_lookup(email)
    if not user:
        return jsonify({"status": "error", "message": "Email not found"}), 404

    # Generate reset token with short expiry, e.g. 15 mins
    reset_token = auth.generate_jwt(sub=str(user["id"]), claims={"reset": True}, ttl_seconds=900)

    # Send email to user with reset link containing token
    chat_manager.send_reset_email(email, reset_link)

    return jsonify({"status": "success", "message": "Password reset email sent"}), 200



if __name__ == '__main__':
    app.run(debug=True, port=5000)

