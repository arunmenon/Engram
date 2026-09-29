"""Run Engram's session extractor over every LoCoMo session.

Recipe: docs/research/2026-09/fetch-H5-labelled-90.md, section 2.

Run with the Engram checkout's interpreter so `context_graph` imports:

  ~/projects/Engram/.venv/bin/python -m gate_eval.locomo_extract \
      --locomo data/raw/locomo/locomo10.json --out data/raw/locomo/

Writes extracted.jsonl (one line per preference, skill or interest),
sessions.jsonl (one line per session with the turn list, for excerpting) and
extraction_manifest.json (model, prompt version, tokens, failed sessions).
Sessions already present in extracted_sessions.txt are skipped, so an
interrupted run resumes without re-calling the model.
"""
from __future__ import annotations

import argparse
import asyncio
import datetime as _dt
import hashlib
import json
import re
import uuid
from pathlib import Path

import litellm

from context_graph.adapters.llm.client import LLMExtractionClient
from context_graph.domain.models import Event
from context_graph.settings import LLMSettings

SESSION_KEY = re.compile(r"session_(\d+)")
EVENT_NAMESPACE = uuid.UUID("7d4c3c1e-5b7a-4f0e-9d7a-6c1f2b3a4d5e")

# Per-session record of every model call made through litellm.acompletion.
_call_log: dict[str, list[dict]] = {}
_current_session: dict[str, str] = {}
_original_acompletion = litellm.acompletion


async def _recording_acompletion(*args, **kwargs):
    session_id = _current_session.get(asyncio.current_task().get_name(), "unknown")
    record: dict = {"ok": False}
    try:
        response = await _original_acompletion(*args, **kwargs)
    except Exception as exc:  # recorded, then re-raised for the client's own retry logic
        record["error"] = f"{type(exc).__name__}: {str(exc)[:300]}"
        _call_log.setdefault(session_id, []).append(record)
        raise
    content = response.choices[0].message.content or ""
    usage = getattr(response, "usage", None)
    record.update(
        ok=True,
        content_sha256=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        prompt_tokens=getattr(usage, "prompt_tokens", 0) or 0,
        completion_tokens=getattr(usage, "completion_tokens", 0) or 0,
        json_ok=_is_json(content),
    )
    _call_log.setdefault(session_id, []).append(record)
    return response


def _is_json(text: str) -> bool:
    try:
        json.loads(text)
        return True
    except (ValueError, TypeError):
        return False


litellm.acompletion = _recording_acompletion


def parse_session_time(raw: str | None) -> _dt.datetime:
    """LoCoMo stamps look like '1:56 pm on 8 May, 2023'."""
    if raw:
        for fmt in ("%I:%M %p on %d %B, %Y", "%I:%M %p on %d %b, %Y"):
            try:
                return _dt.datetime.strptime(raw.strip(), fmt).replace(tzinfo=_dt.timezone.utc)
            except ValueError:
                continue
    return _dt.datetime(2023, 1, 1, tzinfo=_dt.timezone.utc)


def iter_sessions(locomo: list[dict]):
    for conversation in locomo:
        conversation_id = conversation["sample_id"]
        body = conversation["conversation"]
        numbers = sorted(int(m.group(1)) for k in body if (m := SESSION_KEY.fullmatch(k)))
        for number in numbers:
            turns = body[f"session_{number}"]
            if not turns:
                continue
            yield {
                "session_id": f"{conversation_id}:session_{number}",
                "conversation_id": conversation_id,
                "session_time": body.get(f"session_{number}_date_time"),
                "turns": [{"speaker": t["speaker"], "text": t["text"], "dia_id": t.get("dia_id")} for t in turns],
            }


def build_events(session: dict) -> tuple[list[Event], list[dict]]:
    start = parse_session_time(session["session_time"])
    events: list[Event] = []
    payloads: list[dict] = []
    for turn_index, turn in enumerate(session["turns"]):
        event_id = uuid.uuid5(EVENT_NAMESPACE, f"{session['session_id']}#{turn_index}")
        payload = {"role": turn["speaker"], "content": turn["text"], "turn_index": turn_index}
        events.append(
            Event(
                event_id=event_id,
                event_type="user.message",
                occurred_at=start + _dt.timedelta(seconds=30 * turn_index),
                session_id=session["session_id"],
                agent_id="locomo",
                trace_id=session["session_id"],
                payload_ref=f"locomo:{session['session_id']}#{turn_index}",
            )
        )
        payloads.append({"event_id": str(event_id), "payload": payload})
    return events, payloads


def item_rows(session_id: str, result: dict, response_sha256: str | None) -> list[dict]:
    rows = []
    for kind, key, confidence_field in (
        ("preference", "preferences", "confidence"),
        ("skill", "skills", "confidence"),
        ("interest", "interests", "weight"),
    ):
        for n, item in enumerate(result.get(key, [])):
            rows.append(
                {
                    "session_id": session_id,
                    "item_kind": kind,
                    "item_index": n,
                    "fields": item,
                    "source_quote": item.get("source_quote"),
                    "source_turn_index": item.get("source_turn_index"),
                    "confidence": item.get(confidence_field),
                    "response_sha256": response_sha256,
                }
            )
    return rows


async def extract_one(client: LLMExtractionClient, session: dict, semaphore: asyncio.Semaphore) -> tuple[dict, dict]:
    async with semaphore:
        _current_session[asyncio.current_task().get_name()] = session["session_id"]
        events, payloads = build_events(session)
        result = await client.extract_from_session(
            events, session["session_id"], "locomo", event_payloads=payloads
        )
        return session, result


async def run(args: argparse.Namespace) -> None:
    locomo = json.loads(args.locomo.read_text(encoding="utf-8"))
    sessions = list(iter_sessions(locomo))
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "sessions.jsonl", "w", encoding="utf-8") as fh:
        for s in sessions:
            fh.write(json.dumps(s, ensure_ascii=False, sort_keys=True) + "\n")

    done_path = args.out / "extracted_sessions.txt"
    done = set(done_path.read_text().split()) if done_path.exists() else set()
    calls_path = args.out / "extraction_calls.jsonl"
    todo = [s for s in sessions if s["session_id"] not in done]
    if args.limit:
        todo = todo[: args.limit]

    settings = LLMSettings()
    client = LLMExtractionClient(
        model_id=settings.model_id,
        temperature=settings.temperature,
        max_tokens=settings.max_tokens,
        timeout=settings.timeout_seconds,
        max_retries=settings.max_retries,
    )
    semaphore = asyncio.Semaphore(args.concurrency)
    tasks = [asyncio.create_task(extract_one(client, s, semaphore), name=f"t{i}") for i, s in enumerate(todo)]
    with open(args.out / "extracted.jsonl", "a", encoding="utf-8") as items_fh, open(
        done_path, "a", encoding="utf-8"
    ) as done_fh, open(calls_path, "a", encoding="utf-8") as calls_fh:
        for finished in asyncio.as_completed(tasks):
            session, result = await finished
            calls = _call_log.get(session["session_id"], [])
            good = [c for c in calls if c.get("ok") and c.get("json_ok")]
            response_sha = good[-1]["content_sha256"] if good else None
            for row in item_rows(session["session_id"], result, response_sha):
                items_fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            calls_fh.write(
                json.dumps({"session_id": session["session_id"], "failed": not good, "calls": calls}, sort_keys=True) + "\n"
            )
            done_fh.write(session["session_id"] + "\n")
            items_fh.flush(); done_fh.flush(); calls_fh.flush()
            print(session["session_id"], "failed" if not good else "ok", flush=True)

    write_manifest(args, settings, sessions)


def write_manifest(args: argparse.Namespace, settings: LLMSettings, sessions: list[dict]) -> None:
    call_rows = [json.loads(l) for l in (args.out / "extraction_calls.jsonl").read_text().splitlines() if l.strip()]
    latest = {r["session_id"]: r for r in call_rows}
    items = [json.loads(l) for l in (args.out / "extracted.jsonl").read_text().splitlines() if l.strip()]
    prompt_tokens = sum(c.get("prompt_tokens", 0) for r in call_rows for c in r["calls"])
    completion_tokens = sum(c.get("completion_tokens", 0) for r in call_rows for c in r["calls"])
    manifest = {
        "source": "https://github.com/snap-research/locomo",
        "locomo_sha256": hashlib.sha256(args.locomo.read_bytes()).hexdigest(),
        "model_id": settings.model_id,
        "temperature": settings.temperature,
        "max_tokens": settings.max_tokens,
        "prompt_version": "v1",
        "litellm_drop_params": bool(litellm.drop_params),
        "sessions_total": len(sessions),
        "sessions_extracted": len(latest),
        "failed_sessions": sorted(s for s, r in latest.items() if r["failed"]),
        "items_total": len(items),
        "items_by_kind": {k: sum(1 for i in items if i["item_kind"] == k) for k in ("preference", "skill", "interest")},
        "calls_total": sum(len(r["calls"]) for r in call_rows),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "written_at": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    with open(args.out / "extraction_manifest.json", "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=1, sort_keys=True)
        fh.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(prog="gate_eval.locomo_extract")
    parser.add_argument("--locomo", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--concurrency", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--drop-params", action="store_true", help="set litellm.drop_params (model rejects temperature)")
    args = parser.parse_args()
    litellm.drop_params = args.drop_params
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
