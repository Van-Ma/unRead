# vectorstore_manager.py

import logging
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

VECTORSTORES: dict[str, FAISS] = {}
EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def get_vectorstore_for_chat(chat_id: str) -> FAISS:
    if chat_id not in VECTORSTORES:
        VECTORSTORES[chat_id] = FAISS.from_texts([""], EMBEDDINGS)
    return VECTORSTORES[chat_id]

def reset_all_vector_stores():
    """Clears all RAG vector stores."""
    global VECTORSTORES
    VECTORSTORES = {}
    logging.info("All RAG vector stores have been reset.")