"""Build the 90-item H5 candidate file from LoCoMo extraction output (no model).

Recipe: docs/research/2026-09/fetch-H5-labelled-90.md, section 3.

  python -m gate_eval.locomo_candidates --raw data/raw/locomo/ --out data/candidates/H5-labelled-90/

Deviation from the recipe, recorded in candidates_manifest.json: the extractor
leaves `source_turn_index` null on most items, and the recipe's fallback (whole
session as the excerpt) would make every Jev call carry a full session. When the
index is missing, the anchor turn is the first turn that contains the quote
verbatim (case- and whitespace-normalised); only when no turn contains it is the
whole session used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from .common import read_jsonl, sha256_file, utc_now, write_json, write_jsonl

BUCKET_SIZE = 30
MAX_PER_SESSION = 6
EXCERPT_RADIUS = 3


def normalise(text: str) -> str:
    return " ".join((text or "").lower().split())


def render_item(kind: str, fields: dict) -> str:
    if kind == "preference":
        about = f" about {fields['about_entity']}" if fields.get("about_entity") else ""
        return (f"{fields['category']} preference ({fields['polarity']}, strength {fields['strength']:.2f}): "
                f"{fields['key'].replace('_', ' ')}{about}")
    if kind == "skill":
        return f"skill: {fields['name']} ({fields['category'].replace('_', ' ')}, proficiency {fields['proficiency']:.2f})"
    return f"interest: {fields['entity_name']} ({fields['entity_type']}, weight {fields['weight']:.2f})"


def anchor_turn(turns: list[dict], quote: str, given_index) -> tuple[int | None, str]:
    if isinstance(given_index, int) and 0 <= given_index < len(turns):
        return given_index, "extractor"
    q = normalise(quote)
    for index, turn in enumerate(turns):
        if q and q in normalise(turn["text"]):
            return index, "derived_verbatim_match"
    return None, "none_whole_session"


def excerpt(turns: list[dict], index: int | None) -> str:
    chosen = turns if index is None else turns[max(0, index - EXCERPT_RADIUS) : index + EXCERPT_RADIUS + 1]
    return "\n".join(f"[{t['speaker']}] {t['text']}" for t in chosen)


def bucket_of(confidence: float, in_excerpt: bool, in_session: bool) -> str | None:
    if not in_session or confidence < 0.30:
        return "no_fit"
    if confidence >= 0.85 and in_excerpt:
        return "obvious"
    if 0.40 <= confidence <= 0.70 and in_excerpt:
        return "ambiguous"
    return None


KIND_KEYS = (("preference", "preferences", "confidence", "key"), ("skill", "skills", "confidence", "name"),
             ("interest", "interests", "weight", "entity_name"))


def dropped_by_validation(raw: Path, extracted: list[dict]) -> list[dict]:
    """Items in the reply the client used that the client's quote validation dropped.

    The client returns on the first parsable reply, so the used reply is the first
    JSON reply of the session. An item is dropped when no returned item of the same
    kind has the same name and quote.
    """
    path = raw / "raw_responses.jsonl"
    if not path.exists():
        return []
    returned = {(r["session_id"], r["item_kind"], r["fields"].get(name_key), r["source_quote"])
                for r in extracted for kind, _, _, name_key in KIND_KEYS if r["item_kind"] == kind}
    dropped = []
    for session in read_jsonl(path):
        used = None
        for reply in session["responses"]:
            try:
                used = json.loads(reply)
                break
            except (ValueError, TypeError):
                continue
        if not isinstance(used, dict):
            continue
        for kind, list_key, confidence_key, name_key in KIND_KEYS:
            for fields in used.get(list_key) or []:
                if not isinstance(fields, dict) or not fields.get("source_quote") or fields.get(confidence_key) is None:
                    continue
                key = (session["session_id"], kind, fields.get(name_key), fields["source_quote"])
                if key in returned:
                    continue
                try:
                    rendered = render_item(kind, fields)
                    confidence = float(fields[confidence_key])
                except (KeyError, TypeError, ValueError, AttributeError):
                    continue
                dropped.append({"session_id": session["session_id"], "item_kind": kind, "fields": fields,
                                "source_quote": fields["source_quote"], "source_turn_index": fields.get("source_turn_index"),
                                "confidence": confidence, "rendered": rendered, "dropped_by_validation": True})
    return dropped


def build(raw: Path, out: Path) -> dict:
    sessions = {s["session_id"]: s for s in read_jsonl(raw / "sessions.jsonl")}
    returned_items = read_jsonl(raw / "extracted.jsonl")
    dropped = dropped_by_validation(raw, returned_items)
    extracted = returned_items + dropped
    per_session_counter: Counter = Counter()
    candidates = []
    for row in extracted:
        session = sessions[row["session_id"]]
        n = per_session_counter[row["session_id"]]
        per_session_counter[row["session_id"]] += 1
        turns = session["turns"]
        quote = row.get("source_quote") or ""
        index, anchor = anchor_turn(turns, quote, row.get("source_turn_index"))
        text = excerpt(turns, index)
        q = normalise(quote)
        in_session = bool(q) and q in normalise("\n".join(t["text"] for t in turns))
        in_excerpt = bool(q) and q in normalise(text)
        confidence = float(row["confidence"])
        candidates.append({
            "item_id": f"{row['session_id']}#{n}",
            "source_document_id": row["session_id"],
            "conversation_id": session["conversation_id"],
            "transcript_excerpt": text,
            "item": render_item(row["item_kind"], row["fields"]),
            "item_kind": row["item_kind"],
            "quote": quote,
            "extractor_confidence": confidence,
            "excerpt_anchor": anchor,
            "origin": "dropped_by_client_validation" if row.get("dropped_by_validation") else "returned",
            "bucket": bucket_of(confidence, in_excerpt, in_session),
        })
    by_bucket = defaultdict(list)
    for c in candidates:
        if c["bucket"]:
            by_bucket[c["bucket"]].append(c)
    chosen, per_session, dropped_for_cap, no_fit_fallback = [], Counter(), 0, 0
    for bucket in ("obvious", "ambiguous", "no_fit"):
        pool = sorted(by_bucket[bucket], key=lambda c: hashlib.sha256(c["item_id"].encode()).hexdigest())
        taken = 0
        for c in pool:
            if taken == BUCKET_SIZE:
                break
            if per_session[c["source_document_id"]] >= MAX_PER_SESSION:
                dropped_for_cap += 1
                continue
            per_session[c["source_document_id"]] += 1
            chosen.append(c)
            taken += 1
        if taken < BUCKET_SIZE and bucket == "no_fit":
            # Fallback (recorded): the recipe's no_fit rule finds too few items when the
            # extractor quotes verbatim and never scores below 0.30. Fill with the
            # lowest-confidence items not already drawn, ties by sha256(item_id).
            chosen_ids = {c["item_id"] for c in chosen}
            rest = sorted((c for c in candidates if c["item_id"] not in chosen_ids),
                          key=lambda c: (c["extractor_confidence"], hashlib.sha256(c["item_id"].encode()).hexdigest()))
            for c in rest:
                if taken == BUCKET_SIZE:
                    break
                if per_session[c["source_document_id"]] >= MAX_PER_SESSION:
                    dropped_for_cap += 1
                    continue
                per_session[c["source_document_id"]] += 1
                chosen.append({**c, "bucket": "no_fit", "no_fit_fallback": True})
                taken += 1
                no_fit_fallback += 1
        if taken < BUCKET_SIZE:
            raise SystemExit(f"bucket {bucket} has only {taken} eligible items")
    item_fields = ("item_id", "source_document_id", "transcript_excerpt", "item", "quote", "bucket", "extractor_confidence")
    items = [{k: c[k] for k in item_fields} for c in chosen]
    out.mkdir(parents=True, exist_ok=True)
    write_jsonl(out / "items.jsonl", items)
    with open(out / "labelling_sheet.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["item_id", "transcript_excerpt", "item", "quote", "gold_quote_supports_item", "gold_source_type", "notes"])
        for c in items:
            writer.writerow([c["item_id"], c["transcript_excerpt"], c["item"], c["quote"], "", "", ""])
    manifest = {
        "built_at": utc_now(),
        "extracted_sha256": sha256_file(raw / "extracted.jsonl"),
        "candidates_total": len(candidates),
        "pool_sizes": {b: len(v) for b, v in by_bucket.items()},
        "draw_rule": "within each bucket sort by sha256(item_id) hex ascending, take the first 30; skip items whose session already contributes 6 of the 90; buckets drawn in the order obvious, ambiguous, no_fit",
        "verbatim_rule": "quote found = lowercased, whitespace-collapsed quote is a substring of the lowercased, whitespace-collapsed text",
        "bucket_rules": {"obvious": "confidence >= 0.85 and quote in excerpt", "ambiguous": "0.40 <= confidence <= 0.70 and quote in excerpt",
                          "no_fit": "quote not in session, or confidence < 0.30"},
        "excerpt_rule": "3 turns before to 3 turns after the anchor turn; anchor = source_turn_index if present, else first turn containing the quote verbatim, else whole session",
        "excerpt_anchor_counts_chosen": dict(Counter(c["excerpt_anchor"] for c in chosen)),
        "item_kind_counts_chosen": dict(Counter(c["item_kind"] for c in chosen)),
        "dropped_for_session_cap": dropped_for_cap,
        "G_sessions": len(per_session),
        "conversations": len({c["conversation_id"] for c in chosen}),
        "bucket_counts": dict(Counter(c["bucket"] for c in items)),
        "returned_items": len(returned_items),
        "no_fit_by_recipe_rule": BUCKET_SIZE - no_fit_fallback,
        "no_fit_by_fallback": no_fit_fallback,
        "no_fit_fallback_rule": "the recipe's no_fit rule (quote not in session, or confidence < 0.30) matched too few items: gpt-6-astra quoted every item verbatim and scored none below 0.30; the remainder of no_fit is the lowest-confidence items not already drawn, ordered by (confidence, sha256(item_id)), same 6-per-session cap",
        "no_fit_fallback_confidences": sorted(c["extractor_confidence"] for c in chosen if c.get("no_fit_fallback")),
        "dropped_by_client_validation_recovered": len(dropped),
        "origin_counts_chosen": dict(Counter(c["origin"] for c in chosen)),
        "origin_counts_by_bucket_chosen": {b: dict(Counter(c["origin"] for c in chosen if c["bucket"] == b)) for b in ("obvious", "ambiguous", "no_fit")},
        "dropped_item_note": "Engram's client drops items whose quote fails its fuzzy check before returning them; those items are recovered from the raw reply the client used (first JSON reply of the session) and enter the pool with their raw confidence (no source-type ceiling applied). Without them the recipe's no_fit bucket is nearly empty, because the returned items all passed the quote check.",
    }
    write_json(out / "candidates_manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(prog="gate_eval.locomo_candidates")
    parser.add_argument("--raw", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.raw, args.out), indent=1))


if __name__ == "__main__":
    main()
