#!/usr/bin/env bash
# ============================================================
# Provision Google Cloud Managed Service for Apache Kafka
#
# Creates:
#   - Kafka cluster (default: RetailCustomer360-kafka)
#   - Topics: RetailCustomer360.transactions, RetailCustomer360.loyalty_events, RetailCustomer360.profile_changes
#
# Prerequisites:
#   - gcloud CLI installed and authenticated
#   - GCP project exists with billing enabled
#   - Managed Kafka API enabled (gcloud services enable managedkafka.googleapis.com)
#
# VPC Peering for Atlas Connectivity:
#   Atlas clusters in GCP require VPC peering to reach Managed Kafka.
#   1. In MongoDB Atlas: Network Access → Peering → Add Peering Connection
#      - Provider: GCP, Project: $GCP_PROJECT_ID
#      - Network name: default (or your VPC)
#   2. In GCP Console: VPC Network → Peering → Accept the Atlas peering request
#   3. Ensure firewall rules allow traffic on Kafka ports (9092, 9093)
#   4. Use the internal Kafka bootstrap address in ASP $source connectionName
#
# Usage:
#   chmod +x scripts/provision_kafka.sh
#   GCP_PROJECT_ID=my-project GCP_LOCATION=asia-southeast1 ./scripts/provision_kafka.sh
#   # or rely on values exported in your .env / shell
# ============================================================

set -euo pipefail

PROJECT="${GCP_PROJECT_ID:-${PROJECT:-}}"
REGION="${GCP_LOCATION:-${REGION:-asia-southeast1}}"
CLUSTER_NAME="${KAFKA_CLUSTER_NAME:-RetailCustomer360-kafka}"

if [[ -z "${PROJECT}" ]]; then
  echo "ERROR: GCP_PROJECT_ID is not set. Export it (or set PROJECT) before running." >&2
  exit 1
fi

# Topics to create
TOPICS=(
  "RetailCustomer360.transactions"
  "RetailCustomer360.loyalty_events"
  "RetailCustomer360.profile_changes"
)

# Topic configuration
PARTITION_COUNT=3
REPLICATION_FACTOR=3
RETENTION_MS=604800000  # 7 days

echo "=== Retail Customer 360 — Managed Kafka Provisioning ==="
echo "Project:  ${PROJECT}"
echo "Region:   ${REGION}"
echo "Cluster:  ${CLUSTER_NAME}"
echo ""

# ── Ensure correct project ──────────────────────────────────
gcloud config set project "${PROJECT}" --quiet

# ── Enable Managed Kafka API (idempotent) ───────────────────
echo "--- Enabling Managed Kafka API ---"
gcloud services enable managedkafka.googleapis.com --quiet 2>/dev/null || true
echo "  API enabled (or already enabled)"

# ── Create Cluster (idempotent) ─────────────────────────────
echo ""
echo "--- Checking Kafka cluster ---"
if gcloud managed-kafka clusters describe "${CLUSTER_NAME}" \
    --location="${REGION}" --quiet 2>/dev/null; then
  echo "  Cluster '${CLUSTER_NAME}' already exists — skipping creation"
else
  echo "  Creating cluster '${CLUSTER_NAME}'..."
  gcloud managed-kafka clusters create "${CLUSTER_NAME}" \
    --location="${REGION}" \
    --cpu=3 \
    --memory-bytes=3221225472 \
    --subnets="projects/${PROJECT}/regions/${REGION}/subnetworks/default" \
    --async \
    --quiet
  echo "  Cluster creation initiated (async — may take 15-20 minutes)"
  echo "  Monitor with: gcloud managed-kafka clusters describe ${CLUSTER_NAME} --location=${REGION}"

  echo ""
  echo "  Waiting for cluster to become ACTIVE..."
  gcloud managed-kafka clusters describe "${CLUSTER_NAME}" \
    --location="${REGION}" \
    --format="value(state)" 2>/dev/null || true
  echo "  (Run this script again after cluster is ACTIVE to create topics)"
fi

# ── Create Topics (idempotent) ──────────────────────────────
echo ""
echo "--- Creating topics ---"
for TOPIC in "${TOPICS[@]}"; do
  if gcloud managed-kafka topics describe "${TOPIC}" \
      --cluster="${CLUSTER_NAME}" \
      --location="${REGION}" --quiet 2>/dev/null; then
    echo "  Topic '${TOPIC}' already exists — skipping"
  else
    echo "  Creating topic '${TOPIC}'..."
    gcloud managed-kafka topics create "${TOPIC}" \
      --cluster="${CLUSTER_NAME}" \
      --location="${REGION}" \
      --partitions="${PARTITION_COUNT}" \
      --replication-factor="${REPLICATION_FACTOR}" \
      --configs="retention.ms=${RETENTION_MS}" \
      --quiet
    echo "  Created '${TOPIC}' (partitions=${PARTITION_COUNT}, retention=7d)"
  fi
done

# ── Verify ──────────────────────────────────────────────────
echo ""
echo "--- Listing topics ---"
gcloud managed-kafka topics list \
  --cluster="${CLUSTER_NAME}" \
  --location="${REGION}" \
  --format="table(name, partitionCount, replicationFactor)" 2>/dev/null || \
  echo "  (Cluster may still be provisioning — topics will be listed once ACTIVE)"

echo ""
echo "=== Provisioning complete ==="
echo ""
echo "Next steps:"
echo "  1. Wait for cluster ACTIVE state"
echo "  2. Set up VPC peering with MongoDB Atlas (see notes at top of script)"
echo "  3. Configure ASP Kafka connection in Atlas Stream Processing"
echo "  4. Get bootstrap servers: gcloud managed-kafka clusters describe ${CLUSTER_NAME} --location=${REGION} --format='value(bootstrapAddress)'"
echo "  5. Set KAFKA_BOOTSTRAP_SERVERS in .env"
