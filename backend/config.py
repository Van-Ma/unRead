import asyncio
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# psycopg's async driver (used by langchain-postgres) can't run on the default Windows event loop
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://unread:unread@localhost:5432/unread")

# any OpenAI-compatible server: Ollama (default), HuggingFace router, vLLM, OpenAI...
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("HF_API_TOKEN") or "unused"
LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2:1b")

EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
MAX_CONTEXT_CHARS = 12000  # "context" mode sends the whole folder up to this size
HISTORY_MESSAGES = 20

SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
