# PIM MCP server (mini-project)

A standalone **stdio** MCP server exposing the product catalog as five discoverable tools:
`search_products`, `get_product`, `get_category_tree`, `get_category_attributes`, `create_product`.
The persistent ChromaDB index is the source of truth for products; `taxonomy.json` is the source
of truth for categories.

## Setup

```bash
pip install -r requirements.txt
```

No API key needed -- Claude Desktop (or any MCP client) brings its own model.

## 1. Build the index (once, or whenever products.csv changes)

```bash
python build_index.py
```

Embeds `../../data/products.csv` with MiniLM (`all-MiniLM-L6-v2`) and writes a persistent
ChromaDB index to `./chroma_index`.

## 2. Sanity-check the server out-of-process

```bash
python client_demo.py
```

Spawns `pim_server.py` as a subprocess over stdio and exercises all five tools, including the
freshness demo (`create_product` then `search_products` finds it immediately).

## 3. Connect it to Claude Desktop

1. Install [Claude Desktop](https://claude.ai/download), open it, sign in.
2. **Settings → Developer → Edit Config** to open `claude_desktop_config.json`
   (macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`).
3. Register the server (both paths must be absolute -- these are this project's actual paths):

```json
{
  "mcpServers": {
    "pim": {
      "command": "/Users/emile/Desktop/IASD/TP_M2/IA_agentic/Generative-AI-M2-Apprentissage-2026-students/.agentic/bin/python",
      "args": ["/Users/emile/Desktop/IASD/TP_M2/IA_agentic/Generative-AI-M2-Apprentissage-2026-students/notebooks/TD4_mcp/mini_project/pim_server.py"]
    }
  }
}
```

4. **Fully quit Claude Desktop** (⌘Q, not just close the window) and reopen it -- MCP servers are
   only read at startup.
5. In a new chat, open the 🛠️ tools menu and confirm the **`pim`** server lists all five tools.
6. Try asking:
   - *"What noise-cancelling headphones do we carry under €300?"* → calls `search_products`.
   - *"What top-level categories do we have?"* → calls `get_category_tree`.
   - *"What attributes apply to Headphones?"* → calls `get_category_attributes`.
   - *"Add a new product: AquaBeat Pro, a $79 waterproof floating Bluetooth speaker with a
     20-hour battery, category Bluetooth Speakers -- then find it."* → calls `create_product`,
     then `search_products`, and the new item comes back immediately (no reindexing).

## Notes

- `create_product` embeds with the same MiniLM model used to build the index, so new products
  share the one vector space and are searchable the instant they're added.
- `create_product` upserts by `sku` -- calling it again with the same SKU replaces the product
  instead of erroring.
