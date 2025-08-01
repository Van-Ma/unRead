# chat_manager.py

import logging
import uuid
from typing import Optional, Dict, List, Any

from models.langchain import get_global_app, set_global_app, _current_model_params
from models.model_parameters import ModelParameters
from models.kv_cache_hf_model import reset_all_kv_caches, reset_kv_cache_for_chat
from vectorstore_manager import reset_all_vector_stores
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

class ChatManager:
    def create_chat(self, model_params: ModelParameters) -> tuple[str, str]:
        debug_log("Entered create_chat in ChatManager.")
        print("called create chat", flush = True)
        chat_id = str(uuid.uuid4())
        print("trying to set gloval app1", flush = True)
        if _current_model_params is None or _current_model_params != model_params:
            print("trying to set gloval app2", flush = True)
            set_global_app(model_params)
        return chat_id, f"Chat {chat_id} ready."

    def chat(self, chat_id: str, user_input: str, files: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
        try:
            graph_input = {"messages": [HumanMessage(content=user_input)], "file_contents": files or [], "chat_id": chat_id}
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
        try:
            reset_kv_cache_for_chat(chat_id)
            self.update_context(chat_id, [])
            return True, f"Chat {chat_id} has been reset."
        except Exception as e:
            return False, f"Failed to reset chat {chat_id}: {e}"
            
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