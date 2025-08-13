import logging
import os
import torch
from typing import Any, List, Dict, Sequence

# --- Third-party imports ---
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline as hf_pipeline
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_huggingface import HuggingFacePipeline
from langchain_huggingface.chat_models import ChatHuggingFace
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict, Annotated

# --- Local application imports ---
from models.model_parameters import ModelParameters
from models.kv_cache_hf_model import KVCacheHFModel
from models.model_cache import GLOBAL_HF_MODEL_CACHE
from database import PG_URI
from vectorstore_manager import get_vectorstore_for_chat
from file_manager import parse_file_to_text


class ChatState(TypedDict):
	messages: Annotated[Sequence[BaseMessage], lambda x, y: x + y]
	file_contents: List[Dict[str, Any]]
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
		"""
		Prepares messages for the LLM. If files are present, their content is
		injected directly into the latest user message to ensure the model sees it.
		"""
		messages = state["messages"]
		file_contents = state.get("file_contents", [])

		system_prompt = "You are a helpful AI assistant."
		if not file_contents:
			return [SystemMessage(content=system_prompt)] + list(messages)

		file_context_str = "\n\n--- Start of Provided File Content ---\n"
		for file_info in file_contents:
			content = file_info.get('content') if isinstance(file_info, dict) else None
			name = file_info.get('name') if isinstance(file_info, dict) else None
			if content and str(content).strip():
				file_context_str += f"\n[File: {name}]\n{str(content)[:2000]}\n"
		file_context_str += "--- End of Provided File Content ---\n"

		history = list(messages)
		last_user_message = history.pop()
		new_content = (
			f"Based on the following content, please answer my question.\n"
			f"{file_context_str}\n"
			f"My Question: \"{last_user_message.content}\""
		)
		new_user_message = HumanMessage(content=new_content)
		return [SystemMessage(content=system_prompt)] + history + [new_user_message]

	def _strip_special_tokens(self, text: str) -> str:
		assistant_marker = "<|start_header_id|>assistant<|end_header_id|>"
		marker_position = text.rfind(assistant_marker)
		if marker_position != -1:
			start_of_response = marker_position + len(assistant_marker)
			clean_text = text[start_of_response:]
		else:
			clean_text = text
		end_token = "<|eot_id|>"
		clean_text = clean_text.replace(end_token, "")
		return clean_text.strip()

	def _load_stateless_llm(self, model_params: ModelParameters) -> ChatHuggingFace:
		"""Loads a stateless HuggingFacePipeline-based model with authentication."""
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
		# Align with standard approach
		self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=250, chunk_overlap=50)

	def _add_documents_node(self, state: ChatState) -> Dict[str, Any]:
		from file_manager import ingest_files  # local import to avoid cycles
		chat_id = state["chat_id"]
		files = state.get("file_contents", [])
		if not files:
			return {}
		files_to_ingest: List[Any] = []
		for file_info in files:
			if hasattr(file_info, 'save') or hasattr(file_info, 'read'):
				files_to_ingest.append(file_info)
			elif isinstance(file_info, dict):
				f = file_info.get("file_obj") or file_info.get("file")
				if f is not None:
					files_to_ingest.append(f)
		if files_to_ingest:
			ingest_files(chat_id, files_to_ingest)
		return {}

	def _retrieve_node(self, state: ChatState) -> Dict[str, Any]:
		retriever = get_vectorstore_for_chat(state["chat_id"]).as_retriever()
		return {"context": retriever.invoke(state["messages"][-1].content)}

	def _generate_response_node(self, state: ChatState) -> Dict[str, Any]:
		context_docs = state["context"]
		messages = state["messages"]
		context_str = "\n\n".join([
			f"Source: {doc.metadata.get('source', 'Unknown')}\nContent: {doc.page_content}"
			for doc in context_docs
		])
		system_prompt = f"""You are a helpful RAG assistant. Your goal is to answer the user's question based *only* on the provided context.
		
		- Be conversational and helpful.
		- If the answer is in the context, synthesize the information and provide a clear answer.
		- At the end of your answer, cite the source file(s) you used in brackets, like [].
		- If the context is not sufficient to answer the question, simply say "I'm sorry, but I don't have enough information to answer that based on the provided files."

		Context from files:
		{context_str}
		"""
		messages_for_llm = [SystemMessage(content=system_prompt)] + list(messages)
		response = self.llm.invoke(messages_for_llm)
		clean_response = self._strip_special_tokens(response.content)
		return {"messages": [AIMessage(content=clean_response)]}

	def _should_retrieve(self, state: ChatState) -> str:
		# Default to retrieving; retriever will return empty context if no docs
		return "retrieve"


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
        workflow.add_conditional_edges(
            "add_documents",
            model_instance._should_retrieve,
            {"retrieve": "retrieve", "base_chat": "base_chat"},
        )
        workflow.add_edge("retrieve", "generate_rag")
        workflow.add_edge("generate_rag", END)
        workflow.add_edge("base_chat", END)
    else:
        workflow.add_node("call_model", model_instance._call_model_node)
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", END)

    if PG_URI:
        checkpointer = PostgresSaver(PG_URI)
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
		default_params: ModelParameters = {
			"framework_type": "LangChain",
			"backend": "HuggingFace",
			"model_version": "Base",
			"hf_params": {"model_name": "TinyLlama/TinyLlama-1.1B-Chat-v1.0", "use_kv_cache": False},
		}
		set_global_app(default_params)
	return _global_app

