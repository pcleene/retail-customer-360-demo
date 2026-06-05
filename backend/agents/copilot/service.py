"""Customer Intelligence Co-pilot — MCP-based MongoDB agent.

Uses the MongoDB MCP Server (via npx) for database access,
LangGraph's create_react_agent for tool orchestration, and
Voyage AI-backed memory for long-term user preferences.
"""

import asyncio
import logging
import re
import time
from contextlib import AsyncExitStack

from langchain_google_vertexai import ChatVertexAI
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools

from backend.config import settings
from backend.services.memory_service import (
    create_memory_tools,
    get_checkpointer,
    get_memory_store,
)
from backend.services.conversation_service import save_conversation_turn
from backend.agents.copilot.prompts import COPILOT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

_EXCLUDED_TOOLS = frozenset(
    {
        "connect",
        "atlas-local-connect-deployment",
        "atlas-local-list-deployments",
        "list-knowledge-sources",
        "search-knowledge",
        "mongodb-logs",
    }
)

_MEMORY_TOOL_NAMES = {"save_memory", "recall_memories"}

# Vertex AI supported JSON Schema types
_VERTEX_TYPES = {"string", "number", "integer", "boolean", "array", "object"}


# Properties injected by LangChain internals that Vertex AI can't handle
_STRIP_PROPERTIES = {"config", "run_manager", "kwargs"}


def _sanitize_schema(schema: dict) -> dict:
    """Recursively strip JSON Schema features unsupported by Vertex AI."""
    if not isinstance(schema, dict):
        return schema

    # Strip LangChain-internal properties at the top level
    if "properties" in schema and isinstance(schema["properties"], dict):
        schema = dict(schema)
        schema["properties"] = {
            k: v for k, v in schema["properties"].items() if k not in _STRIP_PROPERTIES
        }
        if "required" in schema and isinstance(schema["required"], list):
            schema["required"] = [r for r in schema["required"] if r not in _STRIP_PROPERTIES]

    out: dict = {}
    for k, v in schema.items():
        if k in ("$schema", "additionalProperties", "default", "$defs", "definitions"):
            continue
        if k in ("anyOf", "oneOf"):
            for branch in v:
                if isinstance(branch, dict) and branch.get("type") != "null":
                    out.update(_sanitize_schema(branch))
                    break
            continue
        if k == "type" and v not in _VERTEX_TYPES:
            out[k] = "string"
            continue
        if isinstance(v, dict):
            out[k] = _sanitize_schema(v)
        elif isinstance(v, list):
            out[k] = [_sanitize_schema(i) if isinstance(i, dict) else i for i in v]
        else:
            out[k] = v
    return out


def _make_clean_tool(original_tool):
    """Create a StructuredTool wrapper with Vertex AI-compatible schema.

    MCP tools set args_schema to a raw JSON Schema dict (not a Pydantic model),
    so StructuredTool falls back to inferring schema from the coroutine signature,
    which leaks LangChain's internal `config` parameter. We rebuild each tool
    with an explicit Pydantic model derived from the sanitized JSON Schema.
    """
    from langchain_core.tools import StructuredTool
    from pydantic import create_model, Field

    # Get the raw JSON schema — it may be a dict OR a Pydantic model class
    args_schema = original_tool.args_schema
    if isinstance(args_schema, dict):
        raw_schema = args_schema
    elif hasattr(args_schema, "model_json_schema"):
        raw_schema = args_schema.model_json_schema()
    else:
        raw_schema = {}

    clean = _sanitize_schema(raw_schema)
    props = clean.get("properties", {})
    required = set(clean.get("required", []))

    # Map JSON Schema types to Python types with non-None defaults to avoid anyOf
    _type_defaults = {
        "string": (str, ""),
        "integer": (int, 0),
        "number": (float, 0.0),
        "boolean": (bool, False),
        "array": (list, []),
        "object": (dict, {}),
    }

    fields = {}
    for name, prop in props.items():
        desc = prop.get("description", "")
        ptype = prop.get("type", "string")
        py_type, default_val = _type_defaults.get(ptype, (str, ""))
        if name in required:
            fields[name] = (py_type, Field(description=desc))
        else:
            if not desc:
                desc = "(Optional)"
            fields[name] = (py_type, Field(default=default_val, description=desc))

    if not fields:
        fields["_placeholder"] = (str, Field(default="", description="unused"))

    model_cls = create_model(f"{original_tool.name}_Args", **fields)

    _orig_coroutine = original_tool.coroutine
    _orig_func = original_tool.func

    async def _run_wrapper(**kwargs):
        kwargs.pop("_placeholder", None)
        # Strip default/empty values so the MCP tool sees absent params as unset
        filtered = {}
        for k, v in kwargs.items():
            if v is None:
                continue
            if isinstance(v, str) and v == "":
                continue
            if isinstance(v, (list, dict)) and not v:
                continue
            filtered[k] = v
        if _orig_coroutine:
            return await _orig_coroutine(**filtered)
        if _orig_func:
            return _orig_func(**filtered)
        return await original_tool.ainvoke(filtered)

    return StructuredTool(
        name=original_tool.name,
        description=original_tool.description or original_tool.name,
        coroutine=_run_wrapper,
        args_schema=model_cls,
        response_format=getattr(original_tool, "response_format", "content"),
    )


def _clean_mcp_tools(tools: list) -> list:
    """Rebuild MCP tools with Vertex AI-compatible schemas."""
    cleaned = []
    for tool in tools:
        try:
            cleaned.append(_make_clean_tool(tool))
        except Exception as e:
            logger.warning("Could not clean tool %s, skipping: %s", tool.name, e)
    return cleaned


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

_stats = {"totalQueries": 0, "totalLatencyMs": 0.0}


def get_copilot_stats() -> dict:
    total = _stats["totalQueries"]
    return {
        "totalQueries": total,
        "activeSessions": 0,
        "avgLatencyMs": round(_stats["totalLatencyMs"] / total, 0) if total > 0 else 0,
    }


# ---------------------------------------------------------------------------
# MCP Session Singleton
# ---------------------------------------------------------------------------

class _MCPSession:
    """Manages a singleton MCP stdio session to the MongoDB MCP Server."""

    def __init__(self):
        self._session: ClientSession | None = None
        self._exit_stack: AsyncExitStack | None = None
        self._lock = asyncio.Lock()

    async def _ensure_session(self) -> ClientSession:
        if self._session is not None:
            return self._session

        async with self._lock:
            if self._session is not None:
                return self._session

            uri = settings.mcp_connection_string or settings.mongodb_uri
            server_params = StdioServerParameters(
                command=settings.mcp_server_command,
                args=settings.mcp_server_args,
                env={
                    "MDB_MCP_CONNECTION_STRING": uri,
                    "MDB_MCP_READ_ONLY": "true",
                },
            )

            self._exit_stack = AsyncExitStack()
            stdio_transport = await self._exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read_stream, write_stream = stdio_transport
            session = await self._exit_stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await session.initialize()

            self._session = session
            logger.info("MCP session to MongoDB MCP Server established")
            return self._session

    async def get_session(self) -> ClientSession:
        return await self._ensure_session()

    async def close(self):
        async with self._lock:
            if self._exit_stack:
                await self._exit_stack.aclose()
                self._exit_stack = None
            self._session = None
            logger.info("MCP session closed")


_mcp = _MCPSession()


# ---------------------------------------------------------------------------
# Agent Factory
# ---------------------------------------------------------------------------

async def _build_agent(user_id: str):
    """Build the ReAct agent with MCP + memory tools."""
    session = await _mcp.get_session()

    all_mcp_tools = await load_mcp_tools(session)
    filtered = [t for t in all_mcp_tools if t.name not in _EXCLUDED_TOOLS]
    mcp_tools = _clean_mcp_tools(filtered)
    logger.info(
        "Loaded %d MCP tools (excluded %d, cleaned for Vertex AI): %s",
        len(mcp_tools),
        len(all_mcp_tools) - len(filtered),
        [t.name for t in mcp_tools],
    )

    memory_tools = _clean_mcp_tools(create_memory_tools(user_id))

    model = ChatVertexAI(
        model_name=settings.vertex_ai_model,
        project=settings.gcp_project_id,
        location=settings.gcp_location,
        temperature=0.1,
        max_output_tokens=4000,
    )

    checkpointer = get_checkpointer()
    store = get_memory_store()

    agent = create_react_agent(
        model,
        tools=mcp_tools + memory_tools,
        checkpointer=checkpointer,
        store=store,
        prompt=COPILOT_SYSTEM_PROMPT,
    )
    return agent


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def copilot_query(
    question: str,
    session_id: str = "default",
    user_id: str = "anonymous",
) -> dict:
    """Process a natural-language question through the Co-pilot agent.

    Returns: question, answer, mql, session_id, user_id, latency_ms, memory_trace.
    """
    start = time.time()
    agent = await _build_agent(user_id)

    config = {
        "configurable": {
            "thread_id": session_id,
            "user_id": user_id,
        }
    }

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": question}]},
        config=config,
    )

    messages = result.get("messages", [])
    answer = ""
    for msg in reversed(messages):
        if hasattr(msg, "content") and msg.type == "ai" and msg.content:
            answer = msg.content
            break

    latency_ms = round((time.time() - start) * 1000, 0)
    mql = _extract_mql(answer)
    memory_trace = _extract_memory_trace(messages)

    _stats["totalQueries"] += 1
    _stats["totalLatencyMs"] += latency_ms

    asyncio.create_task(
        save_conversation_turn("copilot", session_id, user_id, question, answer, mql, latency_ms)
    )

    return {
        "question": question,
        "answer": answer,
        "mql": mql,
        "session_id": session_id,
        "user_id": user_id,
        "latency_ms": latency_ms,
        "memory_trace": memory_trace,
    }


async def close_mcp():
    """Shut down the MCP session. Call during application shutdown."""
    await _mcp.close()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_mql(text: str) -> dict | None:
    """Best-effort extraction of MQL from the agent's response text."""
    if not text:
        return None

    pattern = r"```(?:json|javascript|js|mql)\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    if matches:
        return {"raw": matches[0].strip()}

    find_match = re.search(
        r"(db\.\w+\.(?:find|aggregate|countDocuments)\(.*?\))",
        text,
        re.DOTALL,
    )
    if find_match:
        return {"raw": find_match.group(1).strip()}

    return None


def _extract_memory_trace(messages: list) -> list[dict]:
    """Walk agent messages and extract memory tool call/result pairs."""
    pending: dict[str, dict] = {}
    trace: list[dict] = []

    for msg in messages:
        if isinstance(msg, AIMessage) and msg.tool_calls:
            for tc in msg.tool_calls:
                if tc["name"] in _MEMORY_TOOL_NAMES:
                    pending[tc["id"]] = {
                        "tool": tc["name"],
                        "input": tc["args"],
                    }
        elif isinstance(msg, ToolMessage) and msg.tool_call_id in pending:
            entry = pending.pop(msg.tool_call_id)
            entry["output"] = msg.content
            trace.append(entry)

    return trace
