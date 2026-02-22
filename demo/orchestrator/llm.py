import os

from litellm import acompletion

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


async def chat_completion(messages: list[dict], model: str | None = None) -> str:
    model = model or os.getenv("DEMO_LLM_MODEL", DEFAULT_MODEL)
    response = await acompletion(model=model, messages=messages)
    return response.choices[0].message.content or ""
