"""Contradiction detection and resolution for preferences and beliefs.

Detects same-key opposite-polarity preferences and resolves conflicts
using a most-recent-wins strategy, marking the loser with superseded_by.

Also detects contradictory beliefs (same category, similar but non-
identical text) and determines which belief supersedes the other based
on confidence, recency, and confirmation count.

Pure Python — ZERO framework imports.
"""

from __future__ import annotations

from datetime import datetime
from difflib import SequenceMatcher
from typing import Any


def detect_preference_contradictions(
    preferences: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Find same-key opposite-polarity preferences.

    Groups preferences by (category, key) and checks for polarity conflicts.
    Returns a list of (existing, conflicting) pairs.
    """
    conflicts: list[tuple[dict[str, Any], dict[str, Any]]] = []
    by_key: dict[tuple[str, str], dict[str, Any]] = {}

    for pref in preferences:
        key = (pref.get("category", ""), pref.get("key", ""))
        if key in by_key:
            existing = by_key[key]
            if existing.get("polarity") != pref.get("polarity"):
                conflicts.append((existing, pref))
        by_key[key] = pref

    return conflicts


def resolve_contradiction(
    pref_a: dict[str, Any],
    pref_b: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Most recent wins. Returns (winner, loser) where loser gets superseded_by set.

    Compares ``last_confirmed_at`` (falling back to ``created_at``) to determine
    which preference is newer. The loser's ``superseded_by`` field is set to the
    winner's preference_id.
    """
    a_time = _parse_dt(pref_a.get("last_confirmed_at") or pref_a.get("created_at"))
    b_time = _parse_dt(pref_b.get("last_confirmed_at") or pref_b.get("created_at"))

    # If one lacks a timestamp, the one WITH a timestamp is treated as older
    # (new preferences from extraction should win by default)
    if a_time is not None and b_time is not None:
        b_wins = b_time >= a_time
    elif b_time is not None:
        b_wins = False  # a has no timestamp → a is newer (from extraction)
    elif a_time is not None:
        b_wins = True  # b has no timestamp → b is newer (from extraction)
    else:
        b_wins = True  # both missing → default to b (second/newer arg)

    if b_wins:
        winner, loser = pref_b, pref_a
    else:
        winner, loser = pref_a, pref_b

    loser["superseded_by"] = winner.get("preference_id", winner.get("id", ""))
    return winner, loser


# ---------------------------------------------------------------------------
# Belief contradiction detection (WS3 item 3.5 + 3.6)
# ---------------------------------------------------------------------------


def detect_belief_contradiction(
    belief_a: dict[str, Any],
    belief_b: dict[str, Any],
    text_similarity_threshold: float = 0.6,
) -> bool:
    """Detect whether two beliefs contradict each other.

    Two beliefs are considered contradictory when they share the same
    category and their text is sufficiently similar (same topic) but
    not identical. Beliefs that are nearly identical (ratio > 0.95)
    are duplicates, not contradictions. Beliefs below the threshold
    are about different topics.
    """
    category_a = belief_a.get("category", "")
    category_b = belief_b.get("category", "")

    if category_a != category_b:
        return False

    text_a = belief_a.get("belief_text", "")
    text_b = belief_b.get("belief_text", "")

    if not text_a or not text_b:
        return False

    ratio = SequenceMatcher(None, text_a.lower(), text_b.lower()).ratio()

    # Too similar = duplicate, not contradiction
    if ratio > 0.95:
        return False

    # Below threshold = different topic; at or above = contradiction
    return ratio >= text_similarity_threshold


def resolve_belief_contradiction(
    belief_a: dict[str, Any],
    belief_b: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Determine which belief supersedes the other.

    The belief with higher confidence wins. On ties, the more recently
    confirmed belief wins. On further ties, higher confirmation count
    wins. Default: belief_b supersedes belief_a.

    Returns (winner, loser). Sets ``superseded_by`` on the loser.
    """
    conf_a = float(belief_a.get("confidence", 0.0))
    conf_b = float(belief_b.get("confidence", 0.0))

    if conf_a != conf_b:
        if conf_b > conf_a:
            winner, loser = belief_b, belief_a
        else:
            winner, loser = belief_a, belief_b
    else:
        # Tie-break on recency
        time_a = _parse_dt(belief_a.get("last_confirmed_at"))
        time_b = _parse_dt(belief_b.get("last_confirmed_at"))

        if time_a is not None and time_b is not None and time_a != time_b:
            if time_b > time_a:
                winner, loser = belief_b, belief_a
            else:
                winner, loser = belief_a, belief_b
        else:
            # Tie-break on confirmation count
            count_a = int(belief_a.get("confirmation_count", 1))
            count_b = int(belief_b.get("confirmation_count", 1))
            if count_b >= count_a:
                winner, loser = belief_b, belief_a
            else:
                winner, loser = belief_a, belief_b

    loser["superseded_by"] = winner.get("belief_id", "")
    return winner, loser


def find_belief_contradictions(
    beliefs: list[dict[str, Any]],
    text_similarity_threshold: float = 0.6,
) -> list[dict[str, Any]]:
    """Find all contradictory pairs among a list of beliefs.

    Only active (non-superseded) beliefs are compared. Returns a list
    of dicts with ``belief_a_id``, ``belief_b_id``, ``winner_id``,
    ``loser_id``, and ``category``.
    """
    active_beliefs = [b for b in beliefs if not b.get("superseded_by")]

    contradictions: list[dict[str, Any]] = []
    seen_pairs: set[tuple[str, str]] = set()

    for i, belief_a in enumerate(active_beliefs):
        for belief_b in active_beliefs[i + 1 :]:
            id_a = belief_a.get("belief_id", "")
            id_b = belief_b.get("belief_id", "")

            pair_key = (min(id_a, id_b), max(id_a, id_b))
            if pair_key in seen_pairs:
                continue

            if detect_belief_contradiction(belief_a, belief_b, text_similarity_threshold):
                winner, loser = resolve_belief_contradiction(belief_a, belief_b)
                contradictions.append(
                    {
                        "belief_a_id": id_a,
                        "belief_b_id": id_b,
                        "winner_id": winner.get("belief_id", ""),
                        "loser_id": loser.get("belief_id", ""),
                        "category": belief_a.get("category", ""),
                    }
                )
                seen_pairs.add(pair_key)

    return contradictions


def _parse_dt(raw: str | datetime | None) -> datetime | None:
    """Parse a datetime from string or return as-is."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return None
