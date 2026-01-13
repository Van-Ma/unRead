import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from flask_cors import CORS
from huggingface_hub import InferenceClient

load_dotenv()

app = Flask(__name__)
CORS(app)

HF_API_TOKEN = os.getenv("HF_API_TOKEN")

client = InferenceClient(
    model="meta-llama/Meta-Llama-3-8B-Instruct",
    token=HF_API_TOKEN,
)

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])

    if not messages:
        return jsonify({"response": ""})

    # clean chat log
    print("\n=== Chat Log ===")
    seen = set()
    for i, msg in enumerate(messages, 1):
        role = msg.get("role", "unknown").upper()
        content = msg.get("content", "").strip()

        # skip duplicates
        key = f"{role}:{content}"
        if key in seen:
            continue
        seen.add(key)

        print(f"{i}. {role}: {content}")
    print("================\n")

    try:
        result = client.chat_completion(
            messages=messages,
            max_tokens=200,
            temperature=0.7,
        )
        reply = result.choices[0].message.content.strip()
        return jsonify({"response": reply})
    except Exception as e:
        return jsonify({"response": f"Error: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(port=5000, debug=True)
