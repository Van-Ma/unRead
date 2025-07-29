# Chat session and model lifecycle management

import logging
import json
import uuid
import datetime
from typing import Optional, Dict, List, Any, Union

from models.langchain import get_global_app, set_global_app
from models.model_parameters import ModelParameters
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatManager:
    """Manages chat sessions with LangGraph."""

    def __init__(self):
        logging.info("ChatManager initialized, ready to interact with global LangGraph app.")
        # Track model params per chat
        self._chat_parameters: Dict[str, ModelParameters] = {}
        # File content storage
        self._chat_file_content: Dict[str, List[Dict[str, str]]] = {}
        # Chat history storage
        self._chat_history: Dict[str, List[Dict[str, str]]] = {}

    @staticmethod
    def _get_file_extension(filename: str) -> str:
        """Get the file extension for syntax highlighting."""
        if not filename or not isinstance(filename, str):
            return ""
        
        # Get the file extension
        if "." in filename:
            ext = filename.split(".")[-1].lower()
            # Map common extensions to language identifiers
            extension_map = {
                'py': 'python',
                'js': 'javascript',
                'jsx': 'jsx',
                'ts': 'typescript',
                'tsx': 'tsx',
                'html': 'html',
                'css': 'css',
                'json': 'json',
                'md': 'markdown',
                'txt': 'text',
                'csv': 'csv',
                'xml': 'xml',
                'yaml': 'yaml',
                'yml': 'yaml'
            }
            return extension_map.get(ext, ext)
        return ""

    def create_chat(self, model_params: Optional[Dict] = None) -> tuple[str, str]:
        """Register a new chat and eagerly warm-up the chosen global app."""
        # Auto-generate a new chat UUID
        chat_id: str = str(uuid.uuid4())
        
        # Validate input
        if model_params is None:
            model_params = {}
            
        # Set default values if not provided
        if 'framework_type' not in model_params:
            model_params['framework_type'] = 'LangChain'
        if 'backend' not in model_params:
            model_params['backend'] = 'HuggingFace'
        if 'model_version' not in model_params:
            model_params['model_version'] = 'Base'
            
        # Ensure hf_params exists and has required fields
        if 'hf_params' not in model_params:
            model_params['hf_params'] = {}
        if 'model_name' not in model_params['hf_params']:
            model_params['hf_params']['model_name'] = 'meta-llama/Llama-3.1-1B-Instruct'
        if 'use_kv_cache' not in model_params['hf_params']:
            model_params['hf_params']['use_kv_cache'] = True

        # Log config
        logging.info(f"Creating chat {chat_id} with model parameters: {model_params}")
        
        # Save settings
        self._chat_parameters[chat_id] = model_params
        # Initialize empty history and file content for this chat
        self._chat_history[chat_id] = []
        self._chat_file_content[chat_id] = []
        
        # Update the global app with the new model parameters
        set_global_app(model_params)
            
        # Init model
        get_global_app().get_state({"configurable": {"thread_id": chat_id}})
        
        message = f"Chat {chat_id} ready with {model_params['hf_params'].get('model_name')} (version: {model_params.get('model_version', 'Base')})"
        logging.info(message)
        return chat_id, message

    def chat(
        self, 
        chat_id: str, 
        user_input: str, 
        files: Optional[List[Dict[str, str]]] = None,
        model_params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Process a chat message with optional file attachments.
        
        Args:
            chat_id: The ID of the chat
            user_input: The user's message text
            files: Optional list of files, where each file is a dict with 'name' and 'content' keys
            model_params: Optional model parameters for this chat
            
        Returns:
            Dict containing the response and error status
        """
        logging.info(f"=== New chat message for {chat_id} ===")
        logging.info(f"User input: {user_input}")

        # Lazy init chat
        if chat_id not in self._chat_parameters:
            self._chat_parameters[chat_id] = model_params or {}
            self._chat_history[chat_id] = [
                {
                    "role": "system",
                    "content": """You are a helpful assistant that can reference uploaded files. 
                    When files are uploaded, they will be shown to you with their contents. 
                    You can reference them by their number (e.g., 'File 1') or name. 
                    Always acknowledge when files are uploaded and summarize their purpose if possible. 
                    Don't ask the user for the file name - it will be provided to you in the context.""".replace('    ', '').strip()
                }
            ]
            self._chat_file_content[chat_id] = []
        
        # Get current state
        chat_params = self._chat_parameters.get(chat_id, {})
        model_version = chat_params.get("model_version", "Base")
        history = self._chat_history[chat_id]
        file_contents = self._chat_file_content[chat_id]
        
        # Process files
        files_added = False
        if files and isinstance(files, list):
            valid_files = []
            for file_info in files:
                if not isinstance(file_info, dict) or 'content' not in file_info:
                    continue
                name = file_info.get('name', f'file_{len(file_contents) + 1}.txt')
                content = file_info['content']
                valid_files.append({'name': name, 'content': content})
                logging.info(f"Processing file: {name} ({len(content)} chars)")
            
            if valid_files:
                file_contents.extend(valid_files)
                files_added = True
                logging.info(f"Added {len(valid_files)} files to chat {chat_id}")
                
                # Build file context
                file_context = [
                    "## 📎 ATTACHED FILES",
                    "The following files have been uploaded and are available for reference:",
                    "- Reference files by their number (e.g., 'File 1') or by their name"
                ]
                for idx, file_info in enumerate(file_contents, 1):
                    name = file_info.get('name', f'File {idx}')
                    content = file_info.get('content', '')
                    file_context.extend([
                        f"\n### File {idx}: {name}",
                        f"```{self._get_file_extension(name)}",
                        content[:1000] + ("..." if len(content) > 1000 else ""),
                        "```"
                    ])
                file_context.extend([
                    "",
                    "IMPORTANT: Do not ask for the file name - it has already been provided above.",
                    "When responding, you can directly reference the file contents as needed."
                ])
                
                # Add file context to history if files were just added
                history.append({
                    "role": "system",
                    "content": "\n".join(file_context)
                })
        
        # Handle empty input
        if user_input.strip():
            history.append({"role": "user", "content": user_input})
        else:
            # Add default message for files
            if files_added:
                user_input = "I've uploaded some files for you to analyze."
                history.append({"role": "user", "content": user_input})
        
        # Get the global app instance
        current_app = get_global_app()
        
        try:
            # Prepare the system prompt
            system_prompt = SystemMessage(content="""You are a helpful assistant that can reference uploaded files.
When files are uploaded, they will be shown to you with their contents.
You can reference them by their name or number (e.g., 'File 1' or 'test1.txt').""")
            
            # Prepare the user message
            user_message = HumanMessage(content=user_input.strip() or "I've uploaded some files for you to analyze.")
            
            # Prepare file context if we have files
            file_messages = []
            if file_contents:
                for idx, file_info in enumerate(file_contents, 1):
                    name = file_info.get('name', f'File {idx}')
                    content = file_info.get('content', '')
                    file_content = [
                        f"## FILE: {name}",
                        f"```{self._get_file_extension(name)}",
                        content[:1000] + ("..." if len(content) > 1000 else ""),
                        "```"
                    ]
                    file_messages.append(SystemMessage(content="\n".join(file_content)))
            
            # Prepare the full message list
            input_messages = [system_prompt] + file_messages + [user_message]
            
            # Debug logging
            logging.info(f"Sending {len(input_messages)} messages to model:")
            for i, msg in enumerate(input_messages):
                content_preview = str(msg.content)[:100] + ("..." if len(str(msg.content)) > 100 else "")
                logging.info(f"  {i+1}. {type(msg).__name__}: {content_preview}")
            
            # Call the model with the full context
            output = current_app.invoke(
                {
                    "messages": input_messages,
                    "file_contents": file_contents,
                    "rag_enabled": model_version == "RAG"
                },
                {
                    "configurable": {"thread_id": chat_id},
                    "recursion_limit": 100
                }
            )
            
            # Format response
            response = output["messages"][-1].content if output.get("messages") else "I'm sorry, I couldn't generate a response."
            
            return {
                "status": "success",
                "response": response,
                "error": False,
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now().isoformat(),
                "files_added": files_added
            }
            
        except Exception as e:
            # Clean up on error
            if history and history[-1]["role"] == "user":
                history.pop()
            logging.error(f"Error in chat generation: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "response": f"An error occurred: {str(e)}",
                "error": True,
                "message_id": str(uuid.uuid4()),
                "timestamp": datetime.datetime.now().isoformat()
            }

    def get_context_history(self, chat_id: str) -> List[Dict[str, str]]:
        logging.info(f"Getting chat context history for chat {chat_id}.")
        
        if chat_id not in self._chat_history:
            return []
            
        return self._chat_history[chat_id]

        config = {"configurable": {"thread_id": chat_id}}
        try:
            state = current_app.get_state(config)
            history_dicts = []
            if state and state.messages:
                for message in state.messages:
                    history_dicts.append({"role": message.type, "content": message.content})
            return history_dicts
        except Exception as e:
            logging.warning(f"Could not retrieve state for chat {chat_id}: {e}")
            return []

    def clear_context(self, chat_id: str) -> None:
        """Clear the conversation context for a chat."""
        if chat_id in self._chat_file_content:
            self._chat_file_content[chat_id] = []
        if chat_id in self._chat_history:
            self._chat_history[chat_id] = []

    def delete_chat(self, chat_id: str) -> tuple[bool, str]:
        """Delete a chat and its associated resources.
        
        Returns:
            tuple[bool, str]: A tuple containing success status and a message
        """
        logging.info(f"Deleting chat {chat_id}.")
        try:
            if chat_id not in self._chat_parameters:
                return False, f"Chat {chat_id} not found"

            # Get chat config
            chat_params = self._chat_parameters.get(chat_id, {})
            model_version = chat_params.get("model_version", "Base")
            
            # Get the global app instance
            current_app = get_global_app()
                
            config = {"configurable": {"thread_id": chat_id}}

            # Cleanup
            try:
                # Clear state
                current_app.get_state(config)
                
                # Clean local state
                self._chat_parameters.pop(chat_id, None)
                self._chat_file_content.pop(chat_id, None)
                self._chat_history.pop(chat_id, None)
                
                logging.info(f"Successfully deleted chat {chat_id}")
                return True, f"Chat {chat_id} deleted successfully."
                
            except Exception as e:
                # Fallback cleanup
                self._chat_parameters.pop(chat_id, None)
                self._chat_file_content.pop(chat_id, None)
                self._chat_history.pop(chat_id, None)
                logging.warning(f"Cleaned up chat {chat_id} but state may persist: {e}")
                return True, f"Chat {chat_id} cleaned up, but some state may persist."
                
        except Exception as e:
            error_msg = f"Failed to delete chat {chat_id}: {str(e)}"
            logging.error(error_msg)
            return False, error_msg

    def change_global_model(self, model_params: ModelParameters) -> tuple[bool, str]:
        """Switch the global model for new chats.
        
        This updates the global LangGraph app that will be used for new chat sessions.
        Existing chats will continue to use their original model parameters.
        
        Args:
            model_params: The new model parameters to use for future chats
            
        Returns:
            tuple[bool, str]: Success status and message
        """
        from models.langchain import set_global_app
        
        try:
            # Validate input
            if not isinstance(model_params, dict):
                raise ValueError("model_params must be a dictionary")
                
            # Check HF params
            if 'hf_params' not in model_params:
                model_params['hf_params'] = {}
                
            # Set default values if not provided
            if 'model_name' not in model_params['hf_params']:
                model_params['hf_params']['model_name'] = 'meta-llama/Llama-3.1-1B-Instruct'
            if 'use_kv_cache' not in model_params['hf_params']:
                model_params['hf_params']['use_kv_cache'] = True
                
            # Set required fields
            if 'framework_type' not in model_params:
                model_params['framework_type'] = 'LangChain'
            if 'backend' not in model_params:
                model_params['backend'] = 'HuggingFace'
                
            logging.info(f"Changing global model to: {model_params}")
            
            # Update the global app with the new parameters
            set_global_app(model_params)
            
            # Confirm update
            set_global_app(model_params)
                
            message = f"Global model changed to {model_params['hf_params'].get('model_name')} (version: {model_params.get('model_version', 'Base')})"
            logging.info(message)
            return True, message
        except Exception as e:
            error_msg = f"Failed to switch global model: {str(e)}"
            logging.error(error_msg)
            return False, error_msg
