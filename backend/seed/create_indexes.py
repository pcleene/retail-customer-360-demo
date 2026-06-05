"""Create all MongoDB indexes: standard, Atlas Search, and Vector Search."""

import asyncio

from pymongo import AsyncMongoClient, ASCENDING, DESCENDING, GEOSPHERE

from backend.config import settings


async def create_standard_indexes(db):
    """Create standard B-tree indexes for query performance."""
    print("Creating standard indexes...")

    # Customers — nested schema paths
    cust = db["customers"]
    await cust.create_index("customer_id", unique=True)
    await cust.create_index("segment")
    await cust.create_index("tier")
    await cust.create_index("unified_profile.address.state")
    await cust.create_index("unified_profile.ethnicity")
    await cust.create_index("unified_profile.gender")
    await cust.create_index([("cross_entity_metrics.total_ltv", DESCENDING)])
    await cust.create_index([("cross_entity_metrics.cross_sell_score", DESCENDING)])
    await cust.create_index([("cross_entity_metrics.churn_risk", DESCENDING)])
    await cust.create_index([("tier", ASCENDING), ("cross_entity_metrics.cross_sell_score", DESCENDING)])
    await cust.create_index([("segment", ASCENDING), ("unified_profile.address.state", ASCENDING)])
    await cust.create_index("primary_store_id")
    await cust.create_index("entities")
    await cust.create_index("entity_profiles.RetailGroup_co.preferred_stores.store_id")
    await cust.create_index([("active_campaigns.status", ASCENDING)])
    await cust.create_index("interaction_history.marketing_interactions.campaign_id")
    await cust.create_index("join_date")
    await cust.create_index([("last_visit", DESCENDING)])

    # Transactions
    txn = db["transactions"]
    await txn.create_index("transaction_id", unique=True)
    await txn.create_index("customer_id")
    await txn.create_index("store_id")
    await txn.create_index("date")
    await txn.create_index([("customer_id", ASCENDING), ("date", DESCENDING)])
    await txn.create_index("channel")
    await txn.create_index("campaign_attribution")
    await txn.create_index([("date", DESCENDING), ("store_id", ASCENDING)])

    # Products
    prod = db["products"]
    await prod.create_index("product_id", unique=True)
    await prod.create_index("category")
    await prod.create_index("supplier_id")
    await prod.create_index("brand")
    await prod.create_index([("performance.revenue_ytd", DESCENDING)])
    await prod.create_index("lifecycle_stage")
    await prod.create_index("tags")
    await prod.create_index("attributes.is_halal_certified")
    await prod.create_index([("performance.margin_pct", DESCENDING)])
    await prod.create_index([("performance.return_rate_pct", DESCENDING)])

    # Campaigns
    camp = db["campaigns"]
    await camp.create_index("campaign_id", unique=True)
    await camp.create_index("status")
    await camp.create_index("type")
    await camp.create_index("entity")

    # Content assets
    content = db["content_assets"]
    await content.create_index("content_id", unique=True)
    await content.create_index("campaign_id")
    await content.create_index("channel")

    # Stores
    stores = db["stores"]
    await stores.create_index("store_id", unique=True)
    await stores.create_index([("location", GEOSPHERE)])

    # Signals
    signals = db["cross_sell_signals"]
    await signals.create_index("customer_id")
    await signals.create_index("signal_id", unique=True)
    await signals.create_index("severity")
    await signals.create_index("signal_type")
    await signals.create_index([("created_at", DESCENDING), ("processed", ASCENDING)])

    # Thresholds
    thresholds = db["thresholds"]
    await thresholds.create_index("threshold_id", unique=True)
    await thresholds.create_index("signal_type")
    await thresholds.create_index([("active", ASCENDING), ("severity", DESCENDING)])

    # Campaign actions
    actions = db["campaign_actions"]
    await actions.create_index("action_id", unique=True)
    await actions.create_index("enrollment_id")
    await actions.create_index("customer_id")
    await actions.create_index("campaign_id")
    await actions.create_index([("created_at", DESCENDING)])
    await actions.create_index("status")

    # Realtime KPIs
    kpis = db["realtime_kpis"]
    await kpis.create_index([("window_start", DESCENDING)])
    await kpis.create_index([("window_end", DESCENDING)])

    print("  Standard indexes created")


async def create_search_indexes(db):
    """Create Atlas Search and Vector Search indexes."""
    print("Creating Atlas Search indexes...")

    # Customer search index — nested schema with full text, facet, equals, range support
    # NOTE: Atlas Search only allows ONE string type per field, so we use lucene.standard
    # for text search and rely on token/stringFacet for exact match and facets.
    customer_search_def = {
        "mappings": {
            "dynamic": False,
            "fields": {
                "customer_id": [
                    {"type": "string", "analyzer": "lucene.keyword"},
                    {"type": "token"},
                ],
                "segment": [
                    {"type": "string", "analyzer": "lucene.standard"},
                    {"type": "stringFacet"},
                    {"type": "token"},
                ],
                "tier": [
                    {"type": "string", "analyzer": "lucene.standard"},
                    {"type": "stringFacet"},
                    {"type": "token"},
                ],
                "entities": [
                    {"type": "string", "analyzer": "lucene.standard"},
                    {"type": "stringFacet"},
                    {"type": "token"},
                ],
                "primary_store_id": [
                    {"type": "string", "analyzer": "lucene.keyword"},
                    {"type": "token"},
                ],
                "embedding_text": [
                    {"type": "string", "analyzer": "lucene.standard"},
                ],
                "unified_profile": {
                    "type": "document",
                    "fields": {
                        "name": {"type": "string", "analyzer": "lucene.standard"},
                        "ethnicity": [
                            {"type": "string", "analyzer": "lucene.standard"},
                            {"type": "stringFacet"},
                            {"type": "token"},
                        ],
                        "gender": [
                            {"type": "string", "analyzer": "lucene.standard"},
                            {"type": "stringFacet"},
                            {"type": "token"},
                        ],
                        "address": {
                            "type": "document",
                            "fields": {
                                "city": {"type": "string", "analyzer": "lucene.standard"},
                                "state": [
                                    {"type": "string", "analyzer": "lucene.standard"},
                                    {"type": "stringFacet"},
                                    {"type": "token"},
                                ],
                            },
                        },
                    },
                },
                "cross_entity_metrics": {
                    "type": "document",
                    "fields": {
                        "total_ltv": [{"type": "numberFacet"}, {"type": "number"}],
                        "cross_sell_score": [{"type": "numberFacet"}, {"type": "number"}],
                        "churn_risk": [{"type": "numberFacet"}, {"type": "number"}],
                    },
                },
                "entity_profiles": {
                    "type": "document",
                    "fields": {
                        "RetailGroup_co": {
                            "type": "document",
                            "fields": {
                                "top_categories": {
                                    "type": "string",
                                    "analyzer": "lucene.standard",
                                },
                            },
                        },
                        "RetailGroup_credit": {
                            "type": "document",
                            "fields": {
                                "products": {
                                    "type": "document",
                                    "fields": {
                                        "product_name": {
                                            "type": "string",
                                            "analyzer": "lucene.standard",
                                        },
                                    },
                                },
                            },
                        },
                    },
                },
            },
        }
    }

    # Customer vector search index — filter paths match nested schema
    customer_vector_def = {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": settings.voyage_dimensions,
                "similarity": "cosine",
            },
            {"type": "filter", "path": "segment"},
            {"type": "filter", "path": "tier"},
            {"type": "filter", "path": "entities"},
            {"type": "filter", "path": "unified_profile.address.state"},
            {"type": "filter", "path": "unified_profile.gender"},
            {"type": "filter", "path": "unified_profile.ethnicity"},
            {"type": "filter", "path": "active_campaigns.status"},
        ]
    }

    # Campaign vector search index
    campaign_vector_def = {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": settings.voyage_dimensions,
                "similarity": "cosine",
            },
            {"type": "filter", "path": "status"},
            {"type": "filter", "path": "type"},
            {"type": "filter", "path": "entity"},
        ]
    }

    # Content vector search index
    content_vector_def = {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": settings.voyage_dimensions,
                "similarity": "cosine",
            },
            {"type": "filter", "path": "campaign_id"},
            {"type": "filter", "path": "channel"},
        ]
    }

    # Product vector search index
    product_vector_def = {
        "fields": [
            {
                "type": "vector",
                "path": "embedding",
                "numDimensions": settings.voyage_dimensions,
                "similarity": "cosine",
            },
            {"type": "filter", "path": "category"},
            {"type": "filter", "path": "supplier_id"},
            {"type": "filter", "path": "lifecycle_stage"},
        ]
    }

    search_indexes = [
        ("customers", "customers_search", "search", customer_search_def),
        ("customers", "customers_vector", "vectorSearch", customer_vector_def),
        ("campaigns", "campaigns_vector", "vectorSearch", campaign_vector_def),
        ("content_assets", "content_vector", "vectorSearch", content_vector_def),
        ("products", "products_vector", "vectorSearch", product_vector_def),
    ]

    for coll_name, idx_name, idx_type, definition in search_indexes:
        try:
            coll = db[coll_name]
            try:
                await coll.drop_search_index(idx_name)
                print(f"  Dropped existing index: {idx_name}")
                await asyncio.sleep(2)
            except Exception:
                pass

            await coll.create_search_index(
                {"definition": definition, "name": idx_name, "type": idx_type}
            )
            print(f"  Created {idx_type} index: {idx_name} on {coll_name}")
        except Exception as e:
            print(f"  WARN: Could not create {idx_name}: {e}")
            print(f"  -> Create manually in Atlas UI with definition:")
            print(f"     Collection: {coll_name}, Name: {idx_name}, Type: {idx_type}")

    print("Atlas Search indexes creation initiated (may take a few minutes to build)")


async def main():
    client = AsyncMongoClient(settings.mongodb_uri)
    db = client[settings.mongodb_db]

    await create_standard_indexes(db)
    await create_search_indexes(db)

    await client.close()
    print("All indexes created successfully")


if __name__ == "__main__":
    asyncio.run(main())
