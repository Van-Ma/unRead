"""Terminal chat client for the backend. Start `python app.py` first, then run `python chat_cli.py`.

Optional: pass a .txt file to use as context, e.g. `python chat_cli.py notes.txt`.
Commands: /new starts a new session, /quit exits.
"""
import json
import sys
import urllib.request

URL = "http://127.0.0.1:5000/chat"


def build_system_prompt(context):
    prompt = "You are a helpful assistant."
    if context:
        prompt = (
            "You must answer questions using ONLY the context provided below.\n"
            "If the answer cannot be derived at all from the context, respond with "
            '"I cannot answer based on the provided context."\n\n'
            f"Context:\n{context}"
        )
    return {"role": "system", "content": prompt}


def post(payload):
    req = urllib.request.Request(
        URL,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as res:
        return json.load(res)


def main():
    context = ""
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding="utf-8") as f:
            context = f.read()

    system = build_system_prompt(context)
    history = [system]
    print(f"Chatting via {URL}. Type /new for a new session, /quit to exit.")

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
            history = [system]
            print("(new session)")
            continue

        history.append({"role": "user", "content": text})
        try:
            data = post({"messages": history})
        except Exception as e:
            print(f"Error connecting to server: {e}")
            history.pop()
            continue

        reply = data.get("response") or "No response from model."
        print(f"AI: {reply}")
        history.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
