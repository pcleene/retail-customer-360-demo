import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from backend.database import connect_db, close_db, get_db
from backend.query_log import reset_log, get_log
from backend.services.memory_service import init_memory_layer
from backend.services.conversation_service import seed_app_users, seed_user_memories
from backend.agents.copilot.service import close_mcp
from backend.streaming.change_stream_watcher import init_watcher
from backend.routers import customers, campaigns, dashboard, copilot, product_insights, signals


@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_db()
    print("Connected to MongoDB Atlas")
    await init_memory_layer()
    print("Memory layer initialised")
    await seed_app_users()
    print("Demo users seeded")
    await seed_user_memories()
    print("User memories seeded")

    # Start the cross-sell signal change stream watcher
    watcher = init_watcher(get_db())
    watcher.start()
    print("Cross-sell signal watcher started")

    yield

    # Shutdown: stop watcher before closing connections
    await watcher.stop()
    print("Cross-sell signal watcher stopped")
    await close_mcp()
    print("MCP session closed")
    await close_db()
    print("Disconnected from MongoDB Atlas")


app = FastAPI(
    title="Retail Customer 360 — Customer 360 Platform",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def query_log_middleware(request: Request, call_next):
    """Inject captured MongoDB queries into JSON API responses."""
    reset_log()
    response = await call_next(request)

    ct = response.headers.get("content-type") or ""
    if request.url.path.startswith("/api/") and "application/json" in ct:
        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        queries = get_log()
        if queries:
            try:
                data = json.loads(body)
                if isinstance(data, dict):
                    data["_queries"] = queries
                    body = json.dumps(data, default=str).encode()
            except Exception:
                pass

        headers = dict(response.headers)
        headers.pop("content-length", None)
        return Response(
            content=body,
            status_code=response.status_code,
            headers=headers,
        )

    return response


app.include_router(customers.router)
app.include_router(campaigns.router)
app.include_router(dashboard.router)
app.include_router(copilot.router)
app.include_router(product_insights.router)
app.include_router(signals.router)


@app.get("/health")
async def health():
    from backend.database import get_db

    db = get_db()
    await db.command("ping")
    return {"status": "ok", "mongodb": "connected"}
