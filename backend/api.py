import os
import uuid

from flask import Blueprint, abort, jsonify, request

from backend import db, graph, llm, rag
from backend.auth import current_user_id

bp = Blueprint("api", __name__)


def owned_folder(folder_id):
    folder = db.get_folder(current_user_id(), folder_id)
    if not folder:
        abort(404, "Folder not found")
    return folder


@bp.get("/health")
def health():
    return jsonify(ok=True)


# --- models ---

@bp.get("/models")
def models():
    try:
        available = llm.list_models()
    except Exception:
        available = []
    return jsonify(models=available, current=llm.current_model)


@bp.post("/models")
def set_model():
    llm.set_model(request.json["model"])
    return jsonify(current=llm.current_model)


# --- folders: highlighted snippets + attached files, indexed for RAG ---

@bp.get("/folders")
def list_folders():
    return jsonify(db.list_folders(current_user_id()))


@bp.put("/folders/<folder_id>")
def save_folder(folder_id):
    body = request.json
    old = db.get_folder(current_user_id(), folder_id)
    snippets = body.get("snippets", [])
    db.upsert_folder(current_user_id(), folder_id, body.get("name") or "New", snippets, body.get("filePath"))
    if not old or old["snippets"] != snippets:
        rag.index(folder_id, rag.SNIPPETS, snippets)
    return jsonify(ok=True)


@bp.delete("/folders/<folder_id>")
def delete_folder(folder_id):
    owned_folder(folder_id)
    rag.unindex(folder_id)
    db.delete_folder(current_user_id(), folder_id)
    return jsonify(ok=True)


@bp.get("/folders/<folder_id>/files")
def list_files(folder_id):
    owned_folder(folder_id)
    return jsonify([{"path": f["path"], "name": f["name"]} for f in db.list_files(folder_id)])


@bp.post("/folders/<folder_id>/files")
def attach_file(folder_id):
    owned_folder(folder_id)
    path = request.json["path"]
    name = os.path.basename(path)
    text = rag.parse_file(path)
    db.upsert_file(folder_id, path, name, text)
    rag.index(folder_id, name, [text])
    return jsonify(path=path, name=name, chars=len(text)), 201


@bp.delete("/folders/<folder_id>/files")
def detach_file(folder_id):
    owned_folder(folder_id)
    path = request.args["path"]
    rag.unindex(folder_id, os.path.basename(path))
    db.delete_file(folder_id, path)
    return jsonify(ok=True)


@bp.post("/parse")
def parse():
    return jsonify(text=rag.parse_file(request.json["path"]))


# --- chat ---

@bp.post("/chat")
def chat():
    body = request.json
    message = (body.get("message") or "").strip()
    if not message:
        abort(400, "message is required")
    folder_id = body.get("folder_id")
    folder_id = str(folder_id) if folder_id is not None else None
    if folder_id:
        owned_folder(folder_id)

    chat_id = body.get("chat_id")
    if chat_id:
        if not db.get_chat(current_user_id(), chat_id):
            abort(404, "Chat not found")
    else:
        chat_id = str(uuid.uuid4())
        db.create_chat(current_user_id(), chat_id, folder_id, message[:60])

    reply, sources = graph.run(
        chat_id, current_user_id(), message, folder_id, body.get("mode", "context"), body.get("model")
    )
    return jsonify(chat_id=chat_id, response=reply, sources=sources)


@bp.get("/chats")
def list_chats():
    return jsonify([dict(c, messages=graph.history(c["id"])) for c in db.list_chats(current_user_id())])


@bp.delete("/chats/<chat_id>")
def delete_chat(chat_id):
    if not db.get_chat(current_user_id(), chat_id):
        abort(404, "Chat not found")
    graph.checkpointer.delete_thread(chat_id)
    db.delete_chat(current_user_id(), chat_id)
    return jsonify(ok=True)
