"""Fnac-style catalog chatbot -- a small Flask app around the retrieve -> answer RAG loop.

Run:
    python app.py
Then open http://localhost:5000
"""
import os

from dotenv import load_dotenv
import anthropic
import chromadb
from flask import Flask, render_template, request, jsonify
from sentence_transformers import SentenceTransformer

INDEX_PATH = "./chroma_index"
COLLECTION_NAME = "catalog"
MODEL = "claude-haiku-4-5"

load_dotenv()  # reads ANTHROPIC_API_KEY from .env (project root or here)
if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found. Create a .env file with ANTHROPIC_API_KEY=sk-ant-..."
    )

client = anthropic.Anthropic()
embed_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path=INDEX_PATH)
try:
    collection = chroma_client.get_collection(COLLECTION_NAME)
except Exception as exc:
    raise RuntimeError(
        f"Collection '{COLLECTION_NAME}' not found in '{INDEX_PATH}'. Run `python build_index.py` first."
    ) from exc

app = Flask(__name__)


def retrieve(query_text, k=4):
    """Return the k catalog products most similar to `query_text`."""
    query_embedding = embed_model.encode([query_text]).tolist()
    results = collection.query(query_embeddings=query_embedding, n_results=k)
    hits = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        hits.append({
            "sku": results["ids"][0][i],
            "name": meta["name"],
            "brand": meta["brand"],
            "category": meta["category"],
            "price": meta["price"],
            "short_description": meta["short_description"],
            "long_description": meta["long_description"],
            "attributes": meta["attributes"],
        })
    return hits


def answer_question(question, k=4):
    """Answer a question about the catalog, grounded in the k most relevant products."""
    hits = retrieve(question, k=k)
    context = "\n".join(
        f"- {h['name']} ({h['category']}): {h['short_description']}" for h in hits
    )
    prompt = (
        "Answer the question using ONLY the catalog products listed below. If nothing fits, say so.\n\n"
        f"Catalog products:\n{context}\n\nQuestion: {question}"
    )
    resp = client.messages.create(
        model=MODEL, max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text, hits


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.get_json(silent=True) or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    answer, hits = answer_question(question)
    return jsonify({
        "answer": answer,
        "products": [{"name": h["name"], "category": h["category"]} for h in hits],
    })


if __name__ == "__main__":
    app.run(debug=True)
