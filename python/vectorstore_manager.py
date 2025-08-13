from typing import Dict
from database import db_connection
from langchain_community.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings

_vectorstore_cache: Dict[str, PGVector] = {}
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def _collection_name_for_chat(chat_id: str) -> str:
    return f"context_files_{chat_id}"

def get_vectorstore_for_chat(chat_id: str) -> PGVector:
    if chat_id in _vectorstore_cache:
        return _vectorstore_cache[chat_id]
    vectorstore = PGVector(
        connection=db_connection,
        embedding_function=embedding_model,
        collection_name=_collection_name_for_chat(chat_id),
    )
    _vectorstore_cache[chat_id] = vectorstore
    return vectorstore

def reset_vectorstore_for_chat(chat_id: str) -> None:
    if chat_id in _vectorstore_cache:
        _vectorstore_cache.pop(chat_id, None)
    # Note: leaving persisted embeddings as-is; they are isolated by collection name

def reset_all_vector_stores() -> None:
    _vectorstore_cache.clear()
