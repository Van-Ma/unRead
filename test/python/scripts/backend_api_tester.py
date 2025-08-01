# backend_api_tester.py
# A terminal-based testing harness for the chatbot Flask API.

import requests
import argparse
import sys
import json
import os
from typing import Dict, Any, List

# Added new endpoints for context management
ENDPOINTS = {
    "change_model": "/change_model",
    "create_chat": "/create_chat",
    "chat": "/chat",
    "get_context": "/chat_context/",  # Note the trailing slash
    "save_context": "/save_chat_context",
    "delete_chat": "/delete_chat"
}

# --- API Call Functions ---

def create_chat(base_url: str, model_parameters: Dict[str, Any]) -> str:
    """Sends a request to create a new chat with specified model parameters."""
    print("--> Creating new chat with model parameters:")
    print(json.dumps(model_parameters, indent=2))
    payload = {"modelParameters": model_parameters}
    try:
        url = f"{base_url}{ENDPOINTS['create_chat']}"
        response = requests.post(url, json=payload, timeout=30000)
        if response.status_code == 200:
            chat_id = response.json().get("chatId")
            print(f"<-- Success. Chat ID = {chat_id}")
            return chat_id
        else:
            print(f"<-- Error ({response.status_code}): {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"<-- API Connection Error: {e}")
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
    
    try:
        url = f"{base_url}{ENDPOINTS['chat']}"
        response = requests.post(url, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get('response', 'Error: No response field in JSON.')
    except requests.exceptions.RequestException as e:
        return f"API Error: {e}\nResponse: {e.response.text if e.response else 'N/A'}"

def delete_chat(base_url: str, chat_id: str):
    """Sends a request to delete (reset) the chat."""
    print(f"--> Deleting chat {chat_id}...")
    try:
        url = f"{base_url}{ENDPOINTS['delete_chat']}"
        response = requests.post(url, json={"chatId": chat_id}, timeout=30)
        response.raise_for_status()
        print(f"<-- Success: {response.json().get('message')}")
    except requests.exceptions.RequestException as e:
        print(f"<-- API Error: {e}")

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
    try:
        url = f"{base_url}{ENDPOINTS['save_context']}"
        response = requests.post(url, json={"chatId": chat_id}, timeout=30)
        response.raise_for_status()
        print(f"<-- Success: {response.json().get('message')}")
    except requests.exceptions.RequestException as e:
        print(f"<-- API Error: {e}")

# --- Main Application Logic ---

def main():
    """Main function to run the terminal chat client."""
    parser = argparse.ArgumentParser(description="Terminal client to test the chatbot API.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000", help="Base URL of the API.")
    parser.add_argument("--model-version", default="Base", choices=["Base", "RAG"], help="Model version.")
    parser.add_argument("--model-name", default="meta-llama/Llama-3.2-1B-Instruct", help="Specific model name.")
    parser.add_argument("--use-kv-cache", action="store_true", help="Enable KV caching.")
    parser.add_argument("--file", help="Optional path to a file for the first message.")
    args = parser.parse_args()

    model_parameters = {
        "framework_type": "LangChain",
        "backend": "HuggingFace",
        "model_version": args.model_version,
        "hf_params": {"model_name": args.model_name, "use_kv_cache": args.use_kv_cache}
    }
    
    chat_id = create_chat(args.base_url, model_parameters)
    if not chat_id:
        sys.exit("Failed to create chat. Exiting.")

    print("\n--- Chat Started ---")
    
    def show_help():
        print("\n" + "="*19 + " Chat Commands " + "="*19)
        print("/help         - Show this help message")
        print("/file <paths> - Send file(s) with your next message")
        print("/context      - Get the full conversation history")
        print("/save         - Manually save the conversation to the DB")
        print("/new          - Start a new chat session")
        print("/model        - Show the current model configuration")
        print("/exit or /quit- Exit the chat")
        print("="*55)

    show_help()
    
    initial_file_paths = [args.file] if args.file else []

    while True:
        try:
            prompt = "\nYou: "
            user_input = input(prompt).strip()
            if not user_input: continue

            if user_input.lower() in ('/exit', '/quit'): break
            
            if user_input.lower() == '/help':
                show_help()
                continue
            
            if user_input.lower() == '/new':
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

            # Handle file uploads
            file_paths_for_turn = initial_file_paths
            message_to_send = user_input

            if user_input.lower().startswith('/file '):
                # Improved: Allows sending a message with the files
                parts = user_input.split()
                file_paths_for_turn.extend(parts[1:]) # Add new files
                message_to_send = input("Message to send with file(s) (or press Enter): ").strip()
                if not message_to_send:
                    message_to_send = f"Please analyze the attached file(s): {[os.path.basename(p) for p in file_paths_for_turn]}"

            print("Bot: ", end="", flush=True)
            response = chat(args.base_url, chat_id, message_to_send, file_paths_for_turn)
            print(response)
            
            initial_file_paths = [] # Clear initial files after the first use

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\nAn unexpected error occurred: {e}")
            break
    
    if chat_id:
        delete_chat(args.base_url, chat_id)
    print("\n--- Chat Ended ---")

if __name__ == "__main__":
    main()