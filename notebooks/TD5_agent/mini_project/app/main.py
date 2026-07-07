"""PIM Copilot backend -- the TD5 agent loop (reason -> act -> observe) behind one HTTP endpoint.

Serves the Vue chat UI (../web) and POST /chat. The agent's tools come from the TD4 mini-project's
`pim_server.py`, spawned as a subprocess and driven over MCP stdio -- this backend never imports
its code, only launches it (the exact same command you registered in Claude Desktop for TD4).

Run:
    uvicorn app.main:app --reload --app-dir .
Then open http://localhost:8000
"""
import json
import os
import sys
from contextlib import AsyncExitStack
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
TD4_SERVER = (BASE_DIR / ".." / ".." / "TD4_mcp" / "mini_project" / "pim_server.py").resolve()
SKILL_PATH = (BASE_DIR / ".." / ".." / "data" / "skills" / "add_product" / "SKILL.md").resolve()

load_dotenv()
if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY not found. Create a .env file at the project root with ANTHROPIC_API_KEY=sk-ant-..."
    )
if not TD4_SERVER.exists():
    raise RuntimeError(f"TD4 pim_server.py not found at {TD4_SERVER} -- build that mini-project first.")

client = anthropic.Anthropic()
MODEL = "claude-haiku-4-5"
SKILL = SKILL_PATH.read_text()
MAX_ITERS = 12

app = FastAPI(title="PIM Copilot")


class ChatState:
    session: ClientSession | None = None
    tools: list | None = None
    messages: list


state = ChatState()
state.messages = []

_exit_stack = AsyncExitStack()


@app.on_event("startup")
async def startup():
    """Spawn the TD4 stdio MCP server once and keep the session open for the app's lifetime."""
    params = StdioServerParameters(command=sys.executable, args=[str(TD4_SERVER)])
    read, write = await _exit_stack.enter_async_context(stdio_client(params))
    session = await _exit_stack.enter_async_context(ClientSession(read, write))
    await session.initialize()
    state.session = session

    listed = await session.list_tools()
    state.tools = [
        {"name": t.name, "description": t.description, "input_schema": t.inputSchema}
        for t in listed.tools
    ]
    print(f"Connected to TD4 pim_server ({TD4_SERVER}); tools: {[t['name'] for t in state.tools]}")


@app.on_event("shutdown")
async def shutdown():
    await _exit_stack.aclose()


async def run_agent_turn(user_message: str, max_iters: int = MAX_ITERS):
    """Run ONE reason -> act -> observe turn of the TD5 agent loop for a new user message,
    continuing the server-side conversation. Returns (final_text, trace) where trace is the
    list of tool calls made during this turn."""
    state.messages.append({"role": "user", "content": user_message})
    trace = []

    for _ in range(max_iters):
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SKILL,
            tools=state.tools,
            messages=state.messages,
        )
        state.messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            answer = "".join(b.text for b in resp.content if b.type == "text")
            return answer, trace

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                out = await state.session.call_tool(block.name, block.input)
                result_text = "\n".join(c.text for c in out.content)
                trace.append({"tool": block.name, "input": block.input, "output": result_text})
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_text,
                })
        state.messages.append({"role": "user", "content": tool_results})

    return "Reached the iteration limit without a final answer.", trace


class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat(req: ChatRequest):
    answer, trace = await run_agent_turn(req.message)
    return {"reply": answer, "trace": trace}


@app.post("/reset")
async def reset():
    """Clear the server-side conversation (a fresh chat)."""
    state.messages = []
    return {"status": "reset"}


app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web")


@app.get("/")
def index():
    return FileResponse(str(WEB_DIR / "index.html"))
