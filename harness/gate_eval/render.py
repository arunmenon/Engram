"""Factorial cell renderer for the naming audit (E-20260928-06-r2).

A cell is (template, name_set, binding, order, run). Every cell of one template
is rendered from the same template file; only the name-to-rubric map and the
option order differ. The renderer asserts byte equality of question, state and
rubric texts across cells, and maps an answered option name back to a rubric id.
"""
from __future__ import annotations

import itertools
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .common import canonical_json, sha256_bytes


@dataclass(frozen=True)
class Cell:
    template_id: str
    name_set: str
    binding: str
    order: str
    run: int

    @property
    def cell_id(self) -> str:
        return f"{self.template_id}|{self.name_set}|{self.binding}|{self.order}|r{self.run}"

    @property
    def is_aligned(self) -> bool:
        return self.binding == "aligned"


def load_template(path: Path) -> dict:
    template = json.loads(path.read_text(encoding="utf-8"))
    n_rubrics = len(template["rubrics"])
    for name, names in template["name_sets"].items():
        if len(names) != n_rubrics:
            raise ValueError(f"{path}: name set {name} has {len(names)} names for {n_rubrics} rubrics")
        if len(set(names)) != len(names):
            raise ValueError(f"{path}: name set {name} has duplicate names")
    for name, perm in template["bindings"].items():
        if sorted(perm) != list(range(n_rubrics)):
            raise ValueError(f"{path}: binding {name} is not a permutation")
    for name, perm in template["orders"].items():
        if sorted(perm) != list(range(n_rubrics)):
            raise ValueError(f"{path}: order {name} is not a permutation")
    return template


def template_sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def enumerate_cells(template: dict) -> list[Cell]:
    """All cells of one template: name sets x bindings x orders x runs."""
    cells: list[Cell] = []
    runs_aligned = int(template.get("runs_per_aligned_cell", 2))
    for name_set, binding, order in itertools.product(
        template["name_sets"], template["bindings"], template["orders"]
    ):
        runs = runs_aligned if binding == "aligned" else 1
        for run in range(1, runs + 1):
            cells.append(Cell(template["template_id"], name_set, binding, order, run))
    return cells


def name_to_rubric_map(template: dict, cell: Cell) -> dict[str, str]:
    """Option name -> rubric id for this cell."""
    names = template["name_sets"][cell.name_set]
    perm = template["bindings"][cell.binding]
    return {names[j]: template["rubrics"][perm[j]]["rubric_id"] for j in range(len(names))}


def render_state(template: dict, item: dict) -> dict:
    """The state object: only the declared fields, in declared order."""
    missing = [f for f in template["state_fields"] if f not in item]
    if missing:
        raise ValueError(f"item {item.get('item_id')} lacks state fields {missing}")
    return {f: item[f] for f in template["state_fields"]}


def render_request(template: dict, cell: Cell, item: dict, model: str) -> dict:
    """Render one TypeSafe request for (cell, item).

    Options are emitted in the cell's presentation order. JSON objects keep
    insertion order, so the serialised request carries that order.
    """
    names = template["name_sets"][cell.name_set]
    perm = template["bindings"][cell.binding]
    order = template["orders"][cell.order]
    criteria: dict[str, str] = {}
    for slot in order:
        option_name = names[slot]
        rubric = template["rubrics"][perm[slot]]
        criteria[option_name] = rubric["text"]
    question = {"type": "choice", "instructions": template["question"], "criteria": criteria}
    return {
        "state": render_state(template, item),
        "model": model,
        "questions": {template["template_id"]: question},
    }


def request_bytes(request: dict) -> bytes:
    """Serialised request body as sent on the wire (insertion order preserved)."""
    return json.dumps(request, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def assert_byte_equality(template: dict, item: dict, model: str, cells: list[Cell]) -> None:
    """Question, state and every rubric text must be byte-identical across cells."""
    reference: dict[str, Any] | None = None
    for cell in cells:
        req = render_request(template, cell, item, model)
        q = req["questions"][template["template_id"]]
        invariant = {
            "instructions": q["instructions"],
            "state": canonical_json(req["state"]),
            "rubric_texts": sorted(q["criteria"].values()),
        }
        if reference is None:
            reference = invariant
            continue
        for key in invariant:
            if invariant[key] != reference[key]:
                raise AssertionError(
                    f"byte inequality in '{key}' between cell {cells[0].cell_id} and {cell.cell_id} for item {item.get('item_id')}"
                )


def map_answer(template: dict, cell: Cell, answer: dict) -> dict:
    """Map a Choice answer through the cell's map to a rubric id and rubric probabilities."""
    mapping = name_to_rubric_map(template, cell)
    if answer.get("type") != "choice":
        raise ValueError(f"expected a choice answer, got {answer.get('type')}")
    chosen = answer["choice"]
    if chosen not in mapping:
        raise ValueError(f"answer option {chosen!r} is not one of {sorted(mapping)}")
    probs = {mapping[name]: float(p) for name, p in answer["probabilities"].items()}
    ordered = sorted(probs.values(), reverse=True)
    gap = (ordered[0] - ordered[1]) if len(ordered) > 1 else float("nan")
    return {
        "rubric_id": mapping[chosen],
        "rubric_probabilities": probs,
        "top_two_gap": gap,
        "confidence": answer.get("confidence"),
    }


def name_token_delta(names_a: list[str], names_b: list[str]) -> int:
    """Crude local token-count difference of the name strings (whitespace/punct split)."""
    def count(names: list[str]) -> int:
        return sum(max(1, len(n.replace("-", " ").split())) for n in names)
    return abs(count(names_a) - count(names_b))
