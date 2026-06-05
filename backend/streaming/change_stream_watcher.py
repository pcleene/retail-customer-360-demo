"""Change stream watcher -- monitors cross_sell_signals for new inserts and triggers
the cross-sell LangGraph agent for real-time recommendations.

Uses PyMongo AsyncMongoClient's watch() method for async change stream iteration.
Broadcasts real-time events to connected SSE clients.
Includes two-tier debouncing to avoid duplicate investigations for the same customer.
"""

import asyncio
import logging
from datetime import datetime, timezone

from pymongo.asynchronous.database import AsyncDatabase

logger = logging.getLogger(__name__)


class CrossSellSignalWatcher:
    """Watches cross_sell_signals for new inserts, triggers cross-sell agent, broadcasts via SSE."""

    def __init__(self, db: AsyncDatabase):
        self.db = db
        self._task: asyncio.Task | None = None
        self._subscribers: list[asyncio.Queue] = []
        # Two-tier debouncing
        self._active_investigations: set[str] = set()          # Tier 1: currently running
        self._recent_investigations: dict[str, datetime] = {}  # Tier 2: cooldown tracker
        self._cooldown_seconds: int = 120

    # ── SSE Subscription ────────────────────────────────────────

    def subscribe(self) -> asyncio.Queue:
        """Create a new SSE subscriber queue."""
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        logger.info("SSE subscriber added (total: %d)", len(self._subscribers))
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        """Remove an SSE subscriber queue."""
        if queue in self._subscribers:
            self._subscribers.remove(queue)
            logger.info("SSE subscriber removed (total: %d)", len(self._subscribers))

    async def _broadcast(self, event_type: str, data: dict):
        """Broadcast an SSE event to all subscribers."""
        message = {"event": event_type, "data": data}
        dead_queues = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for q in dead_queues:
            self._subscribers.remove(q)

    # ── Debouncing ──────────────────────────────────────────────

    def _should_investigate(self, customer_id: str) -> bool:
        """Check if investigation should proceed (two-tier debounce logic).

        Tier 1: Skip if there's an active (in-progress) investigation for this customer.
        Tier 2: Skip if a completed investigation is within the cooldown window.
        """
        # Tier 1: active investigation check
        if customer_id in self._active_investigations:
            logger.info(
                "Skipping cross-sell for %s -- already in progress", customer_id
            )
            return False

        # Tier 2: cooldown check
        last = self._recent_investigations.get(customer_id)
        if last:
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            if elapsed < self._cooldown_seconds:
                logger.info(
                    "Skipping cross-sell for %s -- cooldown (%ds remaining)",
                    customer_id,
                    int(self._cooldown_seconds - elapsed),
                )
                return False

        return True

    # ── Cross-Sell Agent Invocation ─────────────────────────────

    async def _run_crosssell(self, customer_id: str, signal: dict):
        """Run the cross-sell LangGraph agent and broadcast progress via SSE.

        Includes retry with exponential backoff on failure.
        """
        self._active_investigations.add(customer_id)
        max_retries = 3
        base_delay = 2.0

        try:
            await self._broadcast("crosssell_status", {
                "customerId": customer_id,
                "signalType": signal.get("signal_type"),
                "status": "started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            logger.info(
                "Starting cross-sell agent for %s (signal: %s, score: %.3f)",
                customer_id,
                signal.get("signal_type"),
                signal.get("score", 0),
            )

            # Import the graph builder (lazy import to avoid circular deps)
            from backend.agents.crosssell.graph import build_crosssell_graph

            graph = build_crosssell_graph()

            initial_state = {
                "customer_id": customer_id,
                "queries_executed": [],
            }

            result = None

            for attempt in range(1, max_retries + 1):
                try:
                    # Try streaming first for SSE progress updates
                    try:
                        async for event in graph.astream_events(
                            initial_state, version="v2"
                        ):
                            if event["event"] == "on_chain_start" and event.get("name"):
                                await self._broadcast("crosssell_status", {
                                    "customerId": customer_id,
                                    "status": "in_progress",
                                    "stage": event["name"],
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                })
                            if event["event"] == "on_chain_end" and event.get("name") == "execute_actions":
                                result = event.get("data", {}).get("output", {})
                    except Exception:
                        logger.info(
                            "astream_events not available (attempt %d), falling back to ainvoke",
                            attempt,
                        )
                        result = None

                    if result is None:
                        result = await graph.ainvoke(initial_state)

                    # Success -- break out of retry loop
                    break

                except Exception as e:
                    if attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1))
                        logger.warning(
                            "Cross-sell attempt %d/%d failed for %s (retry in %.1fs): %s",
                            attempt, max_retries, customer_id, delay, e,
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise

            # Broadcast completion
            crosssell_result = {
                "customerId": customer_id,
                "signalType": signal.get("signal_type"),
                "status": "completed",
                "recommendation": result.get("recommendation") if result else None,
                "enrolled": result.get("enrolled", False) if result else False,
                "queriesExecuted": result.get("queries_executed", []) if result else [],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            await self._broadcast("crosssell_complete", crosssell_result)

            # Mark signal as processed in the collection
            try:
                await self.db["cross_sell_signals"].update_one(
                    {"_id": signal.get("_id")},
                    {"$set": {"processed": True, "processed_at": datetime.now(timezone.utc)}},
                )
            except Exception as e:
                logger.warning("Failed to mark signal as processed: %s", e)

            self._recent_investigations[customer_id] = datetime.now(timezone.utc)
            logger.info("Cross-sell completed for customer %s", customer_id)

        except Exception as e:
            logger.exception("Cross-sell agent failed for customer %s", customer_id)
            await self._broadcast("crosssell_status", {
                "customerId": customer_id,
                "signalType": signal.get("signal_type"),
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
        finally:
            self._active_investigations.discard(customer_id)

    # ── Watch Loop ──────────────────────────────────────────────

    async def _watch_loop(self):
        """Main loop: watch cross_sell_signals for inserts and trigger agent."""
        logger.info("Change stream watcher started on cross_sell_signals")

        while True:
            try:
                pipeline = [{"$match": {"operationType": "insert"}}]
                async with self.db["cross_sell_signals"].watch(
                    pipeline, full_document="updateLookup"
                ) as stream:
                    async for change in stream:
                        doc = change.get("fullDocument", {})
                        customer_id = doc.get("customer_id")
                        signal_type = doc.get("signal_type", "unknown")
                        score = doc.get("score", 0)

                        if not customer_id:
                            logger.warning("Change stream: signal without customer_id, skipping")
                            continue

                        logger.info(
                            "Change stream: new cross-sell signal type=%s customer=%s score=%.3f",
                            signal_type, customer_id, score,
                        )

                        # Broadcast the raw signal immediately to SSE clients
                        signal_data = {k: v for k, v in doc.items() if k != "_id"}
                        for k, v in signal_data.items():
                            if hasattr(v, "isoformat"):
                                signal_data[k] = v.isoformat()
                        await self._broadcast("new_signal", signal_data)

                        # Check debounce and fire cross-sell agent
                        if self._should_investigate(customer_id):
                            asyncio.create_task(
                                self._run_crosssell(customer_id, doc)
                            )

            except Exception as e:
                logger.error(
                    "Change stream error (will retry in 5s): %s", e
                )
                await asyncio.sleep(5)

    # ── Lifecycle ───────────────────────────────────────────────

    def start(self):
        """Start the watcher as a background asyncio task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._watch_loop())
            logger.info("CrossSellSignalWatcher background task created")

    async def stop(self):
        """Stop the watcher gracefully."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            logger.info("CrossSellSignalWatcher stopped")


# ── Module-level singleton ──────────────────────────────────

_watcher: CrossSellSignalWatcher | None = None


def get_watcher() -> CrossSellSignalWatcher:
    """Get the singleton watcher instance. Raises if not initialised."""
    assert _watcher is not None, "Watcher not initialised -- call init_watcher() first"
    return _watcher


def init_watcher(db: AsyncDatabase) -> CrossSellSignalWatcher:
    """Initialise the singleton watcher with a database handle."""
    global _watcher
    _watcher = CrossSellSignalWatcher(db)
    return _watcher
