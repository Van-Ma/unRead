# vectorstore_manager.py

import logging
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

VECTORSTORES: dict[str, FAISS] = {}
EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def reset_vectorstore_for_chat(chat_id: str):
    """Clears the RAG vector store for a specific chat."""
    if chat_id in VECTORSTORES:
        del VECTORSTORES[chat_id]
        logging.info(f"Vector store for chat_id {chat_id} has been reset.")

def get_vectorstore_for_chat(chat_id: str) -> FAISS:
    if chat_id not in VECTORSTORES:
        VECTORSTORES[chat_id] = FAISS.from_texts([""], EMBEDDINGS)
    return VECTORSTORES[chat_id]

def reset_all_vector_stores():
    """Clears all RAG vector stores."""
    global VECTORSTORES
    VECTORSTORES = {}
    logging.info("All RAG vector stores have been reset.")