"""Build a persistent ChromaDB index of the product catalog -- the PIM server's source of truth.

Run once (and again whenever products.csv changes):
    python build_index.py
"""
import os

import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "..", "..", "data", "products.csv")
INDEX_PATH = os.path.join(BASE_DIR, "chroma_index")
COLLECTION_NAME = "catalog"


def main():
    df = pd.read_csv(CSV_PATH)
    df["doc"] = df["name"] + " — " + df["long_description"]

    print(f"Loaded {len(df)} products from {CSV_PATH}.")

    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = embed_model.encode(df["doc"].tolist()).tolist()

    metadatas = [
        {
            "name": r["name"],
            "brand": r["brand"],
            "category": r["category"],
            "price": float(r["price"]),
            "short_description": r["short_description"],
            "long_description": r["long_description"],
            "attributes": r["attributes"],  # JSON string -> Chroma metadata must be scalar
        }
        for _, r in df.iterrows()
    ]

    chroma_client = chromadb.PersistentClient(path=INDEX_PATH)
    if COLLECTION_NAME in [c.name for c in chroma_client.list_collections()]:
        chroma_client.delete_collection(COLLECTION_NAME)
    collection = chroma_client.create_collection(COLLECTION_NAME)

    collection.add(
        ids=df["sku"].tolist(),
        embeddings=embeddings,
        documents=df["doc"].tolist(),
        metadatas=metadatas,
    )

    print(f"Indexed {collection.count()} products into '{INDEX_PATH}' (collection '{COLLECTION_NAME}').")


if __name__ == "__main__":
    main()
