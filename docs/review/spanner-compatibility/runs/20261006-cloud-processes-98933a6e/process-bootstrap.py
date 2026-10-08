"""Test-only token/provider bootstrap around ordinary Engram process entry points."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

from engram_spanner_compat import load_credentials
from google.cloud import spanner
from google.oauth2.credentials import Credentials


class ScriptedProvider:
    def __init__(self, **kwargs):
        pass

    async def extract_from_session(self, **kwargs):
        return {
            "persona": {"name": "Process User", "tech_level": "advanced"},
            "entities": [{"name": "Spanner", "entity_type": "technology"}],
            "preferences": [],
            "skills": [{"skill_id": "skill:process-python", "name": "Python"}],
            "interests": [],
        }

    async def generate_text(self, prompt):
        return '{"links": []}'

    async def verify_entailment(self, **kwargs):
        return True


def main():
    values = load_credentials(Path(os.environ["ENGRAM_COMPAT_CREDENTIAL_FILE"]))
    original = spanner.Client
    credentials = Credentials(token=values["GOOGLE_OAUTH_ACCESS_TOKEN"])

    def authenticated_client(*args, **kwargs):
        kwargs["credentials"] = credentials
        return original(*args, **kwargs)

    spanner.Client = authenticated_client
    import context_graph.adapters.llm.client as llm

    llm.LLMExtractionClient = ScriptedProvider
    mode = os.environ["ENGRAM_COMPAT_PROCESS"]
    if mode == "api":
        import uvicorn

        uvicorn.run(
            "context_graph.api.app:create_app",
            factory=True,
            host="127.0.0.1",
            port=int(os.environ["ENGRAM_COMPAT_API_PORT"]),
            log_level="warning",
        )
    else:
        from context_graph.worker.__main__ import run_worker

        asyncio.run(run_worker(mode))


if __name__ == "__main__":
    main()
