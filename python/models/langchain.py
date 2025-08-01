# langchain.py

import logging
from typing import Any, List, Dict, Sequence

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_huggingface import HuggingFacePipeline
from langchain_huggingface.chat_models import ChatHuggingFace
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

from typing_extensions import TypedDict, Annotated

from models.model_parameters import ModelParameters
from models.kv_cache_hf_model import KVCacheHFModel
from ..vectorstore_manager import get_vectorstore_for_chat

# --- State & Globals ---
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    file_contents: List[Dict[str, str]]
    chat_id: str
    context: List[Document]

_global_app: Any = None
_current_model_params: ModelParameters = None

class LangChainBase:
    def __init__(self, model_params: ModelParameters, **kwargs):
        self.params = model_params
        hf_params = model_params["hf_params"]
        if hf_params.get("use_kv_cache"):
            self.llm = KVCacheHFModel(hf_params=hf_params)
        else:
            self.llm = self._load_stateless_llm(model_params)

    def _call_model_node(self, state: ChatState) -> Dict[str, Any]:
        final_messages = self._prepare_messages(state)
        try:
            if isinstance(self.llm, KVCacheHFModel):
                prompt = self.llm.tokenizer.apply_chat_template(final_messages, add_generation_prompt=True, tokenize=False)
                response_text = self.llm.invoke(prompt, chat_id=state['chat_id'])
            else:
                response = self.llm.invoke(final_messages)
                response_text = response.content
            return {"messages": [AIMessage(content=self._strip_special_tokens(response_text))]}
        except Exception as e:
            return {"messages": [AIMessage(content=f"An error occurred: {e}")]}

    def _prepare_messages(self, state: ChatState) -> List[BaseMessage]:
        messages = state["messages"]
        file_contents = state.get("file_contents", [])
        if not file_contents:
            return list(messages)
        file_context_parts = ["The user has provided the following files for context:"]
        for file_info in file_contents:
            if content := file_info.get('content', '').strip():
                file_context_parts.extend([f"\n### File: {file_info.get('name')}", "```", content[:1000], "```"])
        return [SystemMessage(content="\n".join(file_context_parts))] + list(messages)

    def _strip_special_tokens(self, text: str) -> str: return text
    def _load_stateless_llm(self, params): return None # Placeholder for stateless LLM loading

class LangChainRAG(LangChainBase):
    def __init__(self, model_params: ModelParameters, **kwargs):
        super().__init__(model_params=model_params, **kwargs)
        if model_params["model_version"] != "RAG": raise ValueError("Invalid model_version for LangChainRAG.")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    # The nodes _add_documents_node, _retrieve_node, _generate_response_node, _should_retrieve
    # can remain as they were in the previous version.

def set_global_app(model_params: ModelParameters) -> None:
    global _global_app, _current_model_params
    _current_model_params = model_params
    workflow = StateGraph(ChatState)
    model_instance = LangChainRAG(model_params) if model_params.get("model_version") == "RAG" else LangChainBase(model_params)
    # The rest of the graph definition logic remains the same
    _global_app = workflow.compile(checkpointer=PostgresSaver.from_conn_string("..."))

def get_global_app() -> Any:
    global _global_app
    if _global_app is None:
        default_params: ModelParameters = {"framework_type": "LangChain", "backend": "HuggingFace", "model_version": "Base", "hf_params": {"model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "use_kv_cache": False}}
        set_global_app(default_params)
    return _global_appgit 