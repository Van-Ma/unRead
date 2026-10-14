from pathlib import Path

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import ConnectionPool

from backend import config

# shared by the app queries and the LangGraph checkpointer (which requires autocommit + dict rows)
pool = ConnectionPool(
    config.DATABASE_URL,
    kwargs={"autocommit": True, "row_factory": dict_row},
    open=False,
)


def init():
    pool.open(wait=True, timeout=10)
    schema = (Path(__file__).parent.parent / "sql" / "schema.sql").read_text()
    with pool.connection() as conn:
        conn.execute(schema)


def query(sql, params=None):
    with pool.connection() as conn:
        return conn.execute(sql, params).fetchall()


def execute(sql, params=None):
    with pool.connection() as conn:
        conn.execute(sql, params)


# --- users ---

def upsert_user(user_id, email, name):
    execute(
        "INSERT INTO users (id, email, name) VALUES (%s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, name = EXCLUDED.name",
        (user_id, email, name),
    )


def get_user(user_id):
    rows = query("SELECT id, email, name FROM users WHERE id = %s", (user_id,))
    return rows[0] if rows else None


# --- folders ---

def list_folders(user_id):
    return query(
        'SELECT id, name, snippets, file_path AS "filePath" FROM folders WHERE user_id = %s ORDER BY created_at',
        (user_id,),
    )


def get_folder(user_id, folder_id):
    rows = query(
        'SELECT id, name, snippets, file_path AS "filePath" FROM folders WHERE id = %s AND user_id = %s',
        (folder_id, user_id),
    )
    return rows[0] if rows else None


def upsert_folder(user_id, folder_id, name, snippets, file_path):
    execute(
        "INSERT INTO folders (id, user_id, name, snippets, file_path) VALUES (%s, %s, %s, %s, %s) "
        "ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name, snippets = EXCLUDED.snippets, file_path = EXCLUDED.file_path "
        "WHERE folders.user_id = EXCLUDED.user_id",
        (folder_id, user_id, name, Jsonb(snippets), file_path),
    )


def delete_folder(user_id, folder_id):
    execute("DELETE FROM folders WHERE id = %s AND user_id = %s", (folder_id, user_id))


# --- files attached to folders ---

def list_files(folder_id):
    return query("SELECT path, name, text FROM files WHERE folder_id = %s ORDER BY created_at", (folder_id,))


def upsert_file(folder_id, path, name, text):
    execute(
        "INSERT INTO files (folder_id, path, name, text) VALUES (%s, %s, %s, %s) "
        "ON CONFLICT (folder_id, path) DO UPDATE SET text = EXCLUDED.text",
        (folder_id, path, name, text),
    )


def delete_file(folder_id, path):
    execute("DELETE FROM files WHERE folder_id = %s AND path = %s", (folder_id, path))


# --- chats (messages are stored by the LangGraph checkpointer) ---

def list_chats(user_id):
    return query(
        "SELECT c.id, c.folder_id, f.name AS folder_name, c.title, c.created_at "
        "FROM chats c LEFT JOIN folders f ON f.id = c.folder_id WHERE c.user_id = %s ORDER BY c.created_at",
        (user_id,),
    )


def get_chat(user_id, chat_id):
    rows = query("SELECT id, folder_id, title FROM chats WHERE id = %s AND user_id = %s", (chat_id, user_id))
    return rows[0] if rows else None


def create_chat(user_id, chat_id, folder_id, title):
    execute(
        "INSERT INTO chats (id, user_id, folder_id, title) VALUES (%s, %s, %s, %s)",
        (chat_id, user_id, folder_id, title),
    )


def delete_chat(user_id, chat_id):
    execute("DELETE FROM chats WHERE id = %s AND user_id = %s", (chat_id, user_id))
