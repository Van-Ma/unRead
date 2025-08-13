import os
import logging
import psycopg

PG_URI = os.getenv("LANGGRAPH_PG_CHECKPOINT_URI")
if PG_URI is None:
    raise RuntimeError("LANGGRAPH_PG_CHECKPOINT_URI must be set in your .env file!")

try:
    with psycopg.connect(PG_URI) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            if cur.fetchone() == (1,):
                print("✅ Successfully connected to PostgreSQL!")
            else:
                print("⚠️ Connected but unexpected query result.")
except Exception as e:
    print(f"❌ Failed to connect to PostgreSQL: {e}")
