// ============================================================
// Real-Time KPI Stream Processor
// Aggregates transaction events into hourly KPI snapshots
// for the executive dashboard.
//
// Pipeline:
//   $source (RetailCustomer360.transactions topic)
//   → $tumblingWindow (1hr: total_gmv_myr, txn_count, avg_basket,
//                       categories, stores, payment_methods)
//   → compute velocity_ratio (vs. prior window baseline)
//   → $merge (realtime_kpis collection)
//
// KPI fields:
//   total_gmv_myr    — Gross Merchandise Value for the window
//   txn_count        — Number of transactions
//   avg_basket_myr   — Average basket size
//   categories       — Distinct product categories sold
//   velocity_ratio   — Current vs. baseline throughput ratio
//   window_start/end — Window boundaries
// ============================================================

// Step 1: Source from Kafka with timeField for windowed processing
let source = {
  $source: {
    connectionName: "RetailCustomer360KafkaConnection",
    topic: "RetailCustomer360.transactions",
    timeField: { $toDate: "$fullDocument.timestamp" },
    partitionIdleTimeout: { size: 10, unit: "second" }
  }
};

// Step 2: 1-hour tumbling window — aggregate all transactions
let tumblingWindow = {
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
};

// Step 3: Flatten nested category arrays and compute velocity ratio
// Baseline: ~100 txns/hr for normal operations
let computeKpis = {
  $addFields: {
    categories: {
      $reduce: {
        input: "$categories",
        initialValue: [],
        in: { $setUnion: ["$$value", "$$this"] }
      }
    },
    // Velocity ratio: current throughput vs baseline (100 txn/hr)
    velocity_ratio: {
      $round: [{ $divide: ["$txn_count", 100] }, 2]
    },
    unique_store_count: { $size: "$stores" },
    unique_entity_count: { $size: "$entities" },
    unique_payment_methods: { $size: "$payment_methods" },
    window_id: {
      $concat: [
        "kpi-",
        { $toString: { $toDate: "$window_start" } }
      ]
    },
    computed_at: "$$NOW"
  }
};

// Step 4: Project final KPI document
let projectKpis = {
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
};

// Step 5: Merge into realtime_kpis collection
let mergeStage = {
  $merge: {
    into: {
      connectionName: "RetailCustomer360Cluster",
      db: "RetailCustomer360",
      coll: "realtime_kpis"
    },
    on: "_id",
    whenMatched: "replace"
  }
};

// ── Deploy Commands ──────────────────────────────────────────
// Run in mongosh connected to ASP workspace:
//
// 1. Stop & drop existing processor (if running):
//    sp["RetailCustomer360-realtime-kpis"].stop();
//    sp["RetailCustomer360-realtime-kpis"].drop();
//
// 2. Create the stream processor:
sp.createStreamProcessor("RetailCustomer360-realtime-kpis", [
  source, tumblingWindow, computeKpis, projectKpis, mergeStage
]);
//
// 3. Start:
//    sp["RetailCustomer360-realtime-kpis"].start();
//
// 4. Verify:
//    sp["RetailCustomer360-realtime-kpis"].stats();
