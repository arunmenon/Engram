"""HyDE query expansion for semantic retrieval (L6).

Hypothetical Document Embeddings (HyDE) generates a hypothetical answer
to the query using an LLM, then embeds that answer instead of the raw
query for better semantic retrieval.

Pure Python -- ZERO framework imports.
"""

from __future__ import annotations


def build_hyde_prompt(query: str) -> str:
    """Build a prompt that asks the LLM to generate a hypothetical document.

    The prompt instructs the LLM to write a short passage that would be
    a good answer to the query, as if it were a passage from a knowledge base.
    """
    return (
        "Given the following query, write a short passage (2-3 sentences) "
        "that would be a relevant answer found in a knowledge base. "
        "Do not include any preamble or explanation, just write the passage.\n\n"
        f"Query: {query}\n\n"
        "Passage:"
    )


def combine_query_with_hyde(original_query: str, hypothetical_doc: str) -> str:
    """Combine the original query with the hypothetical document for embedding.

    The combined text gives the embedding model both the query intent
    and the hypothetical answer context.
    """
    if not hypothetical_doc or not hypothetical_doc.strip():
        return original_query
    return f"{original_query}\n\n{hypothetical_doc.strip()}"


def expand_query(
    query: str,
    hypothetical_doc: str | None = None,
) -> str:
    """Return expanded query text for embedding.

    If a hypothetical document is provided, combines it with the query.
    Otherwise returns the original query unchanged.
    """
    if hypothetical_doc is None:
        return query
    return combine_query_with_hyde(query, hypothetical_doc)
