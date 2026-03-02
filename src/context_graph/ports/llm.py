"""LLM client port interface.

Source: ADR-0009, ADR-0013
"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    """Protocol for LLM text generation (litellm implementation)."""

    async def generate_text(self, prompt: str) -> str | None:
        """Generate text from a prompt. Returns None on failure."""
        ...
