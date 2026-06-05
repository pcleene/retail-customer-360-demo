// ============================================================
// Loyalty Points Aggregator Stream Processor
// Aggregates loyalty events (earn/redeem/expire) into hourly
// summaries and merges running totals into the customers
// collection.
//
// Pipeline:
//   $source (RetailCustomer360.loyalty_events topic)
//   → $tumblingWindow (1hr: points_earned, points_redeemed,
//                       points_expired, event_count)
//   → $merge (customers collection, on customer_id, whenMatched: merge)
//
// Updates the customer document with:
//   loyalty.hourly_points_earned
//   loyalty.hourly_points_redeemed
//   loyalty.hourly_points_expired
//   loyalty.last_loyalty_activity
//   loyalty.last_tier_change (if applicable)
// ============================================================

// Step 1: Source from Kafka with timeField for windowed processing
let source = {
  $source: {
    connectionName: "RetailCustomer360KafkaConnection",
    topic: "RetailCustomer360.loyalty_events",
    timeField: { $toDate: "$fullDocument.timestamp" },
    partitionIdleTimeout: { size: 10, unit: "second" }
  }
};

// Step 2: 1-hour tumbling window — aggregate loyalty events per customer
let tumblingWindow = {
  $tumblingWindow: {
    interval: { size: 1, unit: "hour" },
    pipeline: [
      {
        $group: {
          _id: "$fullDocument.customer_id",
          points_earned: {
            $sum: {
              $cond: [
                { $eq: ["$fullDocument.event_type", "earn"] },
                "$fullDocument.points",
                0
              ]
            }
          },
          points_redeemed: {
            $sum: {
              $cond: [
                { $eq: ["$fullDocument.event_type", "redeem"] },
                "$fullDocument.points",
                0
              ]
            }
          },
          points_expired: {
            $sum: {
              $cond: [
                { $eq: ["$fullDocument.event_type", "expire"] },
                "$fullDocument.points",
                0
              ]
            }
          },
          event_count: { $sum: 1 },
          last_activity: { $max: "$fullDocument.timestamp" },
          last_tier_change: {
            $max: {
              $cond: [
                { $ifNull: ["$fullDocument.tier_change", false] },
                "$fullDocument.tier_change",
                "$$REMOVE"
              ]
            }
          }
        }
      }
    ]
  }
};

// Step 3: Reshape for merge into customers collection
let reshapeForMerge = {
  $project: {
    customer_id: "$_id",
    "loyalty.hourly_points_earned": "$points_earned",
    "loyalty.hourly_points_redeemed": "$points_redeemed",
    "loyalty.hourly_points_expired": "$points_expired",
    "loyalty.hourly_event_count": "$event_count",
    "loyalty.last_loyalty_activity": "$last_activity",
    "loyalty.last_tier_change": "$last_tier_change",
    "loyalty.last_aggregated_at": "$$NOW"
  }
};

// Step 4: Merge into customers collection
let mergeStage = {
  $merge: {
    into: {
      connectionName: "RetailCustomer360Cluster",
      db: "RetailCustomer360",
      coll: "customers"
    },
    on: "customer_id",
    whenMatched: "merge"
  }
};

// ── Deploy Commands ──────────────────────────────────────────
// Run in mongosh connected to ASP workspace:
//
// 1. Stop & drop existing processor (if running):
//    sp["RetailCustomer360-loyalty-aggregator"].stop();
//    sp["RetailCustomer360-loyalty-aggregator"].drop();
//
// 2. Create the stream processor:
sp.createStreamProcessor("RetailCustomer360-loyalty-aggregator", [
  source, tumblingWindow, reshapeForMerge, mergeStage
]);
//
// 3. Start:
//    sp["RetailCustomer360-loyalty-aggregator"].start();
//
// 4. Verify:
//    sp["RetailCustomer360-loyalty-aggregator"].stats();
