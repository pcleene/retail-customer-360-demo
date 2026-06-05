// ============================================================
// Event Ingestion Passthrough Stream Processor
// Pipes raw Kafka transaction events into RetailCustomer360.transactions
// with validation and an _ingestedAt timestamp.
//
// Windowless — no aggregation. Every valid event from the
// RetailCustomer360.transactions topic is written as-is after field
// validation.
// ============================================================

// Step 1: Source from Kafka (windowless — no timeField needed)
let source = {
  $source: {
    connectionName: "RetailCustomer360KafkaConnection",
    topic: "RetailCustomer360.transactions"
  }
};

// Step 2: Validate required fields — reject events missing essentials
let validateFields = {
  $match: {
    "fullDocument.transaction_id": { $exists: true },
    "fullDocument.customer_id": { $exists: true },
    "fullDocument.store_id": { $exists: true },
    "fullDocument.items": { $exists: true },
    "fullDocument.total_myr": { $exists: true },
    "fullDocument.timestamp": { $exists: true }
  }
};

// Step 3: Extract the fullDocument and add ingestion metadata
let reshapeFields = {
  $replaceRoot: { newRoot: "$fullDocument" }
};

let addIngestionFields = {
  $addFields: {
    _ingestedAt: { $toDate: "$_ts" },
    _source: "kafka_asp"
  }
};

// Step 4: Write to transactions collection
let mergeStage = {
  $merge: {
    into: {
      connectionName: "RetailCustomer360Cluster",
      db: "RetailCustomer360",
      coll: "transactions"
    }
  }
};

// ── Deploy Commands ──────────────────────────────────────────
// Run in mongosh connected to ASP workspace:
//
// 1. Stop & drop existing processor (if running):
//    sp["RetailCustomer360-event-ingest"].stop();
//    sp["RetailCustomer360-event-ingest"].drop();
//
// 2. Create the stream processor:
sp.createStreamProcessor("RetailCustomer360-event-ingest", [
  source, validateFields, reshapeFields, addIngestionFields, mergeStage
]);
//
// 3. Start:
//    sp["RetailCustomer360-event-ingest"].start();
//
// 4. Verify:
//    sp["RetailCustomer360-event-ingest"].stats();
