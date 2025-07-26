# LangChain implementation with KV-caching and RAG support

import logging
from typing import Any, Optional, List, Dict, Sequence, Union, Tuple
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain_huggingface import HuggingFacePipeline
from langchain_huggingface.chat_models import ChatHuggingFace

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict, Annotated

from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from models.custom_huggingface_llm import CustomHuggingFaceLLM
from models.model_parameters import ModelParameters, HuggingFaceParameters
from models.model_cache import GLOBAL_HF_MODEL_CACHE

# Basic logging setup
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# LangGraph state definition
class ChatState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "add_messages"]
    file_contents: Annotated[List[Dict[str, str]], "append_file_content"]
    rag_enabled: bool

# Append file content to state
def append_file_content(current: List[Dict[str, str]], new: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if current is None:
        current = []
    return current + new



# Supported HuggingFace models
# TODO: Move to config
ALLOWED_HUGGINGFACE_MODELS = {
    "meta-llama/Llama-3.1-8B-Instruct",
    "meta-llama/Llama-3.2-1B-Instruct",
    "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
}

# Global app instances
_global_base_app = None
_global_rag_app = None

class LangChainBase:
    """Base LangChain implementation with LangGraph state management."""
    
    def __init__(self, model_params: ModelParameters, **kwargs):
        # Validate model parameters
        framework_type = model_params["framework_type"]
        backend = model_params["backend"]
        model_version = model_params["model_version"]
        hf_params = model_params.get("hf_params")

        if framework_type != "LangChain":
            raise ValueError(f"Invalid framework_type for LangChainBase: '{framework_type}'. Must be 'LangChain'.")
        if backend != "HuggingFace":
            raise ValueError(f"Invalid backend for LangChainBase: '{backend}'. Must be 'HuggingFace' for now.")
        if model_version != "Base":
            raise ValueError(f"Invalid model_version for LangChainBase: '{model_version}'. Must be 'Base'.")
        
        if not hf_params or not isinstance(hf_params, dict):
            raise ValueError("Missing or invalid 'hf_params' for HuggingFace backend in LangChainBase.")
        hf_params_typed: HuggingFaceParameters = hf_params 

        if hf_params_typed["model_name"] not in ALLOWED_HUGGINGFACE_MODELS:
            raise ValueError("Invalid model_name for LangChainBase: '{}'. Must be one of {}.".format(hf_params_typed["model_name"], list(ALLOWED_HUGGINGFACE_MODELS)))

        self.model_id = hf_params_typed["model_name"]
        self.use_kv_cache = hf_params_typed["use_kv_cache"]

        if self.use_kv_cache:
            self.llm = CustomHuggingFaceLLM(hf_params=hf_params_typed)
        else:
            logging.info("Initializing ChatHuggingFace with HuggingFacePipeline model '{}' (no explicit KV cache across invocations).".format(self.model_id))
            try:
                if self.model_id in GLOBAL_HF_MODEL_CACHE:
                    logging.info(f"Using cached HuggingFacePipeline model for '{self.model_id}'.")
                    loaded_model = GLOBAL_HF_MODEL_CACHE[self.model_id]['model']
                    loaded_tokenizer = GLOBAL_HF_MODEL_CACHE[self.model_id]['tokenizer']
                else:
                    logging.info(f"Loading HuggingFacePipeline model '{self.model_id}' (not in cache)...")
                    if torch.cuda.is_available():
                        device = torch.device("cuda")
                        logging.info("CUDA available. Loading model on GPU.")
                        to_kwargs = {"device": device}
                    else:
                        logging.info("CUDA not available. Loading model on CPU.")
                        to_kwargs = {}  # .to() call will be skipped for CPU to avoid negative index

                    loaded_tokenizer = AutoTokenizer.from_pretrained(self.model_id)
                    loaded_model = AutoModelForCausalLM.from_pretrained(
                        self.model_id, torch_dtype=torch.bfloat16
                    )
                    if to_kwargs:
                        loaded_model = loaded_model.to(**to_kwargs)
                    if loaded_tokenizer.pad_token is None:
                        loaded_tokenizer.pad_token = loaded_tokenizer.eos_token
                    
                    GLOBAL_HF_MODEL_CACHE[self.model_id] = {
                        'model': loaded_model,
                        'tokenizer': loaded_tokenizer
                    }
                    logging.info(f"HuggingFacePipeline model and tokenizer for '{self.model_id}' cached.")

                from transformers import pipeline as hf_pipeline

                gen_kwargs = dict(max_new_tokens=256, do_sample=True, temperature=0.6, top_p=0.9)
                if torch.cuda.is_available():
                    pipe = hf_pipeline(
                        "text-generation",
                        model=loaded_model,
                        tokenizer=loaded_tokenizer,
                        device=0,
                        **gen_kwargs,
                    )
                else:
                    pipe = hf_pipeline(
                        "text-generation",
                        model=loaded_model,
                        tokenizer=loaded_tokenizer,
                        **gen_kwargs,
                    )

                pipeline_llm = HuggingFacePipeline(pipeline=pipe)
                self.llm = ChatHuggingFace(llm=pipeline_llm)
            except Exception as e:
                logging.error("Failed to load HuggingFacePipeline model '{}'. This could be due to: ".format(self.model_id) +
                              "1. Invalid model name."
                              "2. Insufficient memory/GPU resources."
                              "3. Network issues preventing model download."
                              "4. Hugging Face rate limits or authentication issues (for private models)."
                              "Error details: {}".format(e))
                raise

        self.base_chat_prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful and friendly chatbot."),
            MessagesPlaceholder(variable_name="messages")
        ])

    def _call_model_node(self, state: ChatState) -> Dict[str, Any]:
        """Generate a response for the Base chat model.

        - Processes messages while preserving their order and type
        - Maintains system messages and file context
        - Uses LangGraph's MemorySaver for conversation history
        """
        # Get messages and file contents from state
        messages = state["messages"]
        file_contents = state.get("file_contents", [])
        
        # Debug logging
        logging.info(f"_call_model_node - Incoming state: messages={len(messages)}, files={len(file_contents)}")
        if file_contents:
            for i, f in enumerate(file_contents, 1):
                logging.info(f"  File {i}: {f.get('name', 'unnamed')} ({len(f.get('content', ''))} chars)")
        
        # Debug message logging
        logging.info("Incoming messages:")
        for i, msg in enumerate(messages):
            content_preview = str(msg.content)[:100] + ("..." if len(str(msg.content)) > 100 else "")
            logging.info(f"  {i+1}. {type(msg).__name__}: {content_preview}")
        
        # Keep existing message formatting
        processed_messages = list(messages)
        
        logging.info(f"Final prompt has {len(processed_messages)} messages")
        
        # Generate response
        try:
            if self.use_kv_cache:
                prompt_string = self.llm.tokenizer.apply_chat_template(
                    processed_messages, add_generation_prompt=True, tokenize=False
                )
                response_text = self.llm.invoke(prompt_string)
            else:
                response = self.llm.invoke(processed_messages)
                response_text = response.content if hasattr(response, 'content') else str(response)
            
            # Clean response
            cleaned_response = self._strip_special_tokens(response_text)
            
            # The MemorySaver will handle adding this to the conversation history
            return {
                "messages": [AIMessage(content=cleaned_response)],
                "file_contents": file_contents
            }
            
        except Exception as e:
            logging.error(f"Error in _call_model_node: {str(e)}")
            error_msg = f"I encountered an error processing your request: {str(e)}"
            return {
                "messages": [AIMessage(content=error_msg)]
            }

    @staticmethod
    def _get_file_type(filename: str):
        """Get file type from extension"""
        if not filename:
            return "unknown"
        if "." in filename:
            ext = filename.split(".")[-1].lower()
            if ext in ["py"]:
                return "python"
            elif ext in ["js", "jsx", "ts", "tsx"]:
                return "javascript"
            elif ext in ["html", "htm"]:
                return "html"
            elif ext in ["css"]:
                return "css"
            elif ext in ["json"]:
                return "json"
            elif ext in ["md"]:
                return "markdown"
            elif ext in ["txt"]:
                return "text"
            elif ext in ["csv"]:
                return "csv"
            elif ext in ["xml"]:
                return "xml"
            elif ext in ["yaml", "yml"]:
                return "yaml"
        return "text"

    def _get_file_extension(self, filename: str) -> str:
        """Get the file extension for syntax highlighting."""
        if not filename or not isinstance(filename, str):
            return ""
        
        # Get the file extension
        if "." in filename:
            ext = filename.split(".")[-1].lower()
            # File extension mapping
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
                'yml': 'yaml',
                'java': 'java',
                'c': 'c',
                'cpp': 'cpp',
                'h': 'c',
                'hpp': 'cpp',
                'go': 'go',
                'rs': 'rust',
                'rb': 'ruby',
                'php': 'php',
                'sh': 'bash',
                'bat': 'batch',
                'ps1': 'powershell',
                'sql': 'sql'
            }
            return extension_map.get(ext, '')
        return ''

    @staticmethod
    def _strip_special_tokens(text: str) -> str:
        """Clean Llama template tags"""
        import re
        # Keep content after final assistant tag if present
        if "<|assistant" in text or "assistant<|end_header_id|>" in text:
            # split on the assistant header if present and take the last part
            text = re.split(r"<\|start_header_id\|>assistant<\|end_header_id\|>", text)[-1]
        # Remove all residual <|...|> patterns
        text = re.sub(r"<\|[^>]+\|>", "", text)
        return text.strip()

class LangChainRAG(LangChainBase):
    """LangChain with RAG support using LangGraph."""

    def __init__(self, model_params: ModelParameters, **kwargs):
        super().__init__(model_params=model_params, **kwargs)

        model_version = model_params["model_version"]
        if model_version != "RAG":
            raise ValueError(f"Invalid model_version for LangChainRAG: '{model_version}'. Must be 'RAG'.")
        
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vectorstore = FAISS.from_texts([""], self.embeddings) 
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            length_function=len,
            is_separator_regex=False
        )

        # Prompt templates
        self.history_aware_retriever_prompt = ChatPromptTemplate.from_messages([
            MessagesPlaceholder(variable_name="messages"),
            ("user", "{input}"),
            ("user", "Given the conversation history and latest message, generate a search query that would help find relevant information. Focus on key entities, concepts, and the main question or topic.")
        ])
        
        self.document_chain_prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant that answers questions based on the provided context. 
            
            Context:
            {context}
            
            Sources:
            {sources_list}
            
            Guidelines:
            1. Base your response ONLY on the provided context
            2. If the context is insufficient, say you don't have enough information
            3. Be concise and to the point
            4. When relevant, cite sources using [1], [2], etc."""),
            MessagesPlaceholder(variable_name="messages"), 
            ("user", "{input}"),
        ])
        
        # Track processed files
        self.processed_files = set()

    def _add_documents_node(self, state: ChatState) -> Dict[str, Any]:
        """Process and add file contents to the vector store."""
        if not state.get("file_contents"):
            logging.info("No file contents to process in _add_documents_node")
            return {"rag_enabled": False}
            
        logging.info(f"Processing {len(state['file_contents'])} files in _add_documents_node")
        
        # Process files with metadata
        all_docs = []
        processed_files = 0
        
        for file_info in state["file_contents"]:
            name = file_info.get('name', f'unnamed_{len(self.processed_files)}')
            content = file_info.get('content', '')
            
            # Skip processed files
            if not content.strip() or name in self.processed_files:
                logging.debug(f"Skipping file (empty or already processed): {name}")
                continue
                
            logging.info(f"Processing file: {name} (size: {len(content)} chars)")
            
            try:
                # Chunk content
                chunks = self.text_splitter.split_text(content)
                
                # Create documents with metadata
                for i, chunk in enumerate(chunks):
                    doc = Document(
                        page_content=chunk,
                        metadata={
                            'source': name,
                            'chunk': i,
                            'total_chunks': len(chunks),
                            'file_type': name.split('.')[-1] if '.' in name else 'txt',
                            'chunk_size': len(chunk),
                            'timestamp': datetime.datetime.utcnow().isoformat()
                        }
                    )
                    all_docs.append(doc)
                
                processed_files += 1
                logging.info(f"Created {len(chunks)} chunks from {name}")
                
            except Exception as e:
                logging.error(f"Error processing file {name}: {str(e)}")
                continue
        
        # Update vector store
        if all_docs:
            try:
                if self.vectorstore is None:
                    self.vectorstore = FAISS.from_documents(all_docs, self.embeddings)
                    logging.info(f"Created new vector store with {len(all_docs)} chunks")
                else:
                    current_count = self.vectorstore.index.ntotal if hasattr(self.vectorstore, 'index') else 0
                    self.vectorstore.add_documents(all_docs)
                    logging.info(f"Added {len(all_docs)} chunks to vector store (total: {current_count + len(all_docs)})")
                
                return {
                    "rag_enabled": True,
                    "files_processed": processed_files,
                    "chunks_processed": len(all_docs)
                }
                
            except Exception as e:
                logging.error(f"Error updating vector store: {str(e)}")
                return {
                    "rag_enabled": False,
                    "error": f"Failed to update vector store: {str(e)}"
                }
        
        return {
            "rag_enabled": False,
            "message": "No new documents were processed"
        }

    def _route_after_adding_documents(self, state: ChatState) -> str:
        """Determine the next step after adding documents."""
        if not state.get("file_contents"):
            logging.info("No files to process, using base chat model")
            return "base_chat"
            
        # Check for new files
        new_files = [
            f for f in state["file_contents"] 
            if f.get('name') not in self.processed_files
        ]
        
        if new_files:
            logging.info(f"Processing {len(new_files)} new files")
            for file_info in new_files:
                if 'name' in file_info:
                    self.processed_files.add(file_info['name'])
            return "retrieve"
            
        logging.info("No new files to process, using base chat model")
        return "base_chat"
        
    def _route_after_generation(self, state: ChatState) -> str:
        """Determine next step after generating a response."""
        # End of generation
        return END
        
    def _route_after_base_chat(self, state: ChatState) -> str:
        """Determine next step after base chat processing."""
        # End of base chat
        return END
        
    def _route_to_rag_or_base(self, state: ChatState) -> str:
        """Backward compatibility"""
        if state.get("rag_enabled", False) and self.vectorstore.index.ntotal > 0:
            logging.info("Routing to RAG path.")
            return "retrieve"
        else:
            logging.info("Routing to base chat model path.")
            return "base_chat"

    def _retrieve_node(self, state: ChatState) -> Dict[str, Any]:
        question = state["messages"][-1].content 
        chat_history = state["messages"][:-1] 

        retriever = self.vectorstore.as_retriever()

        history_aware_retriever_chain = create_history_aware_retriever(self.llm, retriever, self.history_aware_retriever_prompt)
        
        retrieved_docs = history_aware_retriever_chain.invoke({
            "input": question,
            "messages": chat_history 
        })
        logging.info(f"Retrieved {len(retrieved_docs)} documents.")
        return {"context": retrieved_docs, "messages": state["messages"]}

    def _generate_response_node(self, state: ChatState) -> Dict[str, Any]:
        context_docs = state["context"]
        question = state["messages"][-1].content
        chat_history = state["messages"][:-1]

        # Add source info to context
        enhanced_context = []
        source_map = {}
        
        # Group by source
        for doc in context_docs:
            source = doc.metadata.get('source', 'unknown')
            if source not in source_map:
                source_map[source] = []
            source_map[source].append(doc)
        
        # Structure context
        for source, docs in source_map.items():
            file_type = docs[0].metadata.get('file_type', 'document')
            enhanced_context.append(f"## Source: {source} (Type: {file_type})")
            for doc in docs:
                enhanced_context.append(f"### Chunk {doc.metadata.get('chunk', 0) + 1} of {doc.metadata.get('total_chunks', 1)}")
                enhanced_context.append(doc.page_content)
                enhanced_context.append("\n---\n")
        
        # Build prompt
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful assistant that answers questions based on the provided context.
            The context comes from the following sources:
            {sources_list}
            
            When answering questions:
            1. Always cite your sources using the format [source: filename]
            2. If you're not sure, say so
            3. Be concise but thorough
            
            Available context:
            {context}
            """),
            MessagesPlaceholder(variable_name="messages"),
            ("user", "{input}")
        ])
        
        # Format sources
        sources_list = "\n".join([f"- {source} ({len(docs)} chunks)" for source, docs in source_map.items()])
        
        document_chain = create_stuff_documents_chain(self.llm, prompt)

        response = document_chain.invoke({
            "context": "\n".join(enhanced_context),
            "sources_list": sources_list,
            "input": question,
            "messages": chat_history
        })
        
        # Return response with history
        return {"messages": [*chat_history, AIMessage(content=response)]}

# Global app state
_global_app = None

def get_global_app() -> Any:
    """Get the global LangGraph application."""
    global _global_app
    
    if _global_app is None:
        # Default config
        model_params = {
            "framework_type": "LangChain",
            "backend": "HuggingFace",
            "model_version": "Base",
            "hf_params": {
                "model_name": "meta-llama/Llama-3.1-8B-Instruct",
                "use_kv_cache": True
            }
        }
        
        logging.info("Initializing global LangGraph application")
        llm_instance = LangChainBase(model_params=model_params)
        
        workflow = StateGraph(ChatState)
        workflow.add_node("call_model", llm_instance._call_model_node)
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", END)
        
        _global_app = workflow.compile(checkpointer=MemorySaver())
        logging.info("Global LangGraph application initialized")
    
    return _global_app

def set_global_app(model_params: ModelParameters) -> None:
    """Update the global LangGraph application with new parameters."""
    global _global_app
    
    if not model_params:
        raise ValueError("model_params cannot be None")
    
    # Reset app instance
    _global_app = None
    
    logging.info(f"Updating global app with model: {model_params}")
    llm_instance = LangChainRAG(model_params=model_params) if model_params.get("model_version") == "RAG" else LangChainBase(model_params)
    
    workflow = StateGraph(ChatState)
    
    if model_params.get("model_version") == "RAG":
        workflow.add_node("add_documents", llm_instance._add_documents_node)
        workflow.add_node("retrieve", llm_instance._retrieve_node)
        workflow.add_node("generate_response", llm_instance._generate_response_node)
        workflow.add_node("base_chat_model", llm_instance._call_model_node)
        
        workflow.set_entry_point("add_documents")
        workflow.add_conditional_edges("add_documents", llm_instance._route_after_adding_documents)
        workflow.add_edge("retrieve", "generate_response")
        workflow.add_conditional_edges("generate_response", llm_instance._route_after_generation)
        workflow.add_conditional_edges("base_chat_model", llm_instance._route_after_base_chat)
        workflow.add_conditional_edges(
            "add_documents",
            llm_instance._route_to_rag_or_base,
            {"retrieve": "retrieve", "base_chat": "base_chat_model"}
        )
    else:
        workflow.add_node("call_model", llm_instance._call_model_node)
        workflow.set_entry_point("call_model")
        workflow.add_edge("call_model", END)
    
    _global_app = workflow.compile(checkpointer=MemorySaver())
    logging.info("Global app updated with new model configuration")
# Lazy load on first API request
