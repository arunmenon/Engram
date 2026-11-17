"""Lossless reserved-marker handling, including legacy Spanner cells (#27)."""

import json

import pytest

from context_graph.adapters.spanner.log import json_param, json_value

pytest.importorskip("google.cloud.spanner")


@pytest.mark.parametrize(
    "literal",
    [
        {"$float": "0.125"},
        {"$float": "not-a-number"},
        {"$float": None},
        {"$engram_object": [["$float", "0.125"]]},
        {"$engram_object": "ordinary text"},
    ],
)
def test_literal_markers_round_trip_in_nested_payloads(literal):
    value = {"session_id": "fixture", "payload": [literal, {"nested": literal}], "score": 0.125}
    encoded = json_param(value)
    assert json_value(encoded) == value
    # Preserve fields used by generated schema columns; no root envelope.
    assert json.loads(encoded.serialize())["session_id"] == "fixture"


def test_legacy_numeric_marker_still_decodes_as_float():
    assert json_value('{"score":{"$float":"0.125"}}') == {"score": 0.125}


def test_legacy_nonnumeric_marker_is_readable_literal():
    assert json_value('{"payload":{"$float":"ordinary text"}}') == {
        "payload": {"$float": "ordinary text"}
    }
