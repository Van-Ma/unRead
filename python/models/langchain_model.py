# langchain.py

import logging
import os
import torch
from typing import Any, List, Dict, Sequence
from database_connect import db_connection

# --- Third-party imports ---
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline as hf_pipeline
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_huggingface import HuggingFacePipeline, HuggingFaceEmbeddings
from langchain_huggingface.chat_models import ChatHuggingFace
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict, Annotated

# --- Local application imports ---
from models.model_parameters import ModelParameters
from models.kv_cache_hf_model import KVCacheHFModel
from vectorstore_manager import get_vectorstore_for_chat
from models.model_cache import GLOBAL_HF_MODEL_CACHE

# --- State & Globals ---
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
    file_contents: List[Dict[str, str]]
    chat_id: str
    context: List[Document]

_global_app: Any = None
_current_model_params: ModelParameters = None



# --- Core Classes ---
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

    # Place document context into system message
    # def _prepare_messages(self, state: ChatState) -> List[BaseMessage]:
    #     """Prepares messages, including a streamlined system prompt for file context."""
    #     messages = state["messages"]
    #     file_contents = state.get("file_contents", [])
    #     if not file_contents:
    #         return list(messages)

    #     # Create a more helpful, conversational prompt
    #     file_context_parts = [
    #         "You are a helpful AI assistant. The user has provided the following file(s) for context. Your primary goal is to answer the user's questions based on this context. Be conversational and concise."
    #     ]
    #     for file_info in file_contents:
    #         if content := file_info.get('content', '').strip():
    #             file_context_parts.extend([
    #                 f"\n--- Start of File: {file_info.get('name')} ---",
    #                 content[:2000], # Limit context size
    #                 f"--- End of File: {file_info.get('name')} ---"
    #             ])
        
    #     system_prompt = "\n".join(file_context_parts)
    #     print("context: 123")
    #     print(system_prompt)
    #     return [SystemMessage(content=system_prompt)] + list(messages)

    # Place document context in human message
    # In python/models/langchain.py, inside the LangChainBase class

    def _prepare_messages(self, state: ChatState) -> List[BaseMessage]:
        """
        Prepares messages for the LLM. If files are present, their content is
        injected directly into the latest user message to ensure the model sees it.
        """
        messages = state["messages"]
        file_contents = state.get("file_contents", [])

        # The first message in the history is always a system prompt setting the persona.
        # Note: In your _generate_response_node for RAG, you have a more specific one.
        # This one is a good general default.
        system_prompt = "You are a helpful AI assistant."
        
        if not file_contents:
            # If no files, just ensure the system prompt is there and return
            return [SystemMessage(content=system_prompt)] + list(messages)

        # --- If there ARE files, inject their content into the user's message ---

        # 1. Construct the file context string
        file_context_str = "\n\n--- Start of Provided File Content ---\n"
        for file_info in file_contents:
            if content := file_info.get('content', '').strip():
                file_context_str += f"\n[File: {file_info.get('name')}]\n{content[:2000]}\n"
        file_context_str += "--- End of Provided File Content ---\n"

        # 2. Get the history and the last user message
        history = list(messages)
        last_user_message = history.pop()

        # 3. Create a new, combined content for the last user message
        new_content = (
            f"Based on the following content, please answer my question.\n"
            f"{file_context_str}\n"
            f"My Question: \"{last_user_message.content}\""
        )
        
        # 4. Create a new HumanMessage with the combined content
        new_user_message = HumanMessage(content=new_content)

        # 5. Return the history plus the new, enhanced user message
        print("message: ")
        print(new_user_message)
        return [SystemMessage(content=system_prompt)] + history + [new_user_message]    


    def _strip_special_tokens(self, text: str) -> str:
        """
        Finds the last assistant marker and returns only the text after it,
        effectively removing the echoed prompt.
        """
        # The marker that precedes the model's actual response
        assistant_marker = "<|start_header_id|>assistant<|end_header_id|>"
        
        # Find the last occurrence of the marker
        marker_position = text.rfind(assistant_marker)
        
        if marker_position != -1:
            # If the marker is found, take the text after it
            start_of_response = marker_position + len(assistant_marker)
            clean_text = text[start_of_response:]
        else:
            # If for some reason the marker isn't there, return the original text
            clean_text = text
            
        # Also remove the end-of-turn token if it exists
        end_token = "<|eot_id|>"
        clean_text = clean_text.replace(end_token, "")
            
        return clean_text.strip()
    
    def _load_stateless_llm(self, model_params: ModelParameters) -> ChatHuggingFace:
        """Loads a stateless HuggingFacePipeline-based model with authentication."""
        # Read the token from the environment
        hf_token = os.getenv("HF_TOKEN")
        
        hf_params = model_params["hf_params"]
        model_name = hf_params["model_name"]
        
        logging.info(f"Initializing stateless ChatHuggingFace with model '{model_name}'.")
        try:
            if model_name in GLOBAL_HF_MODEL_CACHE:
                logging.info(f"Using cached HuggingFace model for '{model_name}'.")
                loaded_model = GLOBAL_HF_MODEL_CACHE[model_name]['model']
                loaded_tokenizer = GLOBAL_HF_MODEL_CACHE[model_name]['tokenizer']
            else:
                logging.info(f"Loading HuggingFace model '{model_name}' (not in cache)...")
                device = "cuda" if torch.cuda.is_available() else "cpu"
                
                # Pass the token to the from_pretrained methods
                loaded_tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
                loaded_model = AutoModelForCausalLM.from_pretrained(
                    model_name, torch_dtype=torch.bfloat16, token=hf_token
                ).to(device)
                
                if loaded_tokenizer.pad_token is None:
                    loaded_tokenizer.pad_token = loaded_tokenizer.eos_token
                
                GLOBAL_HF_MODEL_CACHE[model_name] = {'model': loaded_model, 'tokenizer': loaded_tokenizer}
                logging.info(f"HuggingFace model '{model_name}' cached.")

            pipe = hf_pipeline(
                "text-generation", model=loaded_model, tokenizer=loaded_tokenizer,
                device=0 if torch.cuda.is_available() else -1,
                max_new_tokens=512, do_sample=True, temperature=0.6, top_p=0.9,
            )

            pipeline_llm = HuggingFacePipeline(pipeline=pipe)
            return ChatHuggingFace(llm=pipeline_llm)
        except Exception as e:
            logging.error(f"Failed to load stateless HuggingFace model '{model_name}': {e}", exc_info=True)
            raise
            
class LangChainRAG(LangChainBase):
    def __init__(self, model_params: ModelParameters, **kwargs):
        super().__init__(model_params=model_params, **kwargs)
        if model_params["model_version"] != "RAG": 
            raise ValueError("Invalid model_version for LangChainRAG.")
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        self.context_manager = ContextManager()  # instantiate once
        
    
    def _add_documents_node(self, state: ChatState) -> Dict[str, Any]:
        chat_id = state["chat_id"]
        user_id = state.get("user_id")
        files = state.get("file_contents", [])
        if not files:
            return {}

        all_docs = []
        for file_info in files:
            file_obj = file_info.get("file_obj")  # your actual uploaded file object
            mime_type = file_info.get("mime_type")

            # Parse file to text and create ContextFile
            context_file = self.context_manager.parse_and_create_context_file(
                user_id=user_id,
                chat_id=chat_id,
                file=file_obj,
                mime_type=mime_type,
                vector=None,
            )
            if context_file is None:
                continue

            saved = self.context_manager.save_context_file(user_id, context_file)
            if not saved:
                continue

            text_content = context_file.file_content.decode("utf-8")
            chunks = self.text_splitter.split_text(text_content)
            for chunk in chunks:
                all_docs.append(Document(page_content=chunk, metadata={'source': context_file.file_name}))

        if all_docs:
            get_vectorstore_for_chat(chat_id).add_documents(all_docs)

        return {}

    def _retrieve_node(self, state: ChatState) -> Dict[str, Any]:
        retriever = get_vectorstore_for_chat(state["chat_id"]).as_retriever()
        return {"context": retriever.invoke(state["messages"][-1].content)}

    def _generate_response_node(self, state: ChatState) -> Dict[str, Any]:
        """
        Generates a helpful, cited response using the retrieved context,
        and cleans the final output.
        """
        context_docs = state["context"]
        messages = state["messages"]

        context_str = "\n\n".join([
            f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}"
            for doc in context_docs
        ])

        system_prompt = f"""You are a helpful RAG assistant. Your goal is to answer the user's question based *only* on the provided context.
        
        - Be conversational and helpful.
        - If the answer is in the context, synthesize the information and provide a clear answer.
        - At the end of your answer, cite the source file(s) you used in brackets, like .
        - If the context is not sufficient to answer the question, simply say "I'm sorry, but I don't have enough information to answer that based on the provided files."

        Context from files:
        {context_str}
        """
        
        messages_for_llm = [SystemMessage(content=system_prompt)] + list(messages)
        
        response = self.llm.invoke(messages_for_llm)
        
        # --- FIX ADDED HERE ---
        # Clean the raw output using the function from the parent class
        clean_response = self._strip_special_tokens(response.content)
        
        return {"messages": [AIMessage(content=clean_response)]}

    def _should_retrieve(self, state: ChatState) -> str:
        return "retrieve" if get_vectorstore_for_chat(state["chat_id"]).index.ntotal > 1 else "base_chat"

def set_global_app(model_params: ModelParameters) -> None:
    """Builds and compiles the appropriate LangGraph app, setting it globally."""
    global _global_app, _current_model_params
    _current_model_params = model_params
    logging.info(f"Building LangGraph app with model params: {model_params}")
    
    workflow = StateGraph(ChatState)
    model_instance = LangChainRAG(model_params) if model_params.get("model_version") == "RAG" else LangChainBase(model_params)
    
    if model_params.get("model_version") == "RAG":
        workflow.add_node("add_documents", model_instance._add_documents_node)
        workflow.add_node("retrieve", model_instance._retrieve_node)
        workflow.add_node("generate_rag", model_instance._generate_response_node)
        workflow.add_node("base_chat", model_instance._call_model_node)
        workflow.set_entry_point("add_documents")
        workflow.add_conditional_edges("add_documents", model_instance._should_retrieve, {"retrieve": "retrieve", "base_chat": "base_chat"})
        workflow.add_edge("retrieve", "generate_rag")
        workflow.add_edge("generate_rag", END)
        workflow.add_edge("base_chat", END)
    else:
        workflow.add_node("call_model", model_instance._call_model_node)
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", END)
    
    if db_connection:
        checkpointer = PostgresSaver(sync_connection=db_connection)
        _global_app = workflow.compile(checkpointer=checkpointer)
        logging.info("Global app compiled and ready with PostgreSQL checkpointer.")
    else:
        logging.warning("Database connection failed. Compiling graph with persistent in-memory checkpointer.")
        memory_checkpointer = MemorySaver()
        _global_app = workflow.compile(checkpointer=memory_checkpointer)

def get_global_app() -> Any:
    """Gets the global app, initializing a default if needed."""
    global _global_app
    if _global_app is None:
        default_params: ModelParameters = {"framework_type": "LangChain", "backend": "HuggingFace", "model_version": "Base", "hf_params": {"model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "use_kv_cache": False}}
        set_global_app(default_params)
    return _global_app
