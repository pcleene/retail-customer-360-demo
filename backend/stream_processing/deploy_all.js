// ============================================================
// Deploy All Retail Customer 360 ASP Stream Processors
//
// Idempotent deployment: for each processor, stop → drop → create → start → verify.
// Safe to run multiple times — existing processors are replaced.
//
// Usage:
//   mongosh "<ASP_URI>" --file backend/stream_processing/deploy_all.js
//
// ASP URI format:
//   mongodb://<user>:<pass>@<asp-host>.query.mongodb.net/?ssl=true&authSource=admin
// ============================================================

const processors = [
  // ── 1. Event Ingestion Passthrough ──────────────────────────
  {
    name: "RetailCustomer360-event-ingest",
    pipeline: [
      {
        $source: {
          connectionName: "RetailCustomer360KafkaConnection",
          topic: "RetailCustomer360.transactions"
        }
      },
      {
        $match: {
          "fullDocument.transaction_id": { $exists: true },
          "fullDocument.customer_id": { $exists: true },
          "fullDocument.store_id": { $exists: true },
          "fullDocument.items": { $exists: true },
          "fullDocument.total_myr": { $exists: true },
          "fullDocument.timestamp": { $exists: true }
        }
      },
      { $replaceRoot: { newRoot: "$fullDocument" } },
      {
        $addFields: {
          _ingestedAt: { $toDate: "$_ts" },
          _source: "kafka_asp"
        }
      },
      {
        $merge: {
          into: {
            connectionName: "RetailCustomer360Cluster",
            db: "RetailCustomer360",
            coll: "transactions"
          }
        }
      }
    ]
  },

  // ── 2. Cross-Sell Trigger (windowed + lookup) ──────────────
  {
    name: "RetailCustomer360-cross-sell-trigger",
    pipeline: [
      {
        $source: {
          connectionName: "RetailCustomer360KafkaConnection",
          topic: "RetailCustomer360.transactions",
          timeField: { $toDate: "$fullDocument.timestamp" },
          partitionIdleTimeout: { size: 10, unit: "second" }
        }
      },
      {
        $tumblingWindow: {
          interval: { size: 1, unit: "hour" },
          pipeline: [
            {
              $group: {
                _id: "$fullDocument.customer_id",
                hourly_spend: { $sum: "$fullDocument.total_myr" },
                txn_count: { $sum: 1 },
                categories: { $addToSet: "$fullDocument.items.category" },
                entities: { $addToSet: "$fullDocument.entity" },
                avg_basket: { $avg: "$fullDocument.total_myr" },
                max_basket: { $max: "$fullDocument.total_myr" },
                store_ids: { $addToSet: "$fullDocument.store_id" },
                payment_methods: { $addToSet: "$fullDocument.payment_method" },
                window_start: { $min: "$fullDocument.timestamp" },
                window_end: { $max: "$fullDocument.timestamp" }
              }
            }
          ]
        }
      },
      {
        $addFields: {
          categories: {
            $reduce: {
              input: "$categories",
              initialValue: [],
              in: { $setUnion: ["$$value", "$$this"] }
            }
          }
        }
      },
      {
        $lookup: {
          from: {
            connectionName: "RetailCustomer360Cluster",
            db: "RetailCustomer360",
            coll: "customers"
          },
          localField: "_id",
          foreignField: "customer_id",
          as: "customer"
        }
      },
      { $unwind: { path: "$customer", preserveNullAndEmptyArrays: true } },
      {
        $match: {
          $or: [
            { hourly_spend: { $gt: 500 } },
            { txn_count: { $gt: 5 } },
            { avg_basket: { $gt: 200 } }
          ]
        }
      },
      {
        $addFields: {
          signal_type: {
            $switch: {
              branches: [
                {
                  case: { $and: [{ $gt: ["$hourly_spend", 500] }, { $gt: ["$txn_count", 5] }] },
                  then: "high_value_velocity"
                },
                { case: { $gt: ["$hourly_spend", 500] }, then: "high_spend_window" },
                { case: { $gt: ["$txn_count", 5] }, then: "high_frequency_window" }
              ],
              default: "premium_basket"
            }
          },
          score: {
            $min: [
              1.0,
              {
                $add: [
                  { $multiply: [{ $divide: ["$hourly_spend", 1000] }, 0.4] },
                  { $multiply: [{ $divide: ["$txn_count", 10] }, 0.3] },
                  { $multiply: [{ $divide: [{ $size: "$categories" }, 10] }, 0.3] }
                ]
              }
            ]
          },
          customer_tier: "$customer.loyalty.tier",
          customer_name: "$customer.name",
          processed: { $literal: false },
          created_at: "$$NOW"
        }
      },
      {
        $project: {
          customer_id: "$_id",
          signal_type: 1, score: 1,
          details: {
            hourly_spend: "$hourly_spend", txn_count: "$txn_count",
            avg_basket: "$avg_basket", max_basket: "$max_basket",
            categories: "$categories", entities: "$entities",
            store_ids: "$store_ids", payment_methods: "$payment_methods",
            window_start: "$window_start", window_end: "$window_end"
          },
          customer_tier: 1, customer_name: 1, processed: 1, created_at: 1
        }
      },
      {
        $merge: {
          into: {
            connectionName: "RetailCustomer360Cluster",
            db: "RetailCustomer360",
            coll: "cross_sell_signals"
          }
        }
      }
    ]
  },

  // ── 3. Loyalty Points Aggregator (windowed) ────────────────
  {
    name: "RetailCustomer360-loyalty-aggregator",
    pipeline: [
      {
        $source: {
          connectionName: "RetailCustomer360KafkaConnection",
          topic: "RetailCustomer360.loyalty_events",
          timeField: { $toDate: "$fullDocument.timestamp" },
          partitionIdleTimeout: { size: 10, unit: "second" }
        }
      },
      {
        $tumblingWindow: {
          interval: { size: 1, unit: "hour" },
          pipeline: [
            {
              $group: {
                _id: "$fullDocument.customer_id",
                points_earned: {
                  $sum: {
                    $cond: [{ $eq: ["$fullDocument.event_type", "earn"] }, "$fullDocument.points", 0]
                  }
                },
                points_redeemed: {
                  $sum: {
                    $cond: [{ $eq: ["$fullDocument.event_type", "redeem"] }, "$fullDocument.points", 0]
                  }
                },
                points_expired: {
                  $sum: {
                    $cond: [{ $eq: ["$fullDocument.event_type", "expire"] }, "$fullDocument.points", 0]
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
      },
      {
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
      },
      {
        $merge: {
          into: {
            connectionName: "RetailCustomer360Cluster",
            db: "RetailCustomer360",
            coll: "customers"
          },
          on: "customer_id",
          whenMatched: "merge"
        }
      }
    ]
  },

  // ── 4. Real-Time KPIs (windowed) ───────────────────────────
  {
    name: "RetailCustomer360-realtime-kpis",
    pipeline: [
      {
        $source: {
          connectionName: "RetailCustomer360KafkaConnection",
          topic: "RetailCustomer360.transactions",
          timeField: { $toDate: "$fullDocument.timestamp" },
          partitionIdleTimeout: { size: 10, unit: "second" }
        }
      },
      {
        $tumblingWindow: {
          interval: { size: 1, unit: "hour" },
          pipeline: [
            {
              $group: {
                _id: null,
                total_gmv_myr: { $sum: "$fullDocument.total_myr" },
                txn_count: { $sum: 1 },
                avg_basket_myr: { $avg: "$fullDocument.total_myr" },
                max_basket_myr: { $max: "$fullDocument.total_myr" },
                min_basket_myr: { $min: "$fullDocument.total_myr" },
                categories: { $addToSet: "$fullDocument.items.category" },
                entities: { $addToSet: "$fullDocument.entity" },
                stores: { $addToSet: "$fullDocument.store_id" },
                payment_methods: { $addToSet: "$fullDocument.payment_method" },
                window_start: { $min: "$fullDocument.timestamp" },
                window_end: { $max: "$fullDocument.timestamp" }
              }
            }
          ]
        }
      },
      {
        $addFields: {
          categories: {
            $reduce: {
              input: "$categories",
              initialValue: [],
              in: { $setUnion: ["$$value", "$$this"] }
            }
          },
          velocity_ratio: { $round: [{ $divide: ["$txn_count", 100] }, 2] },
          unique_store_count: { $size: "$stores" },
          unique_entity_count: { $size: "$entities" },
          unique_payment_methods: { $size: "$payment_methods" },
          window_id: { $concat: ["kpi-", { $toString: { $toDate: "$window_start" } }] },
          computed_at: "$$NOW"
        }
      },
      {
        $project: {
          _id: "$window_id",
          total_gmv_myr: { $round: ["$total_gmv_myr", 2] },
          txn_count: 1,
          avg_basket_myr: { $round: ["$avg_basket_myr", 2] },
          max_basket_myr: { $round: ["$max_basket_myr", 2] },
          min_basket_myr: { $round: ["$min_basket_myr", 2] },
          categories: 1,
          category_count: { $size: "$categories" },
          entities: 1,
          unique_store_count: 1,
          unique_entity_count: 1,
          payment_methods: 1,
          unique_payment_methods: 1,
          velocity_ratio: 1,
          window_start: 1,
          window_end: 1,
          computed_at: 1
        }
      },
      {
        $merge: {
          into: {
            connectionName: "RetailCustomer360Cluster",
            db: "RetailCustomer360",
            coll: "realtime_kpis"
          },
          on: "_id",
          whenMatched: "replace"
        }
      }
    ]
  }
];

// ── Idempotent Deployment ────────────────────────────────────
print("=== Retail Customer 360 — Deploying ASP Stream Processors ===\n");

let successCount = 0;
let errorCount = 0;

for (const proc of processors) {
  print(`--- ${proc.name} ---`);

  // Stop existing (ignore errors — may not be running or may not exist)
  try {
    sp[proc.name].stop();
    print(`  Stopped existing ${proc.name}`);
  } catch (e) {
    // Not running or doesn't exist — expected
  }

  // Drop existing (ignore errors)
  try {
    sp[proc.name].drop();
    print(`  Dropped existing ${proc.name}`);
  } catch (e) {
    // Doesn't exist — expected
  }

  // Create
  try {
    sp.createStreamProcessor(proc.name, proc.pipeline);
    print(`  Created ${proc.name}`);
  } catch (e) {
    print(`  ERROR creating ${proc.name}: ${e.message}`);
    errorCount++;
    continue;
  }

  // Start
  try {
    sp[proc.name].start();
    print(`  Started ${proc.name}`);
    successCount++;
  } catch (e) {
    print(`  ERROR starting ${proc.name}: ${e.message}`);
    errorCount++;
  }
}

// ── Verify ───────────────────────────────────────────────────
print("\n=== Listing all RetailCustomer360 processors ===");
try {
  const all = sp.listStreamProcessors();
  const RetailGroup = all.filter(p => p.name.startsWith("RetailCustomer360-"));
  for (const p of RetailGroup) {
    const status = p.state || "unknown";
    const error = p.errorMsg ? ` (ERROR: ${p.errorMsg})` : "";
    print(`  ${p.name}: ${status}${error}`);
  }
} catch (e) {
  print(`  Could not list processors: ${e.message}`);
}

print(`\n=== Deployment complete: ${successCount} succeeded, ${errorCount} failed ===`);
