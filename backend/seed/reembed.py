"""Re-embed existing documents with voyage-4-large (replacing voyage-3 embeddings)."""

import asyncio

from pymongo import AsyncMongoClient

from backend.config import settings
from backend.services.embedding_service import embed_batch

BATCH = 128


async def reembed_customers():
    """Re-embed all customers with voyage-4-large."""
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    coll = db["customers"]

    total = await coll.count_documents({})
    print(f"Re-embedding {total:,} customers with {settings.voyage_index_model}...")

    skip = 0
    processed = 0
    while True:
        docs = []
        async for doc in coll.find({}, {"_id": 1, "name": 1, "segment": 1, "tier": 1,
                                         "state": 1, "entities": 1}).skip(skip).limit(BATCH):
            docs.append(doc)

        if not docs:
            break

        texts = [
            f"{d.get('segment', '')} {d.get('tier', '')} {' '.join(d.get('entities', []))} "
            f"{d.get('state', '')} {d.get('name', '')}"
            for d in docs
        ]
        embeddings = embed_batch(texts, batch_size=BATCH)

        ops = []
        for doc, emb in zip(docs, embeddings):
            ops.append({
                "filter": {"_id": doc["_id"]},
                "update": {"$set": {"embedding": emb}},
            })

        # Bulk update
        from pymongo import UpdateOne
        await coll.bulk_write([UpdateOne(o["filter"], o["update"]) for o in ops])

        processed += len(docs)
        skip += BATCH
        if processed % 1000 == 0 or processed >= total:
            print(f"  Customers: {processed:,}/{total:,}")

    print(f"Done re-embedding {processed:,} customers")
    await client.close()


async def reembed_campaigns():
    """Re-embed all campaigns with voyage-4-large."""
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]
    coll = db["campaigns"]

    docs = []
    async for doc in coll.find({}, {"_id": 1, "name": 1, "description": 1, "target_segment": 1}):
        docs.append(doc)

    if not docs:
        print("No campaigns to re-embed")
        return

    print(f"Re-embedding {len(docs)} campaigns with {settings.voyage_index_model}...")
    texts = [f"{d.get('name', '')} {d.get('description', '')} {d.get('target_segment', '')}" for d in docs]
    embeddings = embed_batch(texts, batch_size=BATCH)

    from pymongo import UpdateOne
    ops = [UpdateOne({"_id": doc["_id"]}, {"$set": {"embedding": emb}}) for doc, emb in zip(docs, embeddings)]
    await coll.bulk_write(ops)
    print(f"Done re-embedding {len(docs)} campaigns")

    # Also re-embed content assets
    coll2 = db["content_assets"]
    docs2 = []
    async for doc in coll2.find({}, {"_id": 1, "title": 1, "description": 1, "format": 1}):
        docs2.append(doc)

    if docs2:
        print(f"Re-embedding {len(docs2)} content assets...")
        texts2 = [f"{d.get('title', '')} {d.get('description', '')} {d.get('format', '')}" for d in docs2]
        embeddings2 = embed_batch(texts2, batch_size=BATCH)
        ops2 = [UpdateOne({"_id": doc["_id"]}, {"$set": {"embedding": emb}}) for doc, emb in zip(docs2, embeddings2)]
        await coll2.bulk_write(ops2)
        print(f"Done re-embedding {len(docs2)} content assets")

    await client.close()


async def main():
    await reembed_campaigns()
    await reembed_customers()


if __name__ == "__main__":
    asyncio.run(main())
