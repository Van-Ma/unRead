# langchain.py

import logging
import os
import psycopg 
from typing import Any, List, Dict, Sequence

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_huggingface import HuggingFacePipeline
from langchain_huggingface.chat_models import ChatHuggingFace
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver # Corrected Import

from typing_extensions import TypedDict, Annotated

from models.model_parameters import ModelParameters
from models.kv_cache_hf_model import KVCacheHFModel
from vectorstore_manager import get_vectorstore_for_chat



# --- State & Globals ---
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    file_contents: List[Dict[str, str]]
    chat_id: str
    context: List[Document]

_global_app: Any = None
_current_model_params: ModelParameters = None

# # This connection is created once when the module is first loaded.
# try:
#     print("1")
#     PG_URI = os.getenv("LANGGRAPH_PG_CHECKPOINT_URI")
#     if PG_URI is None:
#         raise RuntimeError("LANGGRAPH_PG_CHECKPOINT_URI must be set in your .env file!")
#     print("2")
    
#     # Ensure the 'chats' schema is in the search path for the connection
#     conn_string = PG_URI + "?options=-csearch_path%3Dchats"
#     print("3")
#     db_connection = psycopg.connect(conn_string)
#     print("4")
#     logging.info("Successfully created persistent PostgreSQL connection for LangGraph checkpointer.")
# except Exception as e:
#     logging.error(f"Failed to connect to PostgreSQL for checkpointer: {e}")
#     print("5")
#     db_connection = None

db_connection = None
logging.warning("PostgreSQL connection is DISABLED. Using in-memory checkpointer for testing.")

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
            else: # Stateless ChatHuggingFace
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
    
    def _load_stateless_llm(self, model_params: ModelParameters) -> ChatHuggingFace:
        """Loads a stateless HuggingFacePipeline-based model."""
        print("loading stateless!", flush=True)
        logging.info(f"oading stateless!")
        return

        
        from langchain_huggingface import HuggingFacePipeline
        from langchain_huggingface.chat_models import ChatHuggingFace
        from transformers import pipeline as hf_pipeline
        from models.model_cache import GLOBAL_HF_MODEL_CACHE
        
        hf_params = model_params["hf_params"]
        model_name = hf_params["model_name"]
        
        logging.info(f"Initializing stateless ChatHuggingFace with model '{model_name}'.")
        print("loading stateless model1!!", flush = True)
        try:
            if model_name in GLOBAL_HF_MODEL_CACHE:
                logging.info(f"Using cached HuggingFace model for '{model_name}'.")
                loaded_model = GLOBAL_HF_MODEL_CACHE[model_name]['model']
                loaded_tokenizer = GLOBAL_HF_MODEL_CACHE[model_name]['tokenizer']
            else:
                # This is the same loading logic from your original files
                logging.info(f"Loading HuggingFace model '{model_name}' (not in cache)...")
                device = "cuda" if torch.cuda.is_available() else "cpu"
                loaded_tokenizer = AutoTokenizer.from_pretrained(model_name)
                loaded_model = AutoModelForCausalLM.from_pretrained(model_name, torch_dtype=torch.bfloat16).to(device)
                if loaded_tokenizer.pad_token is None:
                    loaded_tokenizer.pad_token = loaded_tokenizer.eos_token
                
                GLOBAL_HF_MODEL_CACHE[model_name] = {
                    'model': loaded_model,
                    'tokenizer': loaded_tokenizer
                }
                logging.info(f"HuggingFace model '{model_name}' cached.")

            # Create the transformers pipeline
            gen_kwargs = dict(max_new_tokens=512, do_sample=True, temperature=0.6, top_p=0.9)
            pipe = hf_pipeline(
                "text-generation",
                model=loaded_model,
                tokenizer=loaded_tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                **gen_kwargs,
            )

            # Wrap it in the LangChain classes
            pipeline_llm = HuggingFacePipeline(pipeline=pipe)
            print(" done loading stateless model1!!", flush = True)
            return ChatHuggingFace(llm=pipeline_llm)

        except Exception as e:
            logging.error(f"Failed to load stateless HuggingFace model '{model_name}': {e}", exc_info=True)
            raise

class LangChainRAG(LangChainBase):
    def __init__(self, model_params: ModelParameters, **kwargs):
        super().__init__(model_params=model_params, **kwargs)
        if model_params["model_version"] != "RAG": raise ValueError("Invalid model_version for LangChainRAG.")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)

    def _add_documents_node(self, state: ChatState) -> Dict[str, Any]:
        chat_id = state["chat_id"]
        files = state.get("file_contents", [])
        if not files: return {}
        all_docs = [doc for file_info in files if (content := file_info.get('content', '').strip()) for chunk in self.text_splitter.split_text(content) for doc in [Document(page_content=chunk, metadata={'source': file_info.get('name')})]]
        if all_docs: get_vectorstore_for_chat(chat_id).add_documents(all_docs)
        return {}

    def _retrieve_node(self, state: ChatState) -> Dict[str, Any]:
        retriever = get_vectorstore_for_chat(state["chat_id"]).as_retriever()
        return {"context": retriever.invoke(state["messages"][-1].content)}

    def _generate_response_node(self, state: ChatState) -> Dict[str, Any]:
        response = self.llm.invoke(...) # Simplified
        return {"messages": [AIMessage(content=response.content)]}

    def _should_retrieve(self, state: ChatState) -> str:
        return "retrieve" if get_vectorstore_for_chat(state["chat_id"]).index.ntotal > 1 else "base_chat"

def set_global_app(model_params: ModelParameters) -> None:
    """Builds and compiles the appropriate LangGraph app, setting it globally."""
    global _global_app, _current_model_params
    _current_model_params = model_params
    logging.info(f"Building LangGraph app with model params: {model_params}")
    
    workflow = StateGraph(ChatState)
    model_instance = LangChainRAG(model_params) if model_params.get("model_version") == "RAG" else LangChainBase(model_params)
    
    # Define the graph structure based on the model version
    if model_params.get("model_version") == "RAG":
        # Define the RAG graph nodes
        workflow.add_node("add_documents", model_instance._add_documents_node)
        workflow.add_node("retrieve", model_instance._retrieve_node)
        workflow.add_node("generate_rag", model_instance._generate_response_node)
        workflow.add_node("base_chat", model_instance._call_model_node) # Fallback if no docs
        
        # Define the RAG graph flow
        workflow.set_entry_point("add_documents")
        workflow.add_conditional_edges(
            "add_documents",
            model_instance._should_retrieve,
            {
                "retrieve": "retrieve",
                "base_chat": "base_chat"
            }
        )
        workflow.add_edge("retrieve", "generate_rag")
        workflow.add_edge("generate_rag", END)
        workflow.add_edge("base_chat", END)
    else:
        # Define the Base graph
        workflow.add_node("call_model", model_instance._call_model_node)
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", END)
    
    # Pass the persistent connection to the checkpointer
    if db_connection:
        checkpointer = PostgresSaver(sync_connection=db_connection)
        _global_app = workflow.compile(checkpointer=checkpointer)
        logging.info("Global app compiled and ready with PostgreSQL checkpointer.")
    else:
        # Fallback to in-memory if the DB connection failed during startup
        logging.warning("Database connection failed. Compiling graph with in-memory checkpointer.")
        _global_app = workflow.compile()

def get_global_app() -> Any:
    global _global_app
    if _global_app is None:
        default_params: ModelParameters = {"framework_type": "LangChain", "backend": "HuggingFace", "model_version": "Base", "hf_params": {"model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "use_kv_cache": False}}
        set_global_app(default_params)
    return _global_app