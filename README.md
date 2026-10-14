# unRead
A desktop AI chatbot that handles your data and answers the way *you* want.

Take control of every step of your chat: context, model, and answers.

- **Macro & micro context control:** Choose files, highlight specific sentences, and organize work into folders.
- **Context editing:** Remove context you no longer want, and it's gone from the very next answer. No looping AI chats!
- **Local by default:** Models run locally through Ollama, so your chats never leave your machine. No tracking. Cloud models are optional.
- **Extensible:** LangGraph backend. Easily integrate into other components and workflows.

We're extending features such as RAG, the vector store, OAuth, and more.

![upload, highlight text, and create context groups](contextManager/public/workspace/demo1.png)
![chat with user selected context](contextManager/public/workspace/demo2.png)

## Setup (once)
Install [Node.js 20+](https://nodejs.org), [Python 3.10+](https://python.org), [Docker Desktop](https://www.docker.com/products/docker-desktop/) and [Ollama](https://ollama.com), then from the repo root:
```bash
ollama pull llama3.2:1b
pip install -r requirements.txt
cd contextManager && npm install
```

## Run
With Docker Desktop open, run each in its own terminal from the repo root:
```bash
docker compose up -d                      # database
python app.py                             # backend
cd contextManager && npm run dev          # frontend
cd contextManager && npm run electron     # desktop window
```

Chat in the terminal instead of the GUI (backend must be running):
```bash
python chat_cli.py                    # plain chat
python chat_cli.py notes.pdf --rag    # chat with a file
```

Run tests: `pytest tests`

**Troubleshooting (Windows)**
- `npm` blocked by execution policy: use `npm.cmd`.
- Electron error `does not provide an export named 'BrowserWindow'`: run `Remove-Item Env:ELECTRON_RUN_AS_NODE` first (VS Code terminals set it).

## Configuration
Optional: copy `.env.example` to `.env`. It switches the model provider (e.g. HuggingFace instead of Ollama), the database URL, and Google login credentials.

## Features
- Highlight text in .txt, .docx, .pdf and .xlsx files and save snippets into context folders
- Attach whole files to a folder
- **Context** mode sends the whole folder to the model; **RAG** mode retrieves only relevant passages and cites sources
- Folders, files and chat history saved in PostgreSQL (pgvector for embeddings)
- Switch models at runtime (Ollama or any OpenAI-compatible API)
- Chat log of past sessions
- Google login skeleton (`backend/auth.py`)

**Stack:** React, Vite, Electron, Flask, LangChain, LangGraph, PostgreSQL + pgvector, fastembed, Ollama

**Code:** `backend/graph.py` (LangGraph pipeline), `backend/rag.py` (parsing, embeddings, vector store), `backend/api.py` (HTTP routes), `sql/schema.sql` (tables).

## Planned
- Finish auth: login screen, token auth for the desktop/CLI clients, per-user data
- More LangGraph nodes: query rewriting, tool use, web search
- Streaming responses
- Containerize the backend and run multiple instances behind a load balancer
