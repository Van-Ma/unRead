from context_manager import ContextManager
from langchain.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings

_vectorstore_cache = {}
embedding_model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def get_vectorstore_for_chat(chat_id: str) -> PGVector:
    if chat_id in _vectorstore_cache:
        return _vectorstore_cache[chat_id]

    context_manager = ContextManager()
    conn = context_manager.db  # your persistent psycopg connection

    vectorstore = PGVector(
        connection=conn,
        embedding_function=embedding_model.embed_query,
        collection_name="context_files",
        vector_column_name="vector",
        id_column_name="file_id",
        content_column_name="file_content",
    )

    _vectorstore_cache[chat_id] = vectorstore
    return vectorstore