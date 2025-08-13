import os
import logging
import psycopg


# --- Database Connection ---
db_connection = None
try:
    PG_URI = os.getenv("LANGGRAPH_PG_CHECKPOINT_URI")
    if PG_URI is None:
        raise RuntimeError("LANGGRAPH_PG_CHECKPOINT_URI must be set in your .env file!")
    conn_string = PG_URI + "?options=-csearch_path%3Dchats"
    db_connection = psycopg.connect(conn_string)
    logging.info("Successfully created persistent PostgreSQL connection for LangGraph checkpointer.")
except Exception as e:
    logging.error(f"Failed to connect to PostgreSQL for checkpointer: {e}")
    db_connection = None


def user_owns_chat(user_id: str, chat_id: str) -> bool:
    """Return True if the chat belongs to the given user, False otherwise."""
    try:
        if not db_connection:
            return False
        with db_connection.cursor() as cur:
            cur.execute("SELECT 1 FROM chats WHERE chat_id = %s AND user_id = %s", (chat_id, user_id))
            return cur.fetchone() is not None
    except Exception:
        return False

