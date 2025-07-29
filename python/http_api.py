# Flask API for chat management

from flask import Flask, request, jsonify
from flask_cors import CORS # Ensure CORS is imported if you need it
import uuid
import logging

from chat_manager import ChatManager
from models.langchain import get_global_app, set_global_app
from models.model_parameters import ModelParameters # Keep for potential model selection logic in http_api

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
CORS(app)  # Frontend compatibility

# Global chat manager
chat_manager = ChatManager()

# Lazy load LLM on first request

@app.route('/')
def home():
    return "Chatbot Backend is Running!"

@app.route('/create_chat', methods=['POST'])
def create_chat():
    data = request.json
    model_parameters_dict = data.get('modelParameters', {})  # Dict passed straight through
    
    logging.info(f"Creating chat with model parameters: {model_parameters_dict}")
    
    # Ensure we have the required parameters
    if not model_parameters_dict.get('hf_params'):
        model_parameters_dict['hf_params'] = {}
    
    # Ensure hf_params exists
    if 'hf_params' not in model_parameters_dict:
        model_parameters_dict['hf_params'] = {}
    
    # Set default model parameters if not provided
    if 'model_name' not in model_parameters_dict['hf_params']:
        model_parameters_dict['hf_params']['model_name'] = 'meta-llama/Llama-3.1-8B-Instruct'
    
    # Ensure use_kv_cache is set
    model_parameters_dict['hf_params'].setdefault('use_kv_cache', True)

    try:
        # Pass the processed parameters to the chat manager
        chat_id, message = chat_manager.create_chat(model_parameters_dict)
        return jsonify({"status": "success", "chatId": chat_id, "message": message}), 200
    except ValueError as e:
        logging.error(f"Validation error creating chat: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.exception("Error creating chat:")
        return jsonify({"status": "error", "message": f"An internal error occurred: {str(e)}"}), 500

@app.route('/change_model', methods=['POST'])
def change_model():
    """Change the active model at runtime."""
    data = request.json or {}
    model_parameters_dict = data.get('modelParameters')

    if not model_parameters_dict:
        return jsonify({"status": "error", "message": "'modelParameters' JSON is required."}), 400

    try:
        success, msg = chat_manager.change_global_model(model_parameters_dict)
        if success:
            return jsonify({"status": "success", "message": msg}), 200
        else:
            return jsonify({"status": "error", "message": msg}), 500
    except ValueError as e:
        logging.error(f"Validation error changing model: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
    except Exception as e:
        logging.exception("Error changing model:")
        return jsonify({"status": "error", "message": f"An internal error occurred: {str(e)}"}), 500

# -----------------------------------------------------------------------------

@app.route('/chat', methods=['POST'])
def chat_message():
    """Process chat message with optional files.
    
    Args:
        chatId: Unique chat identifier
        message: User's message text
        files: Optional list of file objects with name/content
        modelParameters: Optional model configuration
        
    Returns:
        JSON with status and response
    """
    data = request.json or {}
    chat_id = data.get('chatId')
    message = data.get('message', '').strip()
    files = data.get('files', [])
    model_parameters_dict = data.get('modelParameters')

    if not chat_id:
        return jsonify({"status": "error", "message": "Chat ID is required"}), 400
        
    if not message and not files:
        return jsonify({"status": "error", "message": "Message or file content is required"}), 400

    try:
        # chat_manager now handles multiple files with names
        response_data = chat_manager.chat(
            chat_id=chat_id,
            user_input=message,
            files=files,
            model_params=model_parameters_dict
        )
        
        if response_data.get("error"):
            return jsonify({"status": "error", "message": response_data["response"]}), 500
            
        return jsonify({
            "status": "success",
            "response": response_data["response"]
        })
        
    except Exception as e:
        logging.exception("Error in chat endpoint:")
        return jsonify({
            "status": "error",
            "message": f"An error occurred: {str(e)}"
        }), 500

@app.route('/get_chat_context_history', methods=['POST'])
def get_chat_context_history():
    data = request.json
    chat_id = data.get('chatId')

    if not chat_id:
        return jsonify({"status": "error", "message": "Chat ID is required."}), 400

    try:
        history = chat_manager.get_chat_context_history(chat_id)
        return jsonify({"status": "success", "history": history}), 200
    except Exception as e:
        logging.exception(f"Error getting context history for chat {chat_id}:")
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500

@app.route('/clear_context', methods=['POST'])
def clear_context():
    data = request.json
    chat_id = data.get('chatId')

    if not chat_id:
        return jsonify({"status": "error", "message": "Chat ID is required."}), 400

    try:
        success, message = chat_manager.clear_context(chat_id)
        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "error", "message": message}), 500
    except Exception as e:
        error_msg = f"An error occurred while clearing context: {str(e)}"
        logging.exception(f"Error clearing context for chat {chat_id}:")
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/delete_chat', methods=['POST'])
def delete_chat():
    data = request.json
    chat_id = data.get('chatId')

    if not chat_id:
        return jsonify({"status": "error", "message": "Chat ID is required."}), 400

    try:
        success, message = chat_manager.delete_chat(chat_id)
        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "error", "message": message}), 404
    except Exception as e:
        logging.exception(f"Error deleting chat {chat_id}:")
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500

@app.route('/save_chat_context', methods=['POST'])
def save_chat_context():
    data = request.json
    chat_id = data.get('chatId')
    if not chat_id:
        return jsonify({"status": "error", "message": "chatId is required."}), 400
    try:
        success, message = chat_manager.save_chat_context(chat_id)
        if success:
            return jsonify({"status": "success", "message": message}), 200
        else:
            return jsonify({"status": "error", "message": message}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True)
