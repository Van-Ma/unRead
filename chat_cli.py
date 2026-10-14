"""Terminal chat client for the backend. Start `python app.py` first.

    python chat_cli.py                       plain chat
    python chat_cli.py notes.pdf a.txt       answer only from these files (sent in full)
    python chat_cli.py notes.pdf --rag       answer from retrieved passages, with citations
    python chat_cli.py --model qwen2.5:3b    use a specific model

Commands: /new starts a new chat, /quit exits.
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request

URL = "http://127.0.0.1:5000"


def call(method, path, body=None):
    req = urllib.request.Request(
        URL + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise RuntimeError(json.load(e).get("error", e.reason)) from None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs="*")
    parser.add_argument("--rag", action="store_true")
    parser.add_argument("--model")
    args = parser.parse_args()

    folder_id = None
    if args.files:
        folder_id = f"cli-{int(time.time())}"
        call("PUT", f"/folders/{folder_id}", {"name": "CLI", "snippets": []})
        for path in args.files:
            call("POST", f"/folders/{folder_id}/files", {"path": os.path.abspath(path)})

    mode = "rag" if args.rag else "context"
    chat_id = None
    print(f"Chatting via {URL} ({mode} mode). Type /new for a new chat, /quit to exit.")
    try:
        while True:
            try:
                text = input("\nYou: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not text:
                continue
            if text == "/quit":
                break
            if text == "/new":
                chat_id = None
                print("(new chat)")
                continue
            try:
                data = call("POST", "/chat", {
                    "chat_id": chat_id, "folder_id": folder_id, "message": text, "mode": mode, "model": args.model,
                })
            except Exception as e:
                print(f"Error: {e}")
                continue
            chat_id = data["chat_id"]
            print(f"AI: {data['response']}")
            if data["sources"]:
                print(f"    sources: {', '.join(data['sources'])}")
    finally:
        if folder_id:
            call("DELETE", f"/folders/{folder_id}")


if __name__ == "__main__":
    main()
