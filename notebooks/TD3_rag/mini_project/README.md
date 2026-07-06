# Fnac Catalog Assistant (mini-project)

A small Flask app: type a question about the catalog, get a grounded answer via
the `retrieve -> answer` RAG loop from TD3 §7, backed by a persistent ChromaDB index.

## Setup

```bash
pip install -r requirements.txt
```

Make sure `ANTHROPIC_API_KEY` is set in a `.env` file (this folder or the project root).

## Run

1. Build the persistent index (once, or whenever `products.csv` changes):

   ```bash
   python build_index.py
   ```

   This embeds `../../data/products.csv` with MiniLM (`all-MiniLM-L6-v2`) and writes
   a persistent ChromaDB index to `./chroma_index`.

2. Start the app:

   ```bash
   python app.py
   ```

3. Open http://localhost:5000 and ask a question, e.g.
   *"do you have noise-cancelling headphones under 200 euros?"*

## Notes

- Uses Haiku only (`claude-haiku-4-5`).
- The index is persistent -- restarting the app does not re-embed the catalog.
- `POST /api/ask` (JSON `{"question": "..."}`) is also available directly.
