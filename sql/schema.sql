-- Base extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

-- Use a dedicated schema to match app connection search_path
CREATE SCHEMA IF NOT EXISTS chats;
SET search_path TO chats;

-- USERS table
CREATE TABLE IF NOT EXISTS users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    hash_algo TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- CHATS table, directly owned by users (no projects)
CREATE TABLE IF NOT EXISTS chats (
    chat_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);

-- Note: Context file storage is handled by LangChain PGVector integration
-- which creates and manages its own tables (e.g., langchain_pg_collection, langchain_pg_embedding).
-- No separate context_files table is required.

-- Note: Conversation state/history is persisted by LangGraph Postgres checkpointer
-- in its own tables. No separate chat_history table is required here.

-- Optional: RLS can be enabled if you manage session variables for user scoping.
-- ALTER TABLE chats ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Example RLS policies (commented out by default):
-- CREATE POLICY user_chat_access ON chats
--     USING (user_id = current_setting('app.current_user_id')::UUID);

-- LangChain PGVector tables should be governed separately if you enable RLS there.

-- LangGraph checkpointer tables handle their own access; enable RLS only if you fully manage it.
