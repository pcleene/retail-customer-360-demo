from pymongo import AsyncMongoClient, MongoClient
from pymongo.asynchronous.database import AsyncDatabase

from backend.config import settings

_client: AsyncMongoClient | None = None
_sync_client: MongoClient | None = None


async def connect_db() -> None:
    global _client, _sync_client
    _client = AsyncMongoClient(settings.mongodb_uri)
    await _client.admin.command("ping")
    _sync_client = MongoClient(settings.mongodb_uri)


async def close_db() -> None:
    global _client, _sync_client
    if _sync_client:
        _sync_client.close()
        _sync_client = None
    if _client:
        await _client.close()
        _client = None


def get_db() -> AsyncDatabase:
    if _client is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _client[settings.mongodb_db]


def get_client() -> AsyncMongoClient:
    """Return the raw AsyncMongoClient for async database operations."""
    if _client is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _client


def get_sync_client() -> MongoClient:
    """Return the synchronous MongoClient for LangGraph checkpointer/store."""
    if _sync_client is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    return _sync_client
