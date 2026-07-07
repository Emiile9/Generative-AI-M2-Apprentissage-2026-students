# PIM Copilot (mini-project)

A small chat web-app for a Fnac catalog manager: paste a messy supplier blurb and watch the
agent categorize it, write an on-brand entry, fill every attribute (`null` where unknown), route
leftovers to `extra`, and add it to the catalog — visible instantly, no reindex.

- **Backend** (`app/main.py`) — FastAPI, one `POST /chat` endpoint. Runs the TD5 **reason → act →
  observe** agent loop (Haiku + the `add_product` skill). It never re-implements the PIM tools —
  it spawns the **TD4 mini-project's `pim_server.py`** as a subprocess and talks MCP to it over
  stdio (the same launch line you registered in `claude_desktop_config.json` for TD4).
- **Frontend** (`web/`) — a small Vue 3 chat UI (no build step) that shows each tool call
  (`🔧 tool_name(args)`, with the raw result foldable) alongside the conversation.
- **PIM visualizer** — reuse `notebooks/pim-prod/` as-is (not part of this folder); point it at the
  same `chroma_index` to watch products the copilot creates show up there.

## Setup

```bash
cd notebooks/TD5_agent/mini_project
pip install -r requirements.txt
```

Requires `ANTHROPIC_API_KEY` in a `.env` file (project root or here) and a **built TD4 index**:

```bash
cd ../../TD4_mcp/mini_project
python build_index.py   # only if you haven't already, or products.csv changed
```

## Run

```bash
cd notebooks/TD5_agent/mini_project
uvicorn app.main:app --reload --app-dir .
```

Open **http://localhost:8000**. On startup the backend spawns
`../../TD4_mcp/mini_project/pim_server.py` and connects to it over stdio — check the terminal log
for `Connected to TD4 pim_server; tools: [...]`.

Try:
- *"What noise-cancelling headphones do we carry under €300?"* → `search_products`.
- Paste a supplier blurb, e.g.:
  > Aurora X: flagship ANC over-ear headphones, 40h battery, USB-C fast charge, Bluetooth 5.3,
  > fold flat, midnight black or sand. Wholesale €149, suggested retail €249. 12-month warranty,
  > MOQ 50, ships week 28 from Lyon.

  → the agent walks its `add_product` skill: picks the leaf category, fetches its attribute
  schema, searches similar products for the house voice, writes the entry, fills every attribute
  (`null` if the blurb is silent), routes the wholesale price / warranty / MOQ / ship week /
  warehouse into `extra`, and calls `create_product` with the **retail** price.

Click **New chat** to clear the conversation.

## See it land in the PIM

In another terminal:

```bash
cd notebooks/pim-prod
pip install -r app/requirements.txt
PIM_INDEX_DIR=../TD4_mcp/mini_project/chroma_index uvicorn app.main:app --reload --app-dir . --port 8001
```

Open http://localhost:8001 (a different port from the copilot's 8000) — the product you just
added via the copilot is there, with its completeness and `extra` payload.

## Notes

- No API key in the code — loaded from `.env`.
- The backend keeps one server-side conversation (a single-user demo); **New chat** resets it.
- `POST /chat` returns `{"reply": "...", "trace": [{"tool", "input", "output"}, ...]}` — the trace
  is only the tool calls made during that turn, which is what the UI renders as `🔧` blocks.
