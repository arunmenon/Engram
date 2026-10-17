"""Operator smoke proof through the deployed HTTP service and read-only storage audit.

No worker launch, direct artifact inserts, cleanup, model substitution or project
constants. This is a core Event/delivery proof, not a pack/model-quality suite.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from context_graph.deployment import Deployment, DeploymentError, check_binding, write_private_json


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        return None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeploymentError(message)


def request(
    base: str, token: str, path: str, body: dict[str, Any], *, hint: str | None = None
) -> tuple[int, dict[str, Any]]:
    headers = {"Authorization": "Bearer " + token, "Content-Type": "application/json"}
    if hint is not None:
        headers["X-Tenant-ID"] = hint
    req = Request(base + path, json.dumps(body).encode(), headers)
    try:
        with build_opener(_NoRedirect()).open(req, timeout=30) as response:
            return response.status, json.loads(response.read())
    except HTTPError as error:
        try:
            result = json.loads(error.read())
        except (ValueError, UnicodeError):
            result = {"detail": "Non-JSON HTTP error response"}
        return error.code, result


async def storage_proof(binding: Any, event: dict[str, Any], position: str) -> dict[str, Any]:
    """Inspect exact accepted ledger input and five independently advancing groups."""
    from context_graph.adapters.registry import open_stores
    from context_graph.worker.__main__ import CONSUMER_SUBSCRIPTIONS

    stores = await open_stores(binding.settings(), tenant_binding=binding)
    try:
        documents = await stores.event_log.get_documents([event["event_id"]])
        stored = documents[0]
        ledger_matches = (
            stored is not None
            and stored.get("global_position") == position
            and all(stored.get(k) == v for k, v in event.items() if k != "occurred_at")
        )
        if stored is not None:
            ledger_matches = ledger_matches and datetime.fromisoformat(
                str(stored["occurred_at"]).replace("Z", "+00:00")
            ) == datetime.fromisoformat(event["occurred_at"])
        settings = binding.settings()
        lags = {}
        for kind, (field, _) in CONSUMER_SUBSCRIPTIONS.items():
            group = getattr(settings.consumer, field)
            lags[group] = await stores.subscription(group, "deployment-audit-" + kind).lag()
        state = await asyncio.to_thread(check_binding, binding)
        ready = (
            ledger_matches
            and len(lags) == 5
            and all(v == 0 for v in lags.values())
            and (
                set(lags) <= set(state["registered_groups"])
                and state["pending"] == 0
                and state["dead_letters"] == 0
            )
        )
        return dict(ledger_matches=ledger_matches, lags=lags, delivery=state, ready=ready)
    finally:
        await stores.close()


def verify(
    deployment: Deployment,
    tenant: str,
    base: str,
    confirmed: str,
    output: Path,
    *,
    timeout: float = 120,
) -> None:
    parsed = urlsplit(base)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or (
            parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or parsed.path not in {"", "/"}
        )
    ):
        raise DeploymentError("Use an explicit HTTP(S) service origin, without credentials or path")
    binding = deployment.binding(tenant)
    if confirmed != binding.database_resource:
        raise DeploymentError("Confirmation does not match the selected database resource")
    if output.exists():
        raise DeploymentError("Evidence output exists; choose a fresh path")
    catalog = deployment.catalog()
    spec = next(
        (s for s in deployment.resolved.credentials if s.tenant_id == tenant and "api" in s.roles),
        None,
    )
    if spec is None:
        raise DeploymentError("Selected tenant requires an API producer credential")
    token = os.environ[spec.token_env]
    require(catalog.authenticate(token).tenant_id == tenant, "Credential tenant mismatch")
    eid = str(uuid4())
    event = dict(
        event_id=eid,
        event_type="observation.input",
        occurred_at=datetime.now(UTC).isoformat(),
        session_id="deployment-proof-" + eid,
        agent_id="deployment-proof",
        trace_id=eid,
        payload_ref="deployment-proof:" + eid,
        importance_hint=9,
        payload={"content": "Customer-owned storage probe " + eid},
    )
    report: dict[str, Any] = dict(
        state="running",
        database=binding.database_resource,
        runtime_sha256=deployment.resolved.runtime_sha256,
        bundle_digest=binding.bundle_digest,
        input=event,
        requests=[],
        scope="Core Event, enrichment, delivery, replay and refusal only",
    )

    def call(
        path: str, body: dict[str, Any], hint: str | None = None
    ) -> tuple[int, dict[str, Any]]:
        code, result = request(base.rstrip("/"), token, path, body, hint=hint)
        report["requests"].append(dict(path=path, status=code, output=result, tenant_hint=hint))
        return code, result

    try:
        report["before"] = check_binding(binding)
        # Use a dedicated, quiet proof target. A pre-existing DLQ is not silently allowed.
        if report["before"]["pending"] or report["before"]["dead_letters"]:
            raise DeploymentError("Proof requires no pre-existing pending or dead-letter work")
        code, receipt = call("/v1/events", event)
        require(code == 201 and receipt.get("status") == "created", "Event was not newly accepted")
        query = dict(
            query="Show this exact source",
            intent="what",
            seed_nodes=[eid],
            session_id=event["session_id"],
            agent_id=event["agent_id"],
            max_nodes=20,
        )
        end = time.monotonic() + timeout
        while True:
            code, answer = call("/v1/query/subgraph", query)
            node = answer.get("nodes", {}).get(eid, {})
            provenance = node.get("provenance") or {}
            public_ready = (
                code == 200
                and node.get("node_type") == "Event"
                and (
                    provenance.get("event_id") == eid
                    and provenance.get("source") == "spanner"
                    and provenance.get("global_position") == receipt["global_position"]
                    and node.get("attributes", {}).get("importance_score") == 9
                    and node.get("attributes", {}).get("keywords") == ["observation", "input"]
                )
            )
            report["storage"] = asyncio.run(
                storage_proof(binding, event, receipt["global_position"])
            )
            if public_ready and report["storage"]["ready"]:
                break
            if time.monotonic() >= end:
                raise DeploymentError("Readiness timed out; acceptance alone is not a pass")
            time.sleep(1)
        code, replay = call("/v1/events", event)
        require(code == 201 and replay.get("status") == "duplicate", "Replay was not a duplicate")
        require(
            replay.get("global_position") == receipt["global_position"], "Replay position changed"
        )
        changed = {**event, "payload": {"content": "conflicting source"}}
        code, _ = call("/v1/events", changed)
        require(code == 409, "Changed identity content was not refused")
        code, _ = call("/v1/events", changed, hint=tenant + "-wrong")
        require(code == 401, "Foreign tenant hint was not refused")
        report["after"] = asyncio.run(storage_proof(binding, event, receipt["global_position"]))
        require(
            report["after"]["ready"], "Replay/refusal changed the accepted source or delivery state"
        )
        report["state"] = "passed-core-deployment-proof"
    except BaseException as exc:
        report["state"] = "failed"
        report["error_type"] = type(exc).__name__
        raise
    finally:
        write_private_json(output, report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--tenant", required=True)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--confirm-database", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=float, default=120)
    args = parser.parse_args()
    if args.timeout_seconds <= 0:
        parser.error("Positive timeout required")
    try:
        verify(
            Deployment(args.config),
            args.tenant,
            args.base_url,
            args.confirm_database,
            args.output,
            timeout=args.timeout_seconds,
        )
    except Exception as exc:
        parser.exit(1, f"{type(exc).__name__}: proof failed; inspect the private evidence file\n")
    print("Core deployment proof passed; private evidence saved")


if __name__ == "__main__":
    main()
