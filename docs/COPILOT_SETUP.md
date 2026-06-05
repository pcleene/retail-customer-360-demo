# Customer Intelligence Co-pilot — Setup & Architecture

> A natural-language analytics chatbot that talks to MongoDB Atlas through
> the official **MongoDB MCP Server**, with **zero custom database code
> in the agent**.

This document explains:

1. What it is, what makes it special.
2. How it's wired up (end-to-end).
3. How to run it locally in 5 minutes.
4. How to extend, debug, and demo it.

---

## 1. What it is

The Co-pilot is the chat experience on the **/copilot** page. A user
types a question in English (or any language Gemini understands), the
agent translates it into MongoDB queries, runs them against the
`RetailCustomer360` database, and returns a clear, formatted answer — with the
exact MQL it used.

**Example:**

> _"How many tri-entity customers are in Selangor with LTV over RM 10 000?"_

→ The agent:

1. Recalls any saved user preferences from long-term memory.
2. Picks the right collection (`customers`).
3. Builds an aggregation pipeline using its understanding of the schema.
4. Calls the **`aggregate`** tool exposed by the MongoDB MCP server.
5. Summarises the result, formats currency in MYR (RM), and shows the
   pipeline it used.

The chat also writes new memories (`save_memory`) and reads them back
(`recall_memories`) using a vector-indexed memory collection, so user
preferences persist across sessions.

---

## 2. What makes it special

| Conventional approach                                    | This Co-pilot                                                            |
| -------------------------------------------------------- | ------------------------------------------------------------------------ |
| Hand-written DB tools (`get_customer_count(...)`)        | **Zero** custom DB tools. The MCP server exposes them automatically.    |
| Per-feature SQL/MQL adapters maintained alongside the LLM | The agent reads schema from the system prompt and writes pipelines free-form. |
| Bolt-on vector DB for memory                             | Memory lives in MongoDB (`agent_memories`) with a native vector index.  |
| Custom session state store                               | LangGraph `MongoDBSaver` — checkpoints in the same Atlas cluster.        |

**Bottom line:** when you add a new collection or field to MongoDB, you
update one paragraph in the system prompt. The agent can already query it.

---

## 3. Architecture (end-to-end)

```
            User types in /copilot page
                    │
                    ▼
          POST /api/copilot/ask
                    │
        ┌───────────▼───────────────┐
        │  copilot_query()          │  backend/agents/copilot/service.py
        └───────────┬───────────────┘
                    │
        ┌───────────▼─────────────────────────┐
        │ LangGraph create_react_agent         │
        │   • model = ChatVertexAI (Gemini)    │
        │   • prompt = COPILOT_SYSTEM_PROMPT   │
        │   • tools = MCP tools + memory tools │
        │   • checkpointer = MongoDBSaver      │
        │   • store      = MongoDBStore        │
        └───────────┬─────────────────────────┘
                    │  ReAct loop (think → tool → think → answer)
   ┌────────────────┼─────────────────────┐
   │                │                     │
   ▼                ▼                     ▼
[ MCP tools ]   [ save_memory ]   [ recall_memories ]
(find,         (writes to        (vector search on
 aggregate,     agent_memories    agent_memories)
 count, ...)    via MongoDBStore)
   │
   ▼
 stdio transport (npx)
   │
   ▼
┌──────────────────────────────────────┐
│  mongodb-mcp-server  (Node, official)│
│  Reads MDB_MCP_CONNECTION_STRING     │
│  Speaks MCP protocol                 │
│  Issues queries against MongoDB      │
└──────────────────┬───────────────────┘
                   │ wire protocol
                   ▼
            MongoDB Atlas (RetailCustomer360)
```

### 3.1 The MCP session (singleton)

The backend holds **one** stdio MCP session for the lifetime of the
process. See `backend/agents/copilot/service.py`:

- The `_MCPSession` class lazily spawns `npx -y mongodb-mcp-server`
  on first use.
- It passes two env vars:
  - `MDB_MCP_CONNECTION_STRING` — your Atlas URI.
  - `MDB_MCP_READ_ONLY=true` — guard rail, the agent **cannot write
    or drop**.
- On FastAPI shutdown, `close_mcp()` tears down the stdio transport
  cleanly.

### 3.2 Tool loading and Vertex AI compatibility

```python
all_mcp_tools = await load_mcp_tools(session)
filtered = [t for t in all_mcp_tools if t.name not in _EXCLUDED_TOOLS]
mcp_tools = _clean_mcp_tools(filtered)
```

We:

1. Discover every tool the MCP server advertises.
2. Drop tools that don't apply (`connect`, Atlas-Local management
   tools, Atlas Knowledge Sources we don't use, raw logs).
3. Sanitise each tool's JSON Schema so Vertex AI accepts it
   (Vertex's JSON-Schema dialect is stricter than OpenAI's — we strip
   unsupported keywords and rebuild a clean Pydantic model per tool).

### 3.3 Memory tools

Defined in `backend/services/memory_service.py` and exposed to the
agent in addition to MCP tools:

- `save_memory(key, content)` → writes to `agent_memories` namespaced
  by `("user", user_id, "preferences")`.
- `recall_memories(query)` → vector search using a Voyage AI embedding
  of the query, returns top-5 hits.

The system prompt teaches the model **when** to call them — particularly
to call `recall_memories` _before_ answering analytics questions.

### 3.4 Short-term memory (checkpoints)

`MongoDBSaver` writes a checkpoint at every step of the LangGraph for
each `(thread_id, user_id)`. This means:

- Conversations resume across page reloads.
- The "Conversations" side panel can list and replay any past thread
  (`/api/copilot/conversations`, `/api/copilot/conversations/{thread_id}`).

All three of these (checkpoints, memories, conversation transcripts)
live in **the same Atlas cluster** as the customer data.

---

## 4. Setup — running it locally

### 4.1 Prerequisites

- Python 3.12, Node 20+, `npx` on `PATH`.
- MongoDB Atlas cluster (M10+ — Search & Vector Search require dedicated tier).
- Voyage AI API key.
- GCP project with Vertex AI enabled, ADC configured:
  ```bash
  gcloud auth application-default login
  ```

### 4.2 Environment

```bash
cp .env.example .env
```

Fill in:

```
MONGODB_URI=mongodb+srv://<user>:<pass>@<cluster>/?appName=...
MONGODB_DB=RetailCustomer360
VOYAGE_API_KEY=pa-...
GCP_PROJECT_ID=your-gcp-project
GCP_LOCATION=asia-southeast1
VERTEX_AI_MODEL=gemini-2.5-flash
```

`MCP_CONNECTION_STRING` is optional — when blank, the MCP server reuses
`MONGODB_URI`. The MCP server is launched via `npx -y mongodb-mcp-server`
by default; that's controlled by `MCP_SERVER_COMMAND` /
`MCP_SERVER_ARGS` in `backend/config.py`.

### 4.3 Seed and index

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m backend.seed.seed_all
```

The seeder creates:

- All standard B-tree indexes (see `backend/seed/create_indexes.py`).
- `customers_search` (Atlas Search).
- `customers_vector`, `products_vector`, `campaigns_vector`,
  `content_vector` (Atlas Vector Search, 1024-d cosine).
- A non-unique `(namespace, key)` index on `agent_memories` so
  `MongoDBStore` can use the collection without conflicting on its
  default unique index.

> **Note:** Atlas Search / Vector Search indexes take a couple of
> minutes to build server-side. The Co-pilot itself doesn't strictly
> need them (it uses standard MQL), but the rest of the demo does.

### 4.4 Run the API

```bash
uvicorn backend.main:app --reload --port 8000
```

You should see:

```
Connected to MongoDB Atlas
Memory layer initialised
Demo users seeded
User memories seeded
Cross-sell signal watcher started
```

The first time you hit `/api/copilot/ask`, you'll also see:

```
MCP session to MongoDB MCP Server established
Loaded N MCP tools (excluded M, cleaned for Vertex AI): [...]
```

That means the MCP server spun up and the agent has tools.

### 4.5 Run the frontend

```bash
cd frontend && npm install && npm run dev
```

Open <http://localhost:5173/copilot>. Pick a demo user from the dropdown
(top-right) and ask things like:

- _"How many customers are in each segment?"_
- _"What's the average LTV for tri-entity Platinum customers?"_
- _"Compare cross-sell scores across states."_
- _"Remember I always want results in tables, not prose."_ (then ask a
  fresh question — formatting changes.)

Each response shows the **MQL the agent used** and the **memory trace**
of any save / recall calls.

---

## 5. The system prompt — the single source of truth

`backend/agents/copilot/prompts.py` contains the `COPILOT_SYSTEM_PROMPT`.
It defines:

- **Connection rule** — _"You're already connected, do not call connect."_
- **The schema** — every collection the agent is allowed to query, its
  approximate cardinality, and the field paths that matter (including
  nested ones like `unified_profile.address.state`).
- **Domain glossary** — what RetailGroup Co / Credit / Bank are, what
  segments / tiers mean, what XS, LTV, RM stand for.
- **Query rules** — always use `RetailCustomer360`, exclude embeddings, never use
  `$regex`, format MYR currency, etc.
- **Memory protocol** — exactly when to call `save_memory` and
  `recall_memories`.

> **Adding a new collection? Just add a section to this prompt.** No
> code changes required.

---

## 6. API surface

All endpoints under `/api/copilot/`:

| Method | Path                                  | Purpose                            |
| ------ | ------------------------------------- | ---------------------------------- |
| POST   | `/ask`                                | Ask a question                     |
| GET    | `/history/{session_id}`               | Recent turns for a session         |
| GET    | `/conversations`                      | List past conversations            |
| GET    | `/conversations/{thread_id}`          | One conversation in detail         |
| GET    | `/conversations/{thread_id}/resume`   | Resume an old thread               |
| GET    | `/memories/{user_id}`                 | Long-term memory for a user        |
| GET    | `/users`                              | Demo user list (with suggestions)  |
| GET    | `/stats`                              | Total queries / avg latency         |

Request body for `/ask`:

```json
{
  "question": "How many tri-entity customers are in Selangor?",
  "session_id": "session-analyst-1-1715000000",
  "user_id": "analyst-1"
}
```

Response includes `answer`, `mql`, `memory_trace`, `latency_ms`,
`session_id`, `user_id`.

---

## 7. Customising

### 7.1 Add or remove MCP tools

Edit the `_EXCLUDED_TOOLS` set in
`backend/agents/copilot/service.py`. Anything not excluded is loaded and
exposed to the LLM. To allow writes, also remove `MDB_MCP_READ_ONLY` —
**but think carefully**, the agent will be able to update / delete.

### 7.2 Change the model

Set `VERTEX_AI_MODEL` in `.env` (e.g. `gemini-2.5-pro`,
`gemini-2.0-flash`) or override `gcp_location`. To swap providers
entirely, replace `ChatVertexAI` in `_build_agent()` with
e.g. `ChatOpenAI` or `ChatAnthropic`. Tool schema sanitising is
Vertex-specific; OpenAI/Anthropic don't need it (you can simplify
`_clean_mcp_tools`).

### 7.3 Tune memory

`MongoDBStore` is configured with `voyage-4-lite` query embeddings and
1024-dim cosine similarity. To change vector dim, you'll need to drop
the existing memory collection and recreate it.

### 7.4 Restrict the database

Set `MCP_CONNECTION_STRING` to a Mongo user that only has access to
specific collections. The agent inherits whatever permissions that
user has — RBAC by connection string.

---

## 8. Debugging cheat sheet

| Symptom                                                 | Likely cause                                                   | Fix                                                                  |
| ------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------- |
| `MCP session to MongoDB MCP Server established` never logs | npx not on PATH; first-time install of `mongodb-mcp-server` slow | Run `npx -y mongodb-mcp-server --help` once manually to warm cache  |
| Agent says "I'm already connected" then nothing happens | Vertex schema validation failed on a tool                      | Check logs — the offending tool is logged, often it's `Invalid argument` |
| Memory never recalls                                    | `agent_memories` vector index still building or wrong dim      | Atlas UI → Search Indexes → confirm index status / `numDimensions=1024` |
| `save_memory` saves but `recall_memories` returns empty | Same vector dim mismatch, or query embedding empty             | Make sure `VOYAGE_API_KEY` is set; query embedding falls back to zeros otherwise |
| Slow first response, fast subsequent                    | Cold MCP session boot                                          | Normal — keep the FastAPI process warm                               |
| Agent ignores the schema and hallucinates fields        | System prompt drift                                            | Edit `backend/agents/copilot/prompts.py` to match your collections    |

---

## 9. How this maps to MongoDB's value story

For a customer call, this Co-pilot is a small but very persuasive demo
because it stitches together **four** distinct MongoDB stories at once:

1. **Operational data store** — the very same `customers` collection
   that powers the dashboard is what the agent reads.
2. **MCP-native AI access** — no glue code; LLMs speak Mongo through
   the official server.
3. **Vector-indexed agent memory** — `agent_memories` with Atlas
   Vector Search, queried with Voyage AI embeddings.
4. **State persistence** — LangGraph checkpoints in the same cluster,
   alongside the conversational audit log.

> One Atlas cluster, one query language, one driver — does the work of
> a database, a search engine, a vector DB, an agent state store, and
> an LLM-tool gateway.

That's the demo, in one sentence.

---

## 10. References

- MongoDB MCP Server: <https://github.com/mongodb-js/mongodb-mcp-server>
- Model Context Protocol: <https://modelcontextprotocol.io/>
- LangGraph + MongoDB: <https://github.com/langchain-ai/langgraph-checkpoint-mongodb>
- Voyage AI: <https://docs.voyageai.com/>
- Vertex AI Gemini: <https://cloud.google.com/vertex-ai/generative-ai/docs>

In this repo:

- [`backend/agents/copilot/service.py`](../backend/agents/copilot/service.py)
  — full agent assembly.
- [`backend/agents/copilot/prompts.py`](../backend/agents/copilot/prompts.py)
  — system prompt.
- [`backend/services/memory_service.py`](../backend/services/memory_service.py)
  — checkpointer + semantic store.
- [`backend/config.py`](../backend/config.py) — MCP and Vertex settings.
