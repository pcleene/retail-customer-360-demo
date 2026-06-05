"""Node 5: Check Realtime — query realtime_kpis for latest windows and anomalies."""

import time

from backend.database import get_db
from backend.agents.insights.state import InsightsState


async def check_realtime_node(state: InsightsState) -> dict:
    """ALWAYS query realtime_kpis collection for the latest KPI windows.
    Flag anomalies where velocity_ratio > 2.0 (current velocity is 2x+ the historical average).

    Uses PyMongo AsyncMongoClient: aggregate() needs await.
    """
    t0 = time.time()
    rbac_filter = state.get("rbac_filter", {})

    try:
        db = get_db()
        coll = db["realtime_kpis"]

        # Build the match stage, incorporating RBAC filter if present
        match_stage: dict = {}
        if rbac_filter:
            # Map supplier_id filter to the realtime_kpis collection fields
            if "supplier_id" in rbac_filter:
                # realtime_kpis may reference products by product_id, so we
                # look up via a $lookup or simply filter by category/brand
                # if supplier_id is embedded. For now, pass through any
                # applicable fields.
                match_stage.update(rbac_filter)
            elif "entity" in rbac_filter:
                match_stage.update(rbac_filter)

        # Get the latest KPI windows, sorted by window_end descending
        pipeline = [
            {"$sort": {"window_end": -1}},
            {"$limit": 20},
            {
                "$project": {
                    "_id": 0,
                    "product_id": 1,
                    "category": 1,
                    "brand": 1,
                    "window_start": 1,
                    "window_end": 1,
                    "units_sold": 1,
                    "revenue_myr": 1,
                    "velocity_ratio": 1,
                }
            },
        ]

        # Insert match stage at the beginning if we have filters
        if match_stage:
            pipeline.insert(0, {"$match": match_stage})

        kpis = []
        async for doc in await coll.aggregate(pipeline):
            doc.pop("_id", None)
            kpis.append(doc)

        anomalies = [kpi for kpi in kpis if kpi.get("velocity_ratio", 0) > 2.0]
        has_anomaly = len(anomalies) > 0

        anomaly_message = ""
        if has_anomaly:
            peak = max(anomalies, key=lambda a: a.get("velocity_ratio", 0))
            peak_ratio = peak.get("velocity_ratio", 0)
            peak_window = peak.get("window_end", "")
            peak_gmv = peak.get("total_gmv_myr", peak.get("revenue_myr", 0))

            anomaly_message = (
                f"{len(anomalies)} time window(s) show sales velocity >{2.0:.0f}x the "
                f"hourly baseline (peak: {peak_ratio:.1f}x"
            )
            if peak_gmv:
                anomaly_message += f", GMV RM{peak_gmv:,.2f}"
            if peak_window:
                anomaly_message += f", at {peak_window}"
            anomaly_message += ")"

        prev_queries = state.get("queries_executed", [])
        return {
            "realtime_kpis": kpis,
            "has_anomaly": has_anomaly,
            "anomaly_message": anomaly_message,
            "queries_executed": prev_queries + [{
                "node": "check_realtime",
                "status": "success",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "collection": "realtime_kpis",
                "kpi_count": len(kpis),
                "anomaly_count": len(anomalies),
                "has_anomaly": has_anomaly,
                "anomaly_threshold": "velocity_ratio > 2.0",
                "mql_pipeline": pipeline,
            }],
        }

    except Exception as e:
        prev_queries = state.get("queries_executed", [])
        return {
            "realtime_kpis": [],
            "has_anomaly": False,
            "anomaly_message": "",
            "queries_executed": prev_queries + [{
                "node": "check_realtime",
                "status": "error",
                "duration_ms": round((time.time() - t0) * 1000, 1),
                "error": str(e),
            }],
        }
