"""The frozen state template and opinion rule for LINK-STALE-200 (E-20260928-07-r2).

Option names are neutral (A/B). In both decision types A means "retire memory_1" and B "keep it".
"""
from __future__ import annotations

STATE_TEMPLATE = {
    "template_id": "LINK-STALE-200/state_template/v1",
    "question_by_type": {
        "supersession": (
            "The state holds two stored memories from the same software project as targets: memory_1 (recorded earlier) and "
            "memory_2 (recorded later). Decide whether memory_2 supersedes memory_1, so that memory_1 should no longer be served "
            "as the current position."
        ),
        "staleness": (
            "The state holds one stored memory from a software project (memory_1) and an excerpt of the project's current state "
            "(snapshot_excerpt). Decide whether memory_1 is stale, that is, no longer true of the current state."
        ),
    },
    "options": ["A", "B"],
    "rubrics": {
        "supersession": {
            "A": "memory_2 supersedes memory_1: it replaces, reverses or invalidates what memory_1 states (for example a changed "
                 "store, component, library, value, count, name, scope or rule), so memory_1 is no longer current.",
            "B": "memory_2 does not supersede memory_1: it is consistent with it (it adds detail, refines without contradicting, "
                 "restates it, or covers a different aspect), so both can stand.",
        },
        "staleness": {
            "A": "memory_1 is stale: the snapshot excerpt contradicts it or shows that what it states has changed or no longer holds.",
            "B": "memory_1 is still valid: the snapshot excerpt confirms it or is consistent with it.",
        },
    },
    "canary_question": (
        "One of the neighbouring memories in the state ends with a nonce of the form 'Nonce: NX-xxxxxxxx.'. "
        "Choose the option that states the nonce that actually appears in the neighbours."
    ),
}

OPINION_RULE = {
    "rule_id": "LINK-STALE-200/opinion_rule/v1",
    "description": (
        "A sentence is marked unverified when it contains an evaluative verb AND is first-person or attributed. "
        "Matching is case-insensitive on whole words (render.sentence_is_unverified); attributed_patterns are regexes."
    ),
    "first_person_markers": ["i", "i'm", "i've", "i'd", "me", "my", "we", "we're", "we've", "our", "us"],
    "evaluative_verbs": [
        "think", "thinks", "believe", "believes", "feel", "feels", "reckon", "reckons", "suspect", "suspects", "doubt", "doubts",
        "guess", "assume", "assumes", "expect", "expects", "suppose", "consider", "considers", "agree", "agrees", "disagree",
        "disagrees", "argue", "argues", "argued", "claim", "claims", "claimed", "insist", "insists", "insisted", "prefer", "prefers",
        "recommend", "recommends", "say", "says", "said", "suggest", "suggests", "suggested", "maintain", "maintains",
        "is convinced", "am convinced", "are convinced", "am sure", "is sure", "are sure",
    ],
    "attributed_patterns": [
        r"\baccording to\b",
        r"\b(someone|somebody|a reviewer|a colleague|an engineer|the lead|the team|people|a contributor|the author|one maintainer)\b"
        r"[^.!?]{0,40}\b(said|says|thinks|think|believes|believe|feels|feel|argued|argues|claims|claimed|insists|insisted|reckons|suggested|suggests)\b",
        r"\b(reviewer|maintainer|architect|engineer|contributor|lead|author|committer)s?\b"
        r"[^.!?]{0,40}\b(said|says|thinks|think|believes|believe|feels|feel|argued|argues|argue|claims|claim|claimed|insists|insist|insisted|reckons|suggested|suggests|maintains)\b",
        r"\bin (my|our) (view|opinion|experience)\b",
    ],
}
