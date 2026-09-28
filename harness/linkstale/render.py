"""Arm rendering for E-20260928-07-r2.

One frozen `state_template` (JSON) renders arms A, A', B, C1, C2, the probe
variants and the delivery canary. Question, options and rubric bytes are
identical in every arm; neighbour text is identical across B, C1 and C2 after
stripping the C1/C2 labels. Option names are neutral (A/B) as the spec fixes.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ARMS = ("A", "A_prime", "B", "C1", "C2")
NEIGHBOUR_ARMS = ("B", "C1", "C2")
SOURCE_CLASSES = ("user-stated", "tool-result", "inferred", "imported")
EVENT_TYPE_TO_SOURCE_CLASS = {
    "user.message": "user-stated",
    "tool.result": "tool-result",
    "extraction.output": "inferred",
    "import": "imported",
}


def load_state_template(path: Path) -> dict:
    tpl = json.loads(path.read_text(encoding="utf-8"))
    for key in ("question_by_type", "options", "rubrics"):
        if key not in tpl:
            raise ValueError(f"state template lacks {key}")
    if list(tpl["options"]) != ["A", "B"]:
        raise ValueError("options must be exactly A and B (neutral names, per spec)")
    return tpl


def load_opinion_rule(path: Path) -> dict:
    rule = json.loads(path.read_text(encoding="utf-8"))
    if "first_person_markers" not in rule or "evaluative_verbs" not in rule:
        raise ValueError("opinion_rule.json needs first_person_markers and evaluative_verbs")
    rule["_compiled"] = [re.compile(p, re.IGNORECASE) for p in rule.get("attributed_patterns", [])]
    return rule


def sentence_is_unverified(sentence: str, rule: dict) -> bool:
    """Deterministic rule: first-person or attributed evaluative sentence."""
    lowered = sentence.lower()
    has_eval = any(re.search(rf"\b{re.escape(v)}\b", lowered) for v in rule["evaluative_verbs"])
    first_person = any(re.search(rf"\b{re.escape(m)}\b", lowered) for m in rule["first_person_markers"])
    attributed = any(p.search(sentence) for p in rule["_compiled"])
    return has_eval and (first_person or attributed)


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p]


def source_class_for(neighbour: dict, p5_landed: bool) -> tuple[str, str]:
    """Returns (source_class, provenance) — P5 field if landed, else event type map."""
    if p5_landed and neighbour.get("source_class") in SOURCE_CLASSES:
        return neighbour["source_class"], "P5"
    et = neighbour.get("originating_event_type", "")
    for prefix, cls in EVENT_TYPE_TO_SOURCE_CLASS.items():
        if et.startswith(prefix):
            return cls, "event-type"
    return "inferred", "event-type-default"


def render_neighbours(neighbours: list[dict], arm: str, rule: dict | None, p5_landed: bool) -> list[dict] | str:
    if arm == "B":
        return "\n\n".join(n["text"] for n in neighbours)
    if arm == "C1":
        return [{"text": n["text"]} for n in neighbours]
    if arm == "C2":
        out = []
        for n in neighbours:
            cls, _ = source_class_for(n, p5_landed)
            sentences = [{"text": s, "unverified": sentence_is_unverified(s, rule)} for s in split_sentences(n["text"])]
            out.append({"source_class": cls, "sentences": sentences})
        return out
    raise ValueError(arm)


def render_state(tpl: dict, item: dict, arm: str, neighbours: list[dict], rule: dict | None, p5_landed: bool) -> dict:
    """State payload. Targets always present; neighbours section only in B/C1/C2 and always inside the state."""
    state: dict = {"targets": item["targets"]}
    if item.get("snapshot_excerpt") is not None:
        state["snapshot_excerpt"] = item["snapshot_excerpt"]
    if arm == "B":
        state["neighbours_text"] = render_neighbours(neighbours, "B", rule, p5_landed)
    elif arm in ("C1", "C2"):
        state["neighbours"] = render_neighbours(neighbours, arm, rule, p5_landed)
    return state


def render_request(tpl: dict, item: dict, arm: str, neighbours: list[dict], rule: dict | None, p5_landed: bool, model: str) -> dict:
    question = tpl["question_by_type"][item["decision_type"]]
    criteria = {"A": tpl["rubrics"][item["decision_type"]]["A"], "B": tpl["rubrics"][item["decision_type"]]["B"]}
    return {
        "state": render_state(tpl, item, arm, neighbours, rule, p5_landed),
        "model": model,
        "questions": {"decision": {"type": "choice", "instructions": question, "criteria": criteria}},
    }


def render_canary_request(tpl: dict, item: dict, arm: str, neighbours: list[dict], nonce: str, rule: dict | None, p5_landed: bool, model: str) -> dict:
    """One neighbour carries the nonce; the question asks only to quote it (Choice over two candidate nonces)."""
    decoy = nonce[::-1]
    req = render_request(tpl, item, arm, neighbours, rule, p5_landed, model)
    req["questions"] = {"canary": {"type": "choice", "instructions": tpl["canary_question"],
                                   "criteria": {"A": f"The nonce present in the neighbours is {nonce}", "B": f"The nonce present in the neighbours is {decoy}"}}}
    return req


def strip_labels(rendered) -> str:
    """Neighbour text with C1/C2 structure removed, for the cross-arm identity assertion."""
    if isinstance(rendered, str):
        return rendered
    texts = []
    for n in rendered:
        if "text" in n:
            texts.append(n["text"])
        else:
            texts.append(" ".join(s["text"] for s in n["sentences"]))
    return "\n\n".join(texts)


def request_bytes(request: dict) -> bytes:
    return json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
