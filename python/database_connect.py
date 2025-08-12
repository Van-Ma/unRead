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
    print("✅ Successfully connected to PostgreSQL database for LangGraph checkpointer.")  # <-- added print here
except Exception as e:
    logging.error(f"Failed to connect to PostgreSQL for checkpointer: {e}")
    print(f"❌ Failed to connect to PostgreSQL: {e}")  # <-- optional print on error
    db_connection = None
