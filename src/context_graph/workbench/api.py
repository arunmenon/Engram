"""Local operator control API. Run with uvicorn --factory, one worker.

Authentication is explicit and fail-closed. Operator records own separate drafts;
there is deliberately no endpoint that mutates live bindings or runtime stores.
"""

from __future__ import annotations

import asyncio
import copy
import fcntl
import json
import logging
import os
import secrets
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Literal

import yaml
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from context_graph.workbench.authoring import ModelAuthor, evidence, verify_proposal
from context_graph.workbench.catalog import entries, has_lifecycle
from context_graph.workbench.changes import pack_changes, pack_items, removed_items
from context_graph.workbench.decision_preview import preview_options
from context_graph.workbench.draft_stories import draft_story
from context_graph.workbench.engine import digest, engine_revision, validate
from context_graph.workbench.explain import (
    Explainer,
    ExplainRequest,
    ModelExplainer,
    context_for,
    verify_answer,
)
from context_graph.workbench.job_errors import job_failure_reason
from context_graph.workbench.journey_authoring import (
    JourneyBrief,
    JourneyGeneration,
    propose_journey,
    validate_variant,
)
from context_graph.workbench.journey_runner import run_journey
from context_graph.workbench.journeys import (
    RETRIEVAL_VARIANTS,
    Journey,
    fixture_journey,
    reference_journey,
    release_journey,
    retrieval_trust_journey,
    retrieval_variant_journey,
    source_coverage,
)
from context_graph.workbench.limits import IntakeLimits
from context_graph.workbench.models import Content, Proposal, Review, Revision, Save, StoryReview
from context_graph.workbench.sandbox import evaluation_artifact, run_sandbox
from context_graph.workbench.store import ConflictError, Store
from context_graph.workbench.story_inspection import inspect_story, result_stale

if TYPE_CHECKING:
    from context_graph.workbench.execution import SpannerExecution

Author = Callable[[Content], Awaitable[Proposal]]


def readiness(record: dict[str, Any]) -> dict[str, Any]:
    if record.get("journey"):
        running = (record.get("job") or {}).get("status") == "running"
        reviewed = record["journey"].get("expectations_reviewed", False)
        return {
            "begin": {"ready": True, "missing": []},
            "run": {
                "ready": not running and reviewed,
                "missing": (["Wait for the current run"] if running else [])
                + ([] if reviewed else ["Generate and review story expectations before running"]),
            },
            "approve": {
                "ready": False,
                "missing": ["Prepared journeys are test workspaces, not activation artifacts"],
            },
        }
    c = Content.model_validate(record["content"])
    begin = []
    if c.data_policy == "undecided" or not c.redaction_confirmed:
        begin.append("Review data handling and redaction")
    if not c.scope.strip():
        begin.append("Describe the domain scope")
    if not c.sources:
        begin.append("Add a specification, schema or sample events")
    run = list(begin)
    if (record.get("job") or {}).get("status") == "running":
        run.append("Wait for the current job or cancel it")
    kinds = {source.kind for source in c.sources}
    for kind in ("schema", "samples"):
        if kind not in kinds:
            run.append(f"Add {kind} evidence")
    if record.get("proposal_stale"):
        run.append("Regenerate the proposal after input changes")
    if record.get("pending_decisions"):
        run.append("Apply your pending answers with the assistant")
    proposal = record.get("proposal")
    review = record.get("review") or {}
    if review.get("rejected_facts"):
        run.append("Revise the pack to address rejected proposals")
    if not proposal or not proposal.get("pack"):
        run.append("Generate an executable pack proposal")
    if proposal:
        if set(review.get("accepted_removals", [])) != set(proposal.get("repair_removals", [])):
            run.append("Review the data removed by the assistant before accepting this pack")
        for decision in proposal["decisions"]:
            if not c.decisions.get(decision["id"]):
                run.append(f"Resolve: {decision['question']}")
        if set(review.get("accepted_facts", [])) != {f["id"] for f in proposal["facts"]}:
            run.append("Review each proposed fact or inference")
    for key in (
        ["identity", "lifecycle"] if has_lifecycle((proposal or {}).get("pack")) else ["identity"]
    ):
        if not c.decisions.get(key) and key not in review.get("confirmed_policies", []):
            run.append(f"Record the {key} policy")
    if set(review.get("accepted_changes", [])) != {
        change["id"] for change in record.get("proposal_changes", [])
    }:
        run.append("Acknowledge the changes from the previous pack")
    if not review.get("pack_accepted"):
        run.append("Accept the proposed pack")
    if not (record.get("validation") or {}).get("passed"):
        run.append("Pass engine composition and sample admission validation")
    if not c.questions or not all(q.reviewed for q in c.questions):
        run.append("Review questions and expected answers")
    if any(
        q.expectation_statement is not None and not q.expectation_statement.strip()
        for q in c.questions
    ):
        run.append("Record the business expectation before reviewing generated answer candidates")
    if not c.graph_reviewed or not c.expected_nodes:
        run.append("Review expected graph nodes before execution")
    if not c.trust_reviewed:
        run.append("Review sandbox producer trust (untrusted is an explicit choice)")
    approve = list(run)
    if not (record.get("sandbox") or {}).get("passed"):
        approve.append("Pass the current revision's sandbox checks")
    return {
        "begin": {"ready": not begin, "missing": begin},
        "run": {"ready": not run, "missing": run},
        "approve": {"ready": not approve, "missing": approve},
    }


def create_app(
    *,
    database: Path | None = None,
    operators: dict[str, str] | None = None,
    author: Author | None = None,
    model_label: str | None = None,
    execution: SpannerExecution | None = None,
    explainer: Explainer | None = None,
    explain_timeout: float = 30,
) -> FastAPI:
    if operators is None:
        key = os.environ.get("ENGRAM_WORKBENCH_TOKEN", "")
        if len(key) < 24:
            raise RuntimeError(
                "Set ENGRAM_WORKBENCH_TOKEN to a random token of at least 24 characters"
            )
        operators = {key: "local-operator"}
    if not operators or any(not key or not owner for key, owner in operators.items()):
        raise ValueError("Explicit operator credentials are required")
    store = Store(
        database or Path(os.environ.get("ENGRAM_WORKBENCH_DB", ".workbench/drafts.sqlite3"))
    )
    revision_identity = engine_revision()
    model = model_label or os.environ.get("ENGRAM_WORKBENCH_MODEL")
    if author is None and model:
        author = ModelAuthor(model)
    if explainer is None and model:
        explainer = ModelExplainer(model)
    explaining: set[str] = set()
    active: dict[str, asyncio.Task[None]] = {}

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # One local job runner owns this control store; do not run multiple workers.
        with store.path.with_suffix(".lock").open("a") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise RuntimeError("Workbench store is already served by another process") from exc
            store.recover_jobs()

            async def recover_pool() -> None:
                while execution is not None:
                    await execution.recover()
                    await asyncio.sleep(30)

            recovery_task = asyncio.create_task(recover_pool()) if execution is not None else None
            try:
                yield
            finally:
                tasks = list(active.values())
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                if recovery_task is not None:
                    recovery_task.cancel()
                    await asyncio.gather(recovery_task, return_exceptions=True)
                if execution is not None:
                    await execution.close()
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)

    app = FastAPI(
        title="Engram operator workbench", docs_url=None, redoc_url=None, lifespan=lifespan
    )

    app.add_middleware(IntakeLimits)

    async def authenticate(authorization: Annotated[str | None, Header()] = None) -> str:
        token = (authorization or "").removeprefix("Bearer ")
        for credential, owner in operators.items():
            if (
                authorization
                and authorization.startswith("Bearer ")
                and secrets.compare_digest(token, credential)
            ):
                return owner
        raise HTTPException(401, "An operator credential is required")

    @app.exception_handler(ConflictError)
    async def conflict(_request: Any, exc: ConflictError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, status_code=409)

    def get(
        owner: str, draft_id: str, revision: int | None = None, *, allow_running: bool = False
    ) -> dict[str, Any]:
        record = store.get(owner, draft_id)
        if record is None:
            raise HTTPException(404, "Draft not found")
        if revision is not None and record["revision"] != revision:
            raise HTTPException(409, "Draft changed. Reload before continuing.")
        if (
            revision is not None
            and execution is not None
            and draft_id in active
            and (record.get("job") or {}).get("kind") in {"sandbox", "journey"}
            and not allow_running
        ):
            raise HTTPException(
                409, "Cancel the sandbox and wait for cleanup before changing this draft"
            )
        return record

    def view(record: dict[str, Any]) -> dict[str, Any]:
        task = active.get(record["id"])
        if task and task.cancelling() and record.get("job"):
            record["job"]["cancelling"] = True
        record["readiness"] = readiness(record)
        if record.get("journey"):
            record["journey_coverage"] = source_coverage(record["journey"])
        recorded = (record.get("validation") or {}).get("engine_revision")
        if record.get("validation") and recorded != revision_identity:
            for tier in ("run", "approve"):
                record["readiness"][tier]["ready"] = False
                record["readiness"][tier]["missing"].append("Revalidate after the engine changed")
        if record.get("journey_result"):
            record["journey_result_stale"] = result_stale(record)
        if record.get("journey"):
            record["story_inspection"] = inspect_story(record)
        record["runtime"] = {
            "activation": "not_requested",
            "intents": "not_evaluated",
            "reason": "This workbench does not activate live tenant configuration.",
        }
        return record

    def put(owner: str, record: dict[str, Any], revision: int, action: str) -> dict[str, Any]:
        record.pop("readiness", None)
        record.pop("runtime", None)
        return view(store.put(owner, jsonable_encoder(record), revision, action))

    @app.get("/admin/capabilities")
    async def capabilities(owner: str = Depends(authenticate)) -> dict[str, Any]:
        catalog = entries()
        return {
            "operator": owner,
            "authoring": author is not None,
            "explaining": explainer is not None,
            "model": model,
            "roots": ["core", "memory", "user"],
            "packs": [entry["name"] for entry in catalog],
            "pack_catalog": catalog,
            "sandbox": "spanner" if execution is not None else "isolated-memory",
            "activation": False,
            "engine_revision": revision_identity,
        }

    @app.post("/admin/tenants/{draft_id}/explain")
    async def explain_problem(
        draft_id: str, body: ExplainRequest, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        content = Content.model_validate(record["content"])
        if content.data_policy != "provider_allowed" or not content.redaction_confirmed:
            raise HTTPException(
                403, "Allow provider use and confirm redaction before asking the agent"
            )
        if (
            record.get("proposal_stale")
            and not record.get("explain_stale_allowed")
            and body.scope != "author_error"
        ) or (record.get("job") or {}).get("status") == "running":
            raise HTTPException(409, "Wait for a current proposal before asking about it")
        if explainer is None:
            raise HTTPException(503, "The explanation agent is not configured")
        try:
            context = context_for(record, body)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if draft_id in explaining or len(explaining) >= 2:
            raise HTTPException(
                429, "Explanation capacity is busy; try again shortly", headers={"Retry-After": "2"}
            )

        def explanation_basis(r: dict[str, Any]) -> str:
            return digest(
                [
                    r.get("proposal"),
                    r.get("journey"),
                    r.get("journey_result"),
                    r.get("journey_pack_snapshot"),
                ]
            )

        bound_digest = explanation_basis(record)
        proposal_digest = digest(record.get("proposal"))
        explaining.add(draft_id)
        preview_task = None
        try:
            async with asyncio.timeout(explain_timeout):
                for attempt in range(2):
                    raw = await explainer(copy.deepcopy(context))
                    try:
                        answer = verify_answer(raw, context)
                        break
                    except ValueError:
                        if attempt:
                            raise HTTPException(
                                502, "The agent could not ground an answer. Your pack is unchanged."
                            ) from None
                preview_task = asyncio.create_task(
                    asyncio.to_thread(preview_options, copy.deepcopy(record), answer.options)
                )
                option_previews = await asyncio.shield(preview_task)
                current = get(owner, draft_id, body.revision)
                if explanation_basis(current) != bound_digest:
                    raise HTTPException(409, "The proposal changed; ask again")
                return {
                    "draft_id": draft_id,
                    "revision": body.revision,
                    "proposal_digest": proposal_digest,
                    "scope": body.scope,
                    "index": body.index,
                    "answer": answer.model_dump(),
                    "option_previews": option_previews,
                    "evidence": context["evidence"],
                }
        except TimeoutError:
            raise HTTPException(504, "The explanation timed out. Your pack is unchanged.") from None
        except HTTPException:
            raise
        except Exception:
            logging.getLogger(__name__).warning("Explanation failed without changing draft state")
            raise HTTPException(
                502, "The agent could not finish. Your pack is unchanged."
            ) from None
        finally:
            if preview_task is not None and not preview_task.done():
                # Timeout stops waiting, not a running thread. Keep its capacity reserved.
                def release_preview(task: asyncio.Task[Any]) -> None:
                    explaining.discard(draft_id)
                    if not task.cancelled():
                        task.exception()  # Consume late failures without leaking draft details.

                preview_task.add_done_callback(release_preview)
            else:
                explaining.discard(draft_id)

    @app.get("/admin/sandbox-capacity")
    async def sandbox_capacity(owner: str = Depends(authenticate)) -> dict[str, Any]:
        if execution is None:
            return {"backend": "isolated-memory", "capacity": None, "available": None, "slots": []}
        return await asyncio.to_thread(execution.pool.status)

    @app.get("/admin/tenants")
    async def tenants(owner: str = Depends(authenticate)) -> list[dict[str, Any]]:
        return [view(record) for record in store.list(owner)]

    @app.post("/admin/journeys/{name}", status_code=201)
    async def prepare_journey(
        name: Literal[
            "implementation",
            "planning",
            "release",
            "references",
            "retrieval-trust",
            "review-verdict",
            "trust-corroboration",
            "version-precision",
            "number-precision",
            "rare-word",
            "paging-complete",
            "paging-proposed",
            "paging-truncated",
            "paging-traversal",
            "category-evaluation",
            "query-budget",
            "rejected-refinement",
        ],
        owner: str = Depends(authenticate),
    ) -> dict[str, Any]:
        if name == "retrieval-trust":
            journey = retrieval_trust_journey()
        elif name in RETRIEVAL_VARIANTS:
            journey = retrieval_variant_journey(name)
        elif name == "references":
            journey = reference_journey()
        elif name == "release":
            journey = release_journey()
        elif name in ("implementation", "planning"):
            journey = fixture_journey(name)
        else:
            raise HTTPException(422, "Unknown prepared journey")
        for existing in store.list(owner):
            if existing.get("journey") and digest(existing["journey"]) == digest(
                journey.model_dump()
            ):
                return view(existing)
        record = store.create(
            owner,
            Content(
                name=f"PDLC · {name} journey",
                environment="sandbox",
                scope=journey.story,
                data_policy="local_only",
            ).model_dump(),
        )
        record["journey"] = journey.model_dump()
        return put(owner, record, record["revision"], "journey_prepared")

    @app.post("/admin/tenants/{draft_id}/story-workspace", status_code=201)
    async def prepare_draft_story(
        draft_id: str, body: Revision, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if (record.get("job") or {}).get("status") == "running":
            raise HTTPException(409, "Wait for the current job")
        if (
            record.get("proposal_stale")
            or record.get("pending_decisions")
            or not (record.get("review") or {}).get("pack_accepted")
            or not (record.get("validation") or {}).get("passed")
        ):
            raise HTTPException(409, "Review and validate the current pack first")
        if record["validation"].get("engine_revision") != revision_identity:
            raise HTTPException(409, "Revalidate the pack against the current engine")
        content = Content.model_validate(record["content"])
        try:
            baseline, snapshot = draft_story(content, record["proposal"]["pack"])
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        created = store.create(
            owner,
            Content(
                name=baseline.title[:100],
                environment="sandbox",
                scope=baseline.story,
                data_policy="local_only",
            ).model_dump(),
        )
        created.update(
            journey=baseline.model_dump(),
            journey_pack_snapshot=snapshot,
            journey_pack_origin={"draft_id": draft_id, "revision": body.revision},
        )
        return put(owner, created, created["revision"], "draft_story_prepared")

    @app.post("/admin/tenants/{draft_id}/journey-outline", status_code=202)
    async def outline_journey(
        draft_id: str, body: JourneyBrief, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if not record.get("journey") or not model:
            raise HTTPException(409, "A prepared journey and configured model are required")
        if not body.provider_allowed:
            raise HTTPException(409, "Explicit provider permission is required for these inputs")
        record["journey_brief"] = body.model_dump(exclude={"revision"})
        record.pop("journey_outline", None)
        record.pop("journey_proposal", None)
        return launch(owner, record, "journey-outline")

    @app.post("/admin/tenants/{draft_id}/journey-generate", status_code=202)
    async def generate_journey(
        draft_id: str, body: JourneyGeneration, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if not model or not record.get("journey_outline") or not body.outline_reviewed:
            raise HTTPException(409, "Review an outline and resolve its assumptions first")
        if not (record.get("journey_brief") or {}).get("provider_allowed"):
            raise HTTPException(409, "Provider permission is required")
        record["journey_decisions"] = body.decisions
        record.pop("journey_proposal", None)
        return launch(owner, record, "journey-generate")

    @app.post("/admin/tenants/{draft_id}/journey-accept", status_code=201)
    async def accept_journey(
        draft_id: str, body: StoryReview, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if (record.get("job") or {}).get("status") == "running" or not record.get(
            "journey_proposal"
        ):
            raise HTTPException(409, "Wait for a valid generated journey before reviewing it")
        variant = Journey.model_validate(record["journey_proposal"])
        validate_variant(
            variant,
            Journey.model_validate(record["journey"]),
            **(
                {"pack_snapshot": record["journey_pack_snapshot"]}
                if record.get("journey_pack_snapshot")
                else {}
            ),
        )
        if set(body.accepted_checks) != {check.id for check in variant.checks}:
            raise HTTPException(409, "Review every generated check before accepting the story")
        variant.expectations_reviewed = True
        created = store.create(
            owner,
            Content(
                name=variant.title[:100],
                environment="sandbox",
                scope=variant.story,
                data_policy="local_only",
            ).model_dump(),
        )
        created.update(
            journey=variant.model_dump(),
            journey_pack_snapshot=record.get("journey_pack_snapshot"),
            journey_pack_origin=record.get("journey_pack_origin"),
            journey_origin={
                "parent": draft_id,
                "revision": body.revision,
                "brief": record["journey_brief"],
                "outline": record["journey_outline"],
                "decisions": record["journey_decisions"],
                "reviewer": owner,
            },
        )
        return put(owner, created, created["revision"], "journey_expectations_reviewed")

    @app.post("/admin/tenants/{draft_id}/journey-run", status_code=202)
    async def execute_journey(
        draft_id: str, body: Revision, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if not record.get("journey"):
            raise HTTPException(409, "No prepared journey in this workspace")
        if not record["journey"].get("expectations_reviewed"):
            raise HTTPException(409, "Review story expectations before execution")
        return launch(owner, record, "journey")

    @app.post("/admin/tenants", status_code=201)
    async def create(content: Content, owner: str = Depends(authenticate)) -> dict[str, Any]:
        return view(store.create(owner, content.model_dump()))

    @app.get("/admin/tenants/{draft_id}")
    async def detail(draft_id: str, owner: str = Depends(authenticate)) -> dict[str, Any]:
        return view(get(owner, draft_id))

    @app.put("/admin/tenants/{draft_id}")
    async def save(draft_id: str, body: Save, owner: str = Depends(authenticate)) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        try:
            evidence(body.content)
            for source in body.content.sources:
                if source.kind == "schema":
                    json.loads(source.text)
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc
        if draft_id in active:
            active[draft_id].cancel()
        # Keep acceptance independent of transient review flags (including legacy records).
        if (record.get("review") or {}).get("pack_accepted"):
            record["accepted_pack"] = copy.deepcopy((record.get("proposal") or {}).get("pack"))
        incoming = body.content.model_dump()
        old = record["content"]
        # A new instruction can invalidate its predecessor's provenance without
        # changing the saved evidence used to explain the retained proposal.
        normalized_old = Content.model_validate(old).model_dump()
        instruction_only_basis = all(
            normalized_old[key] == incoming[key] for key in incoming if key != "instruction"
        )
        explainable_before_save = not record.get("proposal_stale") or record.get(
            "explain_stale_allowed", False
        )
        if old["trusted_ids"] != incoming["trusted_ids"]:
            incoming["trust_reviewed"] = False
        if any(old[k] != incoming[k] for k in ("expected_nodes", "forbidden_nodes")):
            incoming["graph_reviewed"] = False
        old_questions = {q["id"]: q for q in old["questions"]}
        for question in incoming["questions"]:
            prior = old_questions.get(question["id"])
            if prior and any(prior.get(k) != question.get(k) for k in question if k != "reviewed"):
                question["reviewed"] = False
        body.content = Content.model_validate(incoming)
        provenance_changed = False
        if record.get("proposal"):
            try:
                verify_proposal(Proposal.model_validate(record["proposal"]), body.content)
            except ValueError:
                provenance_changed = True
        model_fields = ("scope", "roots", "existing_packs", "sources")
        model_changed = any(record["content"][key] != incoming[key] for key in model_fields)
        answers_changed = record["content"]["decisions"] != incoming["decisions"]
        same_sources = record["content"]["sources"] == incoming["sources"]
        record["authoring_context"] = proposal_context(record) if same_sources else None
        if record.get("sandbox"):
            record["previous_sandbox"] = {
                "revision": record["revision"],
                "result": record["sandbox"],
            }
        record.update(content=incoming, sandbox=None, approval=None, job=None)
        if answers_changed and record.get("proposal"):
            record.update(pending_decisions=True, review=None)
        if model_changed or provenance_changed:
            record.update(review=None, validation=None)
            record["proposal_stale"] = bool(record.get("proposal"))
        elif (
            record.get("proposal")
            and record["proposal"].get("pack")
            and not record.get("proposal_stale")
        ):
            # Choosing an oracle or source policy tests the existing model. It does not
            # require another provider call or erase the operator's model review.
            try:
                checks = await asyncio.to_thread(validate, body.content, record["proposal"]["pack"])
            except Exception as exc:
                checks = {"passed": False, "problems": [str(exc)[:4000]]}
            checks["engine_revision"] = revision_identity
            checks["input_digest"] = digest(incoming)
            record["validation"] = checks
        record["explain_stale_allowed"] = bool(
            record.get("proposal_stale") and instruction_only_basis and explainable_before_save
        )
        return put(owner, record, body.revision, "intake_updated")

    @app.get("/admin/tenants/{draft_id}/evidence")
    async def inspect_evidence(draft_id: str, owner: str = Depends(authenticate)) -> dict[str, Any]:
        try:
            return evidence(Content.model_validate(get(owner, draft_id)["content"]))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    async def finish_job(owner: str, record: dict[str, Any], kind: str) -> None:
        revision = record["revision"]

        def report_attempt(attempt: int) -> None:
            nonlocal revision
            record["job"]["attempt"] = attempt
            # The same optimistic revision fence as completion prevents a stale
            # worker from publishing progress after cancellation or replacement.
            store.put(owner, record, revision, "author_attempt_started")
            revision = record["revision"]

        def report_storage(evidence: dict[str, Any]) -> None:
            nonlocal revision
            record["storage_run"] = evidence
            store.put(owner, record, revision, "sandbox_" + evidence["phase"])
            revision = record["revision"]

        try:
            content = Content.model_validate(record["content"])
            async with asyncio.timeout(
                250
                if kind in {"author", "journey-outline", "journey-generate"}
                or execution is not None
                else 30
            ):
                if kind == "author":
                    assert author is not None
                    if isinstance(author, ModelAuthor):
                        proposal = await author(
                            content,
                            previous=record.get("authoring_context"),
                            on_attempt=report_attempt,
                        )
                    else:
                        proposal = await author(content)
                    verify_proposal(proposal, content)
                    prior_proposal = record.get("proposal") or {}
                    prior_pack = prior_proposal.get("pack")
                    proposal.repair_removals = sorted(
                        (
                            set(proposal.repair_removals)
                            | set(prior_proposal.get("repair_removals", []))
                            | set(removed_items(prior_pack, proposal.pack))
                        )
                        - pack_items(proposal.pack)
                    )
                    checks = None
                    if proposal.pack:
                        try:
                            checks = await asyncio.to_thread(validate, content, proposal.pack)
                        except Exception as exc:
                            checks = {"passed": False, "problems": [str(exc)[:4000]]}
                        checks["engine_revision"] = revision_identity
                        checks["input_digest"] = digest(record["content"])
                    baseline = record.get("accepted_pack") or (
                        prior_pack
                        if (record.get("review") or {}).get("pack_accepted")
                        else (record.get("proposal_change_base") or prior_pack)
                    )
                    changes = pack_changes(baseline, proposal.pack)
                    # Publish the replacement only after all awaited work finishes.
                    # Failure/cancellation must leave the previous proposal intact.
                    record.update(
                        proposal=proposal.model_dump(),
                        proposal_change_base=baseline,
                        proposal_changes=changes,
                        proposal_stale=False,
                        explain_stale_allowed=False,
                        pending_decisions=False,
                        review=None,
                        validation=checks,
                        sandbox=None,
                        approval=None,
                    )
                elif kind in {"journey-outline", "journey-generate"}:
                    assert model is not None
                    journey_proposal = await propose_journey(
                        model,
                        Journey.model_validate(record["journey"]),
                        record["journey_brief"],
                        record.get("journey_outline") if kind == "journey-generate" else None,
                        record.get("journey_decisions", ""),
                        **(
                            {"pack_snapshot": record["journey_pack_snapshot"]}
                            if record.get("journey_pack_snapshot")
                            else {}
                        ),
                    )
                    record[
                        "journey_proposal" if kind == "journey-generate" else "journey_outline"
                    ] = journey_proposal.model_dump()
                elif kind == "journey":
                    journey = Journey.model_validate(record["journey"])
                    record["journey_result"] = (
                        await run_journey(
                            journey,
                            execution=execution,
                            progress=report_storage,
                            **(
                                {"pack_snapshot": record["journey_pack_snapshot"]}
                                if record.get("journey_pack_snapshot")
                                else {}
                            ),
                        )
                        if execution is not None
                        else await run_journey(
                            journey,
                            **(
                                {"pack_snapshot": record["journey_pack_snapshot"]}
                                if record.get("journey_pack_snapshot")
                                else {}
                            ),
                        )
                    )
                else:
                    pack = record["proposal"]["pack"]
                    record["sandbox"] = (
                        await run_sandbox(
                            content, pack, execution=execution, progress=report_storage
                        )
                        if execution is not None
                        else await run_sandbox(content, pack)
                    )
                    record["sandbox"]["engine_revision"] = revision_identity
                    record["sandbox"]["input_digest"] = digest(record["content"])
            record["job"] = {"kind": kind, "status": "completed"}
        except asyncio.CancelledError:
            record["job"] = {"kind": kind, "status": "cancelled"}
        except Exception as exc:
            reference = secrets.token_hex(6)
            reason = job_failure_reason(exc)
            logging.getLogger(__name__).warning(
                "Workbench job failed reference=%s kind=%s exception=%s reason=%s",
                reference,
                kind,
                type(exc).__name__,
                reason,
            )
            # Generated/provider text never enters the error log or public error message.
            record["job"] = {
                "kind": kind,
                "status": "failed",
                "error": f"{reason} Error reference: {reference}.",
            }
        if kind == "author":
            message = (
                (record.get("proposal") or {}).get("summary")
                if record["job"]["status"] == "completed"
                else record["job"].get("error", "Authoring cancelled")
            )
            record.setdefault("author_messages", []).append(
                {
                    "role": "assistant",
                    "text": message,
                    "status": record["job"]["status"],
                    "revision": revision + 1,
                }
            )
            record["author_messages"] = record["author_messages"][-20:]
        try:
            store.put(
                owner, jsonable_encoder(record), revision, f"{kind}_{record['job']['status']}"
            )
        except ConflictError:
            pass  # A newer edit/cancel supersedes this result.
        finally:
            if active.get(record["id"]) is asyncio.current_task():
                active.pop(record["id"], None)

    def proposal_context(record: dict[str, Any]) -> dict[str, Any] | None:
        if record.get("proposal_stale"):
            return record.get("authoring_context")
        if not record.get("proposal"):
            return None
        return {
            "proposal": record["proposal"],
            "review": record.get("review"),
            "validation_problems": (record.get("validation") or {}).get("problems", []),
            "evaluation": (record.get("sandbox") or {}).get("evaluation")
            or (record.get("authoring_context") or {}).get("evaluation"),
        }

    def launch(owner: str, record: dict[str, Any], kind: str) -> dict[str, Any]:
        if record["id"] in active:
            raise HTTPException(409, "A job is already running for this draft")
        if len(active) >= 2:
            raise HTTPException(429, "Workbench is busy; two jobs are already running")
        record.pop("readiness", None)
        record.pop("runtime", None)
        if kind != "author":
            record["approval"] = None
        if record.get("sandbox"):
            record["previous_sandbox"] = {
                "revision": record["revision"],
                "result": record["sandbox"],
            }
        if kind == "author":
            record.setdefault("author_messages", []).append(
                {
                    "role": "operator",
                    "text": record["content"].get("instruction")
                    or "Build a model from the supplied evidence and decisions.",
                    "revision": record["revision"] + 1,
                }
            )
            record["authoring_context"] = proposal_context(record)
            # Keep the currently saved state while the revision is pending. Input
            # edits already invalidate incompatible evidence in save(); a failed
            # author request must not invalidate it a second time.
        else:
            record["sandbox"] = None
        if kind == "journey":
            record["previous_journey_result"] = record.pop("journey_result", None)
        if kind in {"sandbox", "journey"}:
            record.pop("storage_run", None)
        record["job"] = {"kind": kind, "status": "running"}
        saved = store.put(owner, record, record["revision"], f"{kind}_started")
        active[record["id"]] = asyncio.create_task(finish_job(owner, saved, kind))
        return view(saved.copy())

    @app.post("/admin/tenants/{draft_id}/author", status_code=202)
    async def generate(
        draft_id: str, body: Revision, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        content = Content.model_validate(record["content"])
        if author is None:
            raise HTTPException(503, "No authoring model configured; no data was sent")
        if content.data_policy != "provider_allowed" or not readiness(record)["begin"]["ready"]:
            raise HTTPException(
                409, "Review provider permission, redaction, scope and inputs first"
            )
        return launch(owner, record, "author")

    @app.post("/admin/tenants/{draft_id}/cancel")
    async def cancel(
        draft_id: str, body: Revision, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision, allow_running=True)
        if draft_id in active:
            active[draft_id].cancel()
            if execution is not None and (record.get("job") or {}).get("kind") in {
                "sandbox",
                "journey",
            }:
                # Remain running until the actual task confirms cleanup. No new
                # revision here: the worker owns progress and terminal evidence.
                return view(record)
        record["job"] = {"status": "cancelled"}
        return put(owner, record, body.revision, "job_cancelled")

    @app.post("/admin/tenants/{draft_id}/review")
    async def review(
        draft_id: str, body: Review, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if not record.get("proposal") or record.get("proposal_stale"):
            raise HTTPException(409, "Generate a proposal for the current inputs first")
        if record.get("pending_decisions"):
            raise HTTPException(409, "Apply your pending answers before reviewing the pack")
        removals = set(record["proposal"].get("repair_removals", []))
        if not set(body.accepted_removals).issubset(removals):
            raise HTTPException(422, "Unknown removal decision")
        if body.pack_accepted and set(body.accepted_removals) != removals:
            raise HTTPException(409, "Explicitly review each proposed data removal first")
        changes = {change["id"] for change in record.get("proposal_changes", [])}
        if not set(body.accepted_changes).issubset(changes):
            raise HTTPException(422, "Unknown or outdated pack change acknowledgement")
        if body.pack_accepted and set(body.accepted_changes) != changes:
            raise HTTPException(409, "Acknowledge each pack change before accepting this revision")
        known = {f["id"] for f in record["proposal"]["facts"]}
        if not (set(body.accepted_facts) | set(body.rejected_facts)).issubset(known):
            raise HTTPException(422, "Unknown proposal fact")
        if set(body.accepted_facts) & set(body.rejected_facts):
            raise HTTPException(422, "A proposal cannot be both accepted and rejected")
        if body.pack_accepted and record["proposal"].get("pack"):
            record["accepted_pack"] = copy.deepcopy(record["proposal"]["pack"])
        record.update(review=body.model_dump(exclude={"revision"}), sandbox=None, approval=None)
        return put(owner, record, body.revision, "proposal_reviewed")

    @app.post("/admin/tenants/{draft_id}/validate")
    async def validate_draft(
        draft_id: str, body: Revision, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if record.get("proposal_stale") or not (record.get("proposal") or {}).get("pack"):
            raise HTTPException(409, "Generate a current executable proposal first")
        try:
            record["validation"] = await asyncio.to_thread(
                validate, Content.model_validate(record["content"]), record["proposal"]["pack"]
            )
        except Exception as exc:
            record["validation"] = {"passed": False, "problems": [str(exc)[:4000]]}
        record["validation"]["engine_revision"] = revision_identity
        record["validation"]["input_digest"] = digest(record["content"])
        if record.get("sandbox"):
            record["previous_sandbox"] = {
                "revision": record["revision"],
                "result": record["sandbox"],
            }
        record.update(sandbox=None, approval=None)
        return put(owner, record, body.revision, "engine_validated")

    @app.post("/admin/tenants/{draft_id}/sandbox", status_code=202)
    async def sandbox(
        draft_id: str, body: Revision, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if not view(record)["readiness"]["run"]["ready"]:
            raise HTTPException(409, "Resolve execution readiness items first")
        return launch(owner, record, "sandbox")

    @app.post("/admin/tenants/{draft_id}/approve")
    async def approve(
        draft_id: str, body: Revision, owner: str = Depends(authenticate)
    ) -> dict[str, Any]:
        record = get(owner, draft_id, body.revision)
        if not view(record)["readiness"]["approve"]["ready"]:
            raise HTTPException(409, "Resolve approval readiness items first")
        record["approval"] = {
            "digest": digest(
                {
                    "content": record["content"],
                    "proposal": record["proposal"],
                    "validation": record["validation"],
                    "sandbox": record["sandbox"],
                }
            ),
            "operator": owner,
            "revision": body.revision,
        }
        return put(owner, record, body.revision, "approved_for_handoff")

    @app.get("/admin/tenants/{draft_id}/export")
    async def export(draft_id: str, owner: str = Depends(authenticate)) -> dict[str, Any]:
        record = get(owner, draft_id)
        pack = (record.get("proposal") or {}).get("pack")
        if not pack:
            raise HTTPException(409, "No executable pack yet")
        name = pack["pack"]["name"]
        content = Content.model_validate(record["content"])
        return {
            "pack_yaml": yaml.safe_dump(pack, sort_keys=False),
            "eval_yaml": yaml.safe_dump(evaluation_artifact(content, name), sort_keys=False),
            "record": view(record),
        }

    return app
