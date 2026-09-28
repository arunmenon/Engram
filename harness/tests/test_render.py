import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gate_eval import render as R  # noqa: E402

TPL = Path(__file__).resolve().parents[1] / "templates" / "naming_audit"
ITEM = {"item_id": "i1", "source_document_id": "d1", "transcript_excerpt": "x", "item": "y", "quote": "z"}


def test_cell_counts_match_spec():
    noul = R.load_template(TPL / "noul_quote_supports_item.json")
    choice = R.load_template(TPL / "choice_source_type.json")
    assert len(R.enumerate_cells(noul)) == 18
    assert len(R.enumerate_cells(choice)) == 30


def test_byte_equality_and_latin_square():
    choice = R.load_template(TPL / "choice_source_type.json")
    cells = R.enumerate_cells(choice)
    R.assert_byte_equality(choice, ITEM, "jev-latest", cells)
    pairs = {(j, r) for perm in choice["bindings"].values() for j, r in enumerate(perm)}
    assert len(pairs) == 16


def test_answer_maps_through_cell_binding():
    choice = R.load_template(TPL / "choice_source_type.json")
    cell = R.Cell("choice_source_type", "N", "shift1", "canonical", 1)
    names = choice["name_sets"]["N"]
    answer = {"type": "choice", "choice": names[0], "probabilities": {n: (1.0 if n == names[0] else 0.0) for n in names}, "confidence": 1.0}
    mapped = R.map_answer(choice, cell, answer)
    assert mapped["rubric_id"] == "tool_result"  # name 0 bound to rubric (0+1) mod 4


def test_rendered_order_follows_cell():
    noul = R.load_template(TPL / "noul_quote_supports_item.json")
    canon = R.render_request(noul, R.Cell("noul_quote_supports_item", "R", "aligned", "canonical", 1), ITEM, "m")
    rev = R.render_request(noul, R.Cell("noul_quote_supports_item", "R", "aligned", "reversed", 1), ITEM, "m")
    k1 = list(canon["questions"]["noul_quote_supports_item"]["criteria"])
    k2 = list(rev["questions"]["noul_quote_supports_item"]["criteria"])
    assert k1 == k2[::-1]
    assert json.loads(R.request_bytes(canon))["state"] == {"transcript_excerpt": "x", "item": "y", "quote": "z"}
