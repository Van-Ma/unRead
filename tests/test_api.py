"""API tests. Needs the database running (docker compose up -d); the LLM is replaced by an echo stub."""
import uuid

import pytest
from langchain_core.messages import AIMessage

from app import create_app
from backend import llm


class EchoLLM:
    """Replies with the system prompt and the number of messages it was given."""

    def invoke(self, messages):
        return AIMessage(content=f"{messages[0].content}\n#messages={len(messages)}")


created_chats = []


@pytest.fixture(scope="module")
def client():
    llm.get = lambda model: EchoLLM()
    client = create_app().test_client()
    yield client
    for chat_id in created_chats:
        client.delete(f"/chats/{chat_id}")


@pytest.fixture
def folder(client):
    folder_id = f"test-{uuid.uuid4()}"
    client.put(f"/folders/{folder_id}", json={"name": "Cats", "snippets": ["The office cat is named Pickles."]})
    yield folder_id
    client.delete(f"/folders/{folder_id}")


def chat(client, **body):
    res = client.post("/chat", json=body)
    assert res.status_code == 200, res.json
    created_chats.append(res.json["chat_id"])
    return res.json


def test_plain_chat_keeps_history(client):
    first = chat(client, message="hi")
    assert "helpful assistant" in first["response"]
    second = chat(client, message="again", chat_id=first["chat_id"])
    assert "#messages=4" in second["response"]  # system + user + assistant + user

    chats = {c["id"]: c for c in client.get("/chats").json}
    assert [m["role"] for m in chats[first["chat_id"]]["messages"]] == ["user", "assistant", "user", "assistant"]


def test_context_mode_sends_snippets_and_files(client, folder, tmp_path):
    doc = tmp_path / "notes.txt"
    doc.write_text("Pickles sleeps on the printer.")
    assert client.post(f"/folders/{folder}/files", json={"path": str(doc)}).status_code == 201

    res = chat(client, message="Where does the cat sleep?", folder_id=folder, mode="context")
    assert "Pickles." in res["response"] and "sleeps on the printer" in res["response"]
    assert res["sources"] == ["notes.txt"]


def test_rag_mode_retrieves_relevant_chunks(client, folder, tmp_path):
    doc = tmp_path / "space.txt"
    doc.write_text("The Apollo 11 mission landed on the Moon in 1969.")
    client.post(f"/folders/{folder}/files", json={"path": str(doc)})

    res = chat(client, message="When did Apollo 11 land?", folder_id=folder, mode="rag")
    assert "[space.txt]" in res["response"] and "1969" in res["response"]
    assert "space.txt" in res["sources"]

    client.delete(f"/folders/{folder}/files", query_string={"path": str(doc)})
    res = chat(client, message="When did Apollo 11 land?", folder_id=folder, mode="rag")
    assert "1969" not in res["response"]


def test_folder_snippet_changes_are_reindexed(client, folder):
    client.put(f"/folders/{folder}", json={"name": "Cats", "snippets": ["Pickles is orange."]})
    res = chat(client, message="What color is Pickles?", folder_id=folder, mode="rag")
    assert "orange" in res["response"] and "named Pickles" not in res["response"]


def test_folders_are_scoped_and_validated(client):
    assert client.post("/chat", json={"message": "x", "folder_id": "missing"}).status_code == 404
    assert client.post("/chat", json={"message": ""}).status_code == 400
    assert client.post("/parse", json={"path": "file.exe"}).status_code == 400
