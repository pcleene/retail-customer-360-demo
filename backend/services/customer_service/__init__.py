"""Customer service — hybrid search, single-customer fetch, transactions.

Re-exports the public API so callers can keep importing from
``backend.services.customer_service``.
"""

from .search import search_customers_hybrid  # noqa: F401
from .profile import get_customer_by_id, get_customer_transactions  # noqa: F401
