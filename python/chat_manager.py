# chat_manager.py

import logging
import uuid
from typing import Optional, Dict, List, Any
from context_manager import ContextManager 

from models.langchain_model import get_global_app, set_global_app, _current_model_params
from models.model_parameters import ModelParameters
from models.kv_cache_hf_model import reset_all_kv_caches, reset_kv_cache_for_chat
from vectorstore_manager import reset_all_vector_stores, reset_vectorstore_for_chat
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class ChatManager:
    def create_chat(self, model_params: ModelParameters) -> tuple[str, str]:
        chat_id = str(uuid.uuid4())
        if _current_model_params is None or _current_model_params != model_params:
            set_global_app(model_params)
        return chat_id, f"Chat {chat_id} ready."

    def chat(self, chat_id: str, user_id: str, user_input: str, files: Optional[List[Any]] = None) -> Dict[str, Any]:
        try:
            parsed_context_files = []
            if files:
                for f in files:
                    context_file = self.context_manager.parse_and_create_context_file(user_id, chat_id, f)
                    if context_file:
                        saved = self.context_manager.save_context_file(user_id, context_file)
                        if saved:
                            parsed_context_files.append({
                                "file_name": context_file.file_name,
                                "content": context_file.file_content.decode("utf-8"),
                            })

            graph_input = {
                "messages": [HumanMessage(content=user_input)],
                "file_contents": parsed_context_files,
                "chat_id": chat_id,
            }
            config = {"configurable": {"thread_id": chat_id}}
            final_state = get_global_app().invoke(graph_input, config)
            if final_state and final_state.get("messages"):
                return {"status": "success", "response": final_state["messages"][-1].content}
            raise ValueError("Graph execution did not return a valid state.")
        except Exception as e:
            return {"status": "error", "response": f"An error occurred: {e}"}

    def get_context(self, chat_id: str) -> List[Dict[str, str]]:
        state = get_global_app().get_state({"configurable": {"thread_id": chat_id}})
        return [{"role": msg.type, "content": msg.content} for msg in state.values["messages"]] if state and state.values.get("messages") else []

    def update_context(self, chat_id: str, new_context: List[Dict[str, str]]) -> None:
        messages = [HumanMessage(content=msg['content']) if msg['role'] == 'user' else AIMessage(content=msg['content']) for msg in new_context]
        get_global_app().update_state({"configurable": {"thread_id": chat_id}}, {"messages": messages})

    def delete_chat(self, chat_id: str) -> tuple[bool, str]:
        """
        Performs a "hard delete" by removing the chat's history from the
        checkpointer (database) and clearing any in-memory stores.
        """
        logging.info(f"Performing hard delete for chat {chat_id}.")
        try:
            # Clear in-memory stores first
            reset_kv_cache_for_chat(chat_id)
            reset_vectorstore_for_chat(chat_id)

            # Get the checkpointer and delete the thread's history
            current_app = get_global_app()
            if hasattr(current_app, 'checkpointer') and current_app.checkpointer:
                config = {"configurable": {"thread_id": chat_id}}
                current_app.checkpointer.delete(config)
                message = f"Chat {chat_id} has been deleted from memory and the database."
            else:
                message = f"Chat {chat_id} has been reset from memory (no persistent checkpointer configured)."

            return True, message
        except Exception as e:
            logging.error(f"Failed to delete chat {chat_id}: {e}", exc_info=True)
            return False, f"Failed to delete chat {chat_id}: {e}"
    
    def close_chat(self, chat_id: str) -> tuple[bool, str]:
        """
        Closes a chat by unloading it from local memory (KV cache, vector store)
        but leaves the history in the database untouched.
        """
        logging.info(f"Closing chat {chat_id} from memory.")
        try:
            # Clear the stateful LLM's memory
            reset_kv_cache_for_chat(chat_id)
            
            # Clear the RAG documents from memory
            reset_vectorstore_for_chat(chat_id)
            
            return True, f"Chat {chat_id} has been closed and unloaded from memory."
        except Exception as e:
            logging.error(f"Failed to close chat {chat_id}: {e}", exc_info=True)
            return False, f"Failed to close chat {chat_id}: {e}"
 
    def save_chat_context(self, chat_id: str) -> tuple[bool, str]:
        try:
            current_app = get_global_app()
            if not hasattr(current_app, 'checkpointer') or not current_app.checkpointer:
                return False, "Persistence is disabled; the app has no checkpointer."
            config = {"configurable": {"thread_id": chat_id}}
            snapshot = current_app.get_state(config)
            if not snapshot: return False, f"No state found for chat_id: {chat_id}."
            current_app.checkpointer.put(config, snapshot.to_checkpoint())
            return True, f"Successfully saved context for chat {chat_id}."
        except Exception as e:
            return False, f"Failed to save context: {e}"

    def change_global_model(self, new_model_params: ModelParameters) -> tuple[bool, str]:
        old_params = _current_model_params
        if old_params == new_model_params: return True, "Model is already set to the requested configuration."

        old_version = old_params.get("model_version", "N/A") if old_params else "N/A"
        new_version = new_model_params.get("model_version")
        
        message = ""
        if old_version != new_version:
            message = f"Switching from '{old_version}' to '{new_version}'. All conversation histories and RAG documents will be wiped."
            reset_all_vector_stores()
            reset_all_kv_caches()
        else:
            message = f"Changing underlying model within version '{new_version}'. Chat histories will be preserved, but KV cache will be reset."
            reset_all_kv_caches()
        
        set_global_app(new_model_params)
        return True, message
