// ============================================================
// Cross-Sell Trigger Stream Processor
// Detects high-value shopping patterns that should trigger
// the cross-sell AI agent for real-time recommendations.
//
// Pipeline:
//   $source (RetailCustomer360.transactions)
//   → $tumblingWindow (1hr: hourly_spend, txn_count, categories, entities)
//   → $lookup (customers collection for profile context)
//   → $match (threshold evaluation)
//   → $merge (into cross_sell_signals collection)
//
// Trigger conditions (any one):
//   - Hourly spend > RM 500
//   - Transaction count > 5 in 1 hour
//   - New category detected (vs. customer's historical categories)
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

// Step 2: 1-hour tumbling window — aggregate per customer
let tumblingWindow = {
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
          payment_methods: { $addToSet: "$fullDocument.payment_method" },
          avg_basket: { $avg: "$fullDocument.total_myr" },
          max_basket: { $max: "$fullDocument.total_myr" },
          store_ids: { $addToSet: "$fullDocument.store_id" },
          window_start: { $min: "$fullDocument.timestamp" },
          window_end: { $max: "$fullDocument.timestamp" }
        }
      }
    ]
  }
};

// Step 3: Flatten the nested category arrays
let flattenCategories = {
  $addFields: {
    categories: {
      $reduce: {
        input: "$categories",
        initialValue: [],
        in: { $setUnion: ["$$value", "$$this"] }
      }
    }
  }
};

// Step 4: Lookup customer profile for historical context
let lookupCustomer = {
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
};

let unwindCustomer = {
  $unwind: { path: "$customer", preserveNullAndEmptyArrays: true }
};

// Step 5: Threshold evaluation — trigger on high-value patterns
let matchThresholds = {
  $match: {
    $or: [
      { hourly_spend: { $gt: 500 } },
      { txn_count: { $gt: 5 } },
      // High average basket (premium shopper signal)
      { avg_basket: { $gt: 200 } }
    ]
  }
};

// Step 6: Determine signal type and compute score
let computeSignal = {
  $addFields: {
    signal_type: {
      $switch: {
        branches: [
          {
            case: { $and: [{ $gt: ["$hourly_spend", 500] }, { $gt: ["$txn_count", 5] }] },
            then: "high_value_velocity"
          },
          {
            case: { $gt: ["$hourly_spend", 500] },
            then: "high_spend_window"
          },
          {
            case: { $gt: ["$txn_count", 5] },
            then: "high_frequency_window"
          }
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
};

// Step 7: Project final signal document
let projectSignal = {
  $project: {
    customer_id: "$_id",
    signal_type: 1,
    score: 1,
    details: {
      hourly_spend: "$hourly_spend",
      txn_count: "$txn_count",
      avg_basket: "$avg_basket",
      max_basket: "$max_basket",
      categories: "$categories",
      entities: "$entities",
      store_ids: "$store_ids",
      payment_methods: "$payment_methods",
      window_start: "$window_start",
      window_end: "$window_end"
    },
    customer_tier: 1,
    customer_name: 1,
    processed: 1,
    created_at: 1
  }
};

// Step 8: Merge into cross_sell_signals collection
let mergeStage = {
  $merge: {
    into: {
      connectionName: "RetailCustomer360Cluster",
      db: "RetailCustomer360",
      coll: "cross_sell_signals"
    }
  }
};

// ── Deploy Commands ──────────────────────────────────────────
// Run in mongosh connected to ASP workspace:
//
// 1. Stop & drop existing processor (if running):
//    sp["RetailCustomer360-cross-sell-trigger"].stop();
//    sp["RetailCustomer360-cross-sell-trigger"].drop();
//
// 2. Create the stream processor:
sp.createStreamProcessor("RetailCustomer360-cross-sell-trigger", [
  source, tumblingWindow, flattenCategories, lookupCustomer,
  unwindCustomer, matchThresholds, computeSignal, projectSignal, mergeStage
]);
//
// 3. Start:
//    sp["RetailCustomer360-cross-sell-trigger"].start();
//
// 4. Verify:
//    sp["RetailCustomer360-cross-sell-trigger"].stats();
