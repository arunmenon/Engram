"""Start the operator workbench backend locally; optional dedicated Spanner sandbox allowlist.

Usage: ENGRAM_WORKBENCH_TOKEN=... python scripts/engram_workbench_dev.py
Use --fixture-author only for synthetic UI tests; the UI clearly labels the author.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import uvicorn

from context_graph.workbench.api import create_app
from context_graph.workbench.models import Proposal
from context_graph.workbench.pool_config import configured_execution


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-author", action="store_true")
    parser.add_argument(
        "--spanner-pool", type=Path, help="Server-owned registered sandbox allowlist JSON"
    )
    args = parser.parse_args()
    execution = configured_execution(args.spanner_pool) if args.spanner_pool else None
    if args.fixture_author:
        fixture = Path(__file__).resolve().parents[1] / "tests/fixtures/workbench/incident.json"
        proposal = json.loads(fixture.read_text())["proposal"]

        async def fixture_author(content):
            result = Proposal.model_validate(proposal)
            for fact in result.facts:
                for citation in fact.citations:
                    source = next((s for s in content.sources if citation.quote in s.text), None)
                    if source is not None:
                        citation.source_id = source.id
            return result

        app = create_app(
            author=fixture_author, model_label="TEST FIXTURE — no model calls", execution=execution
        )
    else:
        app = create_app(execution=execution)
    uvicorn.run(app, host="127.0.0.1", port=8101, access_log=False)


if __name__ == "__main__":
    main()
