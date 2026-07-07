"""Tiny stdio MCP client -- sanity-checks pim_server.py out-of-process, before wiring up
Claude Desktop. Spawns the server as a subprocess and speaks MCP to it over stdio.

Run:
    python client_demo.py
"""
import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SERVER_PATH = os.path.join(BASE_DIR, "pim_server.py")


async def main():
    params = StdioServerParameters(command=sys.executable, args=[SERVER_PATH])

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            listed = await session.list_tools()
            print("Discovered tools:", [t.name for t in listed.tools])

            print("\n--- get_category_tree ---")
            res = await session.call_tool("get_category_tree", {})
            tree = json.loads(res.content[0].text)
            print(f"{len(tree)} top categories:", list(tree.keys()))

            print("\n--- search_products('noise cancelling headphones') ---")
            res = await session.call_tool("search_products", {"query": "noise cancelling headphones", "k": 3})
            hits = [json.loads(c.text) for c in res.content]
            for h in hits:
                print(f"  - {h['name']}  ({h['category']}, €{h['price']:.0f})")

            print("\n--- create_product (freshness demo) ---")
            new_sku = "SKU-DEMO-001"
            await session.call_tool("create_product", {
                "sku": new_sku,
                "name": "AquaBeat Pro",
                "brand": "AquaBeat",
                "category": "Bluetooth Speakers",
                "price": 79.0,
                "short_description": "Floating waterproof party speaker.",
                "long_description": "AquaBeat Pro — waterproof floating bluetooth pool speaker with 20-hour battery.",
                "attributes": {"water_resistance": "IPX7"},
            })
            res = await session.call_tool("search_products", {"query": "a speaker for the swimming pool", "k": 3})
            hits = [json.loads(c.text) for c in res.content]
            found = any(h["sku"] == new_sku for h in hits)
            print(f"  new product findable immediately after create_product: {found}")
            for h in hits:
                print(f"  - {h['name']}  ({h['category']})")

            print("\n--- get_product(new_sku) ---")
            res = await session.call_tool("get_product", {"sku": new_sku})
            print(" ", json.loads(res.content[0].text))

            print("\n--- get_category_attributes('Headphones') ---")
            res = await session.call_tool("get_category_attributes", {"category": "Headphones"})
            print(" ", json.loads(res.content[0].text))


if __name__ == "__main__":
    asyncio.run(main())
