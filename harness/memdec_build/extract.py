"""Run Engram's production extractor over the MEMDEC sessions.

  CG_LLM_MODEL_ID=gpt-5.6-terra CG_LLM_MAX_TOKENS=16384 CG_LLM_TIMEOUT_SECONDS=600 \
  ~/projects/Engram/.venv/bin/python -m memdec_build.extract --build <build dir> --drop-params

Reads <build>/sessions.jsonl (memdec_build.fetch). Writes, resumably:
  extractions_raw.jsonl   one SessionExtractionResult per session, as the client returned it,
                          plus repository_id and ended_at (thread creation time, for pair order)
  extraction_calls.jsonl  per-session call log (tokens, reply sha256) from locomo_extract's wrapper
  raw_responses.jsonl     raw model replies per session
and extraction_manifest.json with model and token totals.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import json
import uuid
from pathlib import Path

import litellm

from gate_eval import locomo_extract as recorder  # importing installs the recording wrapper on litellm.acompletion
from context_graph.adapters.llm.client import LLMExtractionClient
from context_graph.domain.models import Event
from context_graph.settings import LLMSettings

EVENT_NAMESPACE = uuid.UUID("0b8e3f7a-2c1d-4e5f-8a9b-1c2d3e4f5a6b")
AGENT_ID = "github"


def build_events(session: dict) -> tuple[list[Event], list[dict]]:
    start = _dt.datetime.fromisoformat(session["created_at"].replace("Z", "+00:00"))
    events, payloads = [], []
    for index, turn in enumerate(session["turns"]):
        event_id = uuid.uuid5(EVENT_NAMESPACE, f"{session['session_id']}#{index}")
        events.append(Event(event_id=event_id, event_type="user.message",
                            occurred_at=start + _dt.timedelta(minutes=index), session_id=session["session_id"],
                            agent_id=AGENT_ID, trace_id=session["session_id"],
                            payload_ref=f"github:{session['session_id']}#{index}"))
        payloads.append({"event_id": str(event_id),
                         "payload": {"role": turn["speaker"], "content": turn["text"], "turn_index": index}})
    return events, payloads


async def extract_one(client: LLMExtractionClient, session: dict, semaphore: asyncio.Semaphore):
    async with semaphore:
        recorder._current_session[asyncio.current_task().get_name()] = session["session_id"]
        events, payloads = build_events(session)
        result = await client.extract_from_session(events, session["session_id"], AGENT_ID, event_payloads=payloads)
        return session, result


async def run(args: argparse.Namespace) -> None:
    sessions = [json.loads(l) for l in (args.build / "sessions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    done_path = args.build / "extracted_sessions.txt"
    done = set(done_path.read_text().split()) if done_path.exists() else set()
    todo = [s for s in sessions if s["session_id"] not in done]
    settings = LLMSettings()
    client = LLMExtractionClient(model_id=settings.model_id, temperature=settings.temperature,
                                 max_tokens=settings.max_tokens, timeout=settings.timeout_seconds,
                                 max_retries=settings.max_retries)
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [asyncio.create_task(extract_one(client, s, semaphore), name=f"m{i}") for i, s in enumerate(todo)]
    with open(args.build / "extractions_raw.jsonl", "a", encoding="utf-8") as ex_fh, \
         open(done_path, "a", encoding="utf-8") as done_fh, \
         open(args.build / "extraction_calls.jsonl", "a", encoding="utf-8") as calls_fh, \
         open(args.build / "raw_responses.jsonl", "a", encoding="utf-8") as raw_fh:
        for finished in asyncio.as_completed(tasks):
            session, result = await finished
            sid = session["session_id"]
            calls = recorder._call_log.get(sid, [])
            failed = not any(c.get("ok") and c.get("json_ok") for c in calls)
            ex_fh.write(json.dumps({**result, "repository_id": session["repository_id"], "ended_at": session["created_at"]},
                                   ensure_ascii=False, sort_keys=True, default=str) + "\n")
            calls_fh.write(json.dumps({"session_id": sid, "failed": failed, "calls": calls}, sort_keys=True) + "\n")
            raw_fh.write(json.dumps({"session_id": sid, "responses": recorder._raw_responses.get(sid, [])}, ensure_ascii=False) + "\n")
            done_fh.write(sid + "\n")
            for fh in (ex_fh, done_fh, calls_fh, raw_fh):
                fh.flush()
            print(sid, "failed" if failed else f"ok prefs={len(result.get('preferences', []))}", flush=True)
    write_manifest(args.build, settings)


def write_manifest(build: Path, settings: LLMSettings) -> None:
    calls = [json.loads(l) for l in (build / "extraction_calls.jsonl").read_text().splitlines() if l.strip()]
    latest = {r["session_id"]: r for r in calls}
    extractions = [json.loads(l) for l in (build / "extractions_raw.jsonl").read_text().splitlines() if l.strip()]
    manifest = {
        "model_id": settings.model_id, "temperature_requested": settings.temperature,
        "litellm_drop_params": bool(litellm.drop_params), "max_tokens": settings.max_tokens,
        "timeout_seconds": settings.timeout_seconds, "prompt_version": "v1",
        "sessions_extracted": len(latest), "failed_sessions": sorted(s for s, r in latest.items() if r["failed"]),
        "preferences_total": sum(len(e.get("preferences", [])) for e in extractions),
        "calls_total": sum(len(r["calls"]) for r in calls),
        "prompt_tokens": sum(c.get("prompt_tokens", 0) for r in calls for c in r["calls"]),
        "completion_tokens": sum(c.get("completion_tokens", 0) for r in calls for c in r["calls"]),
        "written_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (build / "extraction_manifest.json").write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(prog="memdec_build.extract")
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=16)
    parser.add_argument("--drop-params", action="store_true")
    args = parser.parse_args()
    litellm.drop_params = args.drop_params
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
