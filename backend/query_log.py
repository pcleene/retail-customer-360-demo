"""Per-request query logging for the Query Inspector.

Uses contextvars to maintain a per-request list of executed MongoDB queries.
Embeddings are truncated to 3 values + dimension count for readability.
"""

from contextvars import ContextVar
import copy
import time

_queries: ContextVar[list | None] = ContextVar("_queries", default=None)


def reset_log() -> None:
    _queries.set([])


def _truncate_embeddings(obj, max_items: int = 3):
    """Recursively replace long float arrays with a truncated preview."""
    if isinstance(obj, dict):
        return {k: _truncate_embeddings(v, max_items) for k, v in obj.items()}
    if isinstance(obj, list):
        if (
            len(obj) > max_items
            and all(isinstance(x, (int, float)) for x in obj[: max_items + 1])
        ):
            rounded = [round(x, 4) if isinstance(x, float) else x for x in obj[:max_items]]
            return rounded + [f"...{len(obj)} dims"]
        return [_truncate_embeddings(item, max_items) for item in obj]
    return obj


def _truncate_result(obj, max_keys: int = 60, max_array: int = 2, depth: int = 0):
    """Produce a compact preview of a result document for the inspector.

    Keeps the full schema structure but truncates large arrays and deep values.
    """
    if depth > 6:
        return "..."
    if isinstance(obj, dict):
        out = {}
        for i, (k, v) in enumerate(obj.items()):
            if i >= max_keys:
                out[f"...+{len(obj) - max_keys} keys"] = "..."
                break
            out[k] = _truncate_result(v, max_keys, max_array, depth + 1)
        return out
    if isinstance(obj, list):
        if len(obj) == 0:
            return []
        if len(obj) <= max_array:
            return [_truncate_result(item, max_keys, max_array, depth + 1) for item in obj]
        preview = [_truncate_result(item, max_keys, max_array, depth + 1) for item in obj[:max_array]]
        preview.append(f"...+{len(obj) - max_array} more")
        return preview
    if isinstance(obj, float):
        return round(obj, 2)
    if isinstance(obj, str) and len(obj) > 120:
        return obj[:120] + "..."
    return obj


def log_query(
    collection: str,
    operation: str,
    args,
    duration_ms: float = 0,
    result=None,
) -> None:
    """Log a MongoDB operation with optional result preview.

    Args:
        collection:  e.g. "customers"
        operation:   e.g. "aggregate", "find_one", "find", "count_documents"
        args:        pipeline list, filter dict, or other arguments
        duration_ms: wall-clock time in milliseconds
        result:      optional result document(s) for the inspector preview
    """
    log = _queries.get()
    if log is None:
        return
    safe_args = _truncate_embeddings(copy.deepcopy(args))
    entry: dict = {
        "collection": collection,
        "operation": operation,
        "args": safe_args,
        "duration_ms": round(duration_ms, 1),
        "ts": time.time(),
    }
    if result is not None:
        try:
            entry["result"] = _truncate_result(copy.deepcopy(result))
        except Exception:
            pass
    log.append(entry)


def get_log() -> list:
    return _queries.get() or []
