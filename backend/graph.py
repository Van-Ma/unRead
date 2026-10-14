"""LangGraph chat pipeline.

    START -> route -> load_context (whole folder)  -> generate -> END
                   -> retrieve     (vector search) ->
                   -> generate     (no folder)

Conversation history is persisted per chat (thread_id) by the Postgres checkpointer.
Add new behaviour (tools, query rewriting, other modes) as nodes here.
"""
from typing import Annotated, Optional, TypedDict

from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from backend import config as settings, db, llm, rag

BASE_PROMPT = "You are a helpful assistant."

CONTEXT_PROMPT = """Answer questions using ONLY the context below. Do not invent information outside it.
You may reason and infer from the context. If the answer cannot be derived from it, respond with
"I cannot answer based on the provided context."

Context:
{context}"""

RAG_PROMPT = """Answer the question using ONLY the excerpts below.
Cite the sources you used in brackets, e.g. [report.pdf]. If the excerpts are not enough, respond with
"I cannot answer based on the provided context."

Excerpts:
{context}"""


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    folder_id: Optional[str]
    mode: str  # "context" | "rag"
    context: str
    sources: list[str]


def route(state):
    if not state.get("folder_id"):
        return "generate"
    return "retrieve" if state["mode"] == "rag" else "load_context"


def load_context(state, config):
    folder = db.get_folder(config["configurable"]["user_id"], state["folder_id"])
    parts = [f"- {s}" for s in folder["snippets"]] if folder else []
    files = db.list_files(state["folder_id"])
    parts += [f"[{f['name']}]\n{f['text']}" for f in files]
    return {"context": "\n\n".join(parts)[: settings.MAX_CONTEXT_CHARS], "sources": [f["name"] for f in files]}


def retrieve(state):
    docs = rag.search(state["folder_id"], state["messages"][-1].content)
    context = "\n\n".join(f"[{d.metadata['source']}]\n{d.page_content}" for d in docs)
    return {"context": context, "sources": sorted({d.metadata["source"] for d in docs})}


def generate(state, config):
    if not state.get("folder_id"):
        system = BASE_PROMPT
    else:
        prompt = RAG_PROMPT if state["mode"] == "rag" else CONTEXT_PROMPT
        system = prompt.format(context=state.get("context") or "(empty)")
    model = config["configurable"].get("model") or llm.current_model
    history = state["messages"][-settings.HISTORY_MESSAGES:]
    reply = llm.get(model).invoke([SystemMessage(system)] + history)
    return {"messages": [reply]}


def build(checkpointer):
    g = StateGraph(State)
    g.add_node("load_context", load_context)
    g.add_node("retrieve", retrieve)
    g.add_node("generate", generate)
    g.add_conditional_edges(START, route, ["load_context", "retrieve", "generate"])
    g.add_edge("load_context", "generate")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile(checkpointer=checkpointer)


checkpointer = PostgresSaver(db.pool)
app = None


def init():
    global app
    checkpointer.setup()
    app = build(checkpointer)


def run(chat_id, user_id, message, folder_id, mode, model=None):
    """Run one turn; returns (reply_text, sources)."""
    cfg = {"configurable": {"thread_id": chat_id, "user_id": user_id, "model": model}}
    state = app.invoke(
        {"messages": [("user", message)], "folder_id": folder_id, "mode": mode, "context": "", "sources": []},
        cfg,
    )
    return state["messages"][-1].content, state.get("sources", [])


def history(chat_id):
    state = app.get_state({"configurable": {"thread_id": chat_id}})
    msgs = state.values.get("messages", []) if state else []
    return [{"role": "user" if m.type == "human" else "assistant", "content": m.content} for m in msgs]
