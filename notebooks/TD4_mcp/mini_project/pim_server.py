"""Standalone stdio MCP server exposing the PIM catalog as five discoverable tools.

Spawnable by Claude Desktop or any MCP-speaking client:
    python pim_server.py

The persistent ChromaDB index (built by build_index.py) is the source of truth for products;
taxonomy.json is the source of truth for the category tree / attribute schemas.
"""
import json
import os

import chromadb
from sentence_transformers import SentenceTransformer
from mcp.server.fastmcp import FastMCP

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "..", "..", "data")
INDEX_PATH = os.path.join(BASE_DIR, "chroma_index")
COLLECTION_NAME = "catalog"

with open(os.path.join(DATA_DIR, "taxonomy.json")) as f:
    taxonomy = json.load(f)

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.PersistentClient(path=INDEX_PATH)
try:
    collection = chroma_client.get_collection(COLLECTION_NAME)
except Exception as exc:
    raise RuntimeError(
        f"Collection '{COLLECTION_NAME}' not found in '{INDEX_PATH}'. Run `python build_index.py` first."
    ) from exc

mcp_server = FastMCP("pim")


def _parse_attributes(metadata):
    if isinstance(metadata.get("attributes"), str):
        metadata["attributes"] = json.loads(metadata["attributes"])
    return metadata


@mcp_server.tool()
def search_products(query: str, k: int = 3) -> list:
    """Semantic search over the product catalog; returns up to k products most similar to the query."""
    q_vec = embed_model.encode(query).tolist()
    res = collection.query(query_embeddings=[q_vec], n_results=k)
    return [
        {"sku": sku, **_parse_attributes(dict(meta))}
        for sku, meta in zip(res["ids"][0], res["metadatas"][0])
    ]


@mcp_server.tool()
def get_product(sku: str) -> dict:
    """Return one product's full record (document + metadata) by its SKU, or {} if not found."""
    res = collection.get(ids=[sku], include=["documents", "metadatas"])
    if not res["ids"]:
        return {}
    return {
        "sku": res["ids"][0],
        "document": res["documents"][0],
        **_parse_attributes(dict(res["metadatas"][0])),
    }


@mcp_server.tool()
def get_category_tree() -> dict:
    """Return the catalog category tree as {top_category: [leaf, ...]}."""
    return {
        cat["name"]: [sub["name"] for sub in cat["subcategories"]]
        for cat in taxonomy["categories"]
    }


@mcp_server.tool()
def get_category_attributes(category: str) -> dict:
    """Return the applicable attribute schema {attribute_name: type} for a leaf category."""
    for top in taxonomy["categories"]:
        for leaf in top["subcategories"]:
            if leaf["name"] == category:
                return {attr["name"]: attr.get("type", "unknown") for attr in leaf.get("category_attributes", [])}
    return {}


@mcp_server.tool()
def create_product(
    sku: str,
    name: str,
    brand: str,
    category: str,
    price: float,
    short_description: str,
    long_description: str,
    attributes: dict | None = None,
) -> dict:
    """Create (or replace) a product, embed it with MiniLM, and add it to the catalog so it's
    immediately searchable via search_products -- no reindexing needed."""
    doc = f"{name} — {long_description}"
    embedding = embed_model.encode(doc).tolist()
    metadata = {
        "name": name,
        "brand": brand,
        "category": category,
        "price": float(price),
        "short_description": short_description,
        "long_description": long_description,
        "attributes": json.dumps(attributes or {}),
    }
    collection.upsert(ids=[sku], embeddings=[embedding], documents=[doc], metadatas=[metadata])
    return {"sku": sku, "status": "created"}


if __name__ == "__main__":
    mcp_server.run(transport="stdio")
