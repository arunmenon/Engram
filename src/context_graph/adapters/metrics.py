"""Re-export shim for backwards compatibility.

Metrics have been relocated to context_graph.metrics (top-level shared module)
to avoid hex boundary violations when imported from api/ and worker/ layers.
"""

from context_graph.metrics import (  # noqa: F401
    CONSUMER_LAG,
    CONSUMER_MESSAGE_ERRORS,
    CONSUMER_MESSAGES_DEAD_LETTERED,
    CONSUMER_MESSAGES_PROCESSED,
    EVENTS_BATCH_SIZE,
    EVENTS_INGESTED_TOTAL,
    GRAPH_QUERY_DURATION,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    RATE_LIMIT_EXCEEDED,
)
