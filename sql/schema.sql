-- Enable UUID extension for unique IDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- USERS table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- PROJECTS table, linked to users
CREATE TABLE projects (
    project_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    project_name TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- CONTEXT_FILES table with pgvector vector column
CREATE TABLE context_files (
    file_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    file_name TEXT NOT NULL,
    file_content BYTEA,
    mime_type TEXT,
    vector vector(1536), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- CHAT_HISTORY table, linked to projects
CREATE TABLE chat_history (
    chat_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
    user_message TEXT NOT NULL,
    ai_response TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Enable Row Level Security (RLS) on tables where appropriate
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE context_files ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_history ENABLE ROW LEVEL SECURITY;

-- RLS policy on projects: user can only access own projects
CREATE POLICY user_project_access ON projects
    USING (user_id = current_setting('app.current_user_id')::UUID);

-- RLS policy on context_files: user can only access files for their projects
CREATE POLICY user_context_files_access ON context_files
    USING (project_id IN (SELECT project_id FROM projects WHERE user_id = current_setting('app.current_user_id')::UUID));

-- RLS policy on chat_history: user can only access chats for their projects
CREATE POLICY user_chat_history_access ON chat_history
    USING (project_id IN (SELECT project_id FROM projects WHERE user_id = current_setting('app.current_user_id')::UUID));
