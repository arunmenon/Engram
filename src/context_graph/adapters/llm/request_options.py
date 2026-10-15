"""Chat request options for the configured model."""

from typing import Any


def chat_options(model_id: str, temperature: float, max_tokens: int) -> dict[str, Any]:
    """Use Luna without reasoning; retain legacy provider options for overrides."""
    if model_id.removeprefix("openai/").startswith("gpt-6-luna"):
        return {"reasoning_effort": "none", "max_completion_tokens": max_tokens}
    return {"temperature": temperature, "max_tokens": max_tokens}
