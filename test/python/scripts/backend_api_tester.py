# backend_api_tester.py
# A terminal-based testing harness for the chatbot Flask API.

import requests
import argparse
import sys
import json
import os
from typing import Dict, Any, List

# Added the new /close_chat endpoint
ENDPOINTS = {
    "change_model": "/change_model",
    "create_chat": "/create_chat",
    "chat": "/chat",
    "get_context": "/chat_context/",
    "save_context": "/save_chat_context",
    "delete_chat": "/delete_chat",
    "close_chat": "/close_chat"
}

# --- API Call Functions ---

def api_post(base_url: str, endpoint: str, payload: Dict, timeout: int = 60) -> Dict:
    """Helper function for making POST requests to the API."""
    try:
        url = f"{base_url}{endpoint}"
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"\n<-- API Error: {e}")
        if e.response is not None:
            print(f"<-- Response Body: {e.response.text}")
        return None

def create_chat(base_url: str, model_parameters: Dict[str, Any]) -> str:
    """Sends a request to create a new chat."""
    print("--> Creating new chat with model parameters:")
    print(json.dumps(model_parameters, indent=2))
    response_data = api_post(base_url, ENDPOINTS['create_chat'], {"modelParameters": model_parameters}, timeout=300)
    if response_data and response_data.get("chatId"):
        chat_id = response_data["chatId"]
        print(f"<-- Success. Chat ID = {chat_id}")
        return chat_id
    return None

def read_file_content(file_path: str) -> dict:
    """Reads a file and returns its name and content."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {'name': os.path.basename(file_path), 'content': content}
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def chat(base_url: str, chat_id: str, message: str, file_paths: List[str] = None) -> str:
    """Sends a message with optional files to the chat endpoint."""
    payload = {"chatId": chat_id, "message": message}
    if file_paths:
        files_payload = [data for path in file_paths if (data := read_file_content(path))]
        if files_payload:
            payload["files"] = files_payload
            print(f"--> Attaching {len(files_payload)} file(s) to the message.")
    
    response_data = api_post(base_url, ENDPOINTS['chat'], payload, timeout=120)
    return response_data.get('response', 'Error: No response field in JSON.') if response_data else "API call failed."

def delete_chat(base_url: str, chat_id: str):
    """Sends a request to hard-delete the chat."""
    print(f"--> Hard-deleting chat {chat_id} from memory and database...")
    response_data = api_post(base_url, ENDPOINTS['delete_chat'], {"chatId": chat_id})
    if response_data:
        print(f"<-- Success: {response_data.get('message')}")

def close_chat(base_url: str, chat_id: str):
    """Sends a request to close the chat (free memory only)."""
    print(f"\n--> Closing chat {chat_id} from server memory...")
    response_data = api_post(base_url, ENDPOINTS['close_chat'], {"chatId": chat_id})
    if response_data:
        print(f"<-- Success: {response_data.get('message')}")

def get_chat_context(base_url: str, chat_id: str):
    """Retrieves and prints the context for a given chat."""
    print(f"--> Getting context for chat {chat_id}...")
    try:
        url = f"{base_url}{ENDPOINTS['get_context']}{chat_id}"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        print("<-- Chat History:")
        print(json.dumps(response.json().get("history"), indent=2))
    except requests.exceptions.RequestException as e:
        print(f"<-- API Error: {e}")

def save_chat_context(base_url: str, chat_id: str):
    """Sends a request to manually save the chat context to the database."""
    print(f"--> Manually saving context for chat {chat_id}...")
    response_data = api_post(base_url, ENDPOINTS['save_context'], {"chatId": chat_id})
    if response_data:
        print(f"<-- Success: {response_data.get('message')}")

# --- Main Application Logic ---

def main():
    """Main function to run the terminal chat client."""
    parser = argparse.ArgumentParser(description="Terminal client to test the chatbot API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Base URL of the API.")
    parser.add_argument("--framework-type", default="LangChain", help="The agent framework type.")
    parser.add_argument("--backend", default="HuggingFace", help="The backend model provider.")
    parser.add_argument("--model-version", default="Base", choices=["Base", "RAG"], help="Model version.")
    parser.add_argument("--model-name", default="meta-llama/Llama-3.2-1B-Instruct", help="Specific model name.")
    parser.add_argument("--use-kv-cache", action="store_true", help="Enable KV caching.")
    parser.add_argument("--file", help="Optional path to a file for the first message.")
    args = parser.parse_args()

    model_parameters = {
        "framework_type": args.framework_type,
        "backend": args.backend,
        "model_version": args.model_version,
        "hf_params": {"model_name": args.model_name, "use_kv_cache": args.use_kv_cache}
    }
    
    chat_id = create_chat(args.base_url, model_parameters)
    if not chat_id:
        sys.exit("Failed to create chat. Exiting.")

    print("\n--- Chat Started ---")
    
    def show_help():
        print("\n" + "="*21 + " Chat Commands " + "="*21)
        print("/help         - Show this help message")
        print("/file <paths> - Send file(s) with your next message")
        print("/context      - Get the full conversation history")
        print("/save         - Manually save the conversation to the DB")
        print("/new          - Start a new chat session")
        print("/model        - Show the current model configuration")
        print("/exit or /quit- Exit and DELETE the chat from the database")
        print("Ctrl+C        - Exit and CLOSE the chat from memory only")
        print("="*59)

    show_help()
    initial_file_paths = [args.file] if args.file else []

    while True:
        try:
            user_input = input("\nYou: ").strip()
            if not user_input: continue

            if user_input.lower() in ('/exit', '/quit'):
                if chat_id:
                    delete_chat(args.base_url, chat_id)
                break
            
            if user_input.lower() == '/help':
                show_help()
                continue
            
            if user_input.lower() == '/new':
                if chat_id:
                    delete_chat(args.base_url, chat_id)
                chat_id = create_chat(args.base_url, model_parameters)
                if not chat_id: sys.exit("Failed to create new chat.")
                continue

            if user_input.lower() == '/model':
                print(json.dumps(model_parameters, indent=2))
                continue

            if user_input.lower() == '/context':
                get_chat_context(args.base_url, chat_id)
                continue

            if user_input.lower() == '/save':
                save_chat_context(args.base_url, chat_id)
                continue

            file_paths_for_turn = initial_file_paths
            message_to_send = user_input
            if user_input.lower().startswith('/file '):
                parts = user_input.split()
                file_paths_for_turn.extend(parts[1:])
                message_to_send = input("Message to send with file(s) (or press Enter): ").strip()
                if not message_to_send:
                    message_to_send = f"Please analyze the attached file(s): {[os.path.basename(p) for p in file_paths_for_turn]}"

            print("Bot: ", end="", flush=True)
            response = chat(args.base_url, chat_id, message_to_send, file_paths_for_turn)
            print(response)
            
            initial_file_paths = []

        except KeyboardInterrupt:
            if chat_id:
                close_chat(args.base_url, chat_id)
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            break
    
    print("\n--- Chat Ended ---")

if __name__ == "__main__":
    main()