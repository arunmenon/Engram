"""Pack evaluation sets: the gate for retrieval weights (ADR-0018 decisions 8 and 10).

A pack that adds retrieval intents ships, or its operator writes, an
evaluation set ``<pack>.eval.yaml`` (in ``CG_ONTOLOGY_PACK_DIRS`` or next to
the built-in packs). The questions are about that deployment's data:

    pack: pdlc
    min_f1: 0.8                 # mean F1 the set must reach
    questions:
      - id: untested-requirements
        query: Which requirements have no tests?
        expected: ["Requirement:refunds|R2"]
        # optional: how an agent reads the answer
        answer: {node_type: Requirement, reasons: [no_link]}
        # optional: what the caller passes
        intent: completeness
        seed_node_ids: []

Each question runs through ``ArtifactRetriever`` on the graph under test.
The answer is the response's node ids, narrowed by ``answer`` when given,
and is scored by F1 against ``expected``. The set passes when the mean F1
reaches ``min_f1``.

A blue/green rebuild (``python -m context_graph.ontology rebuild``) runs
the sets of every active pack with intents on the new graph before it is
switched to; a pack with intents and no set fails the gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from context_graph.domain.ontology import OPEN_PACKS, OntologyError
from context_graph.ontology.loader import find_eval_set, load_yaml
from context_graph.retrieval.artifacts import ArtifactQuery

if TYPE_CHECKING:
    from pathlib import Path

    from context_graph.domain.models import AtlasResponse
    from context_graph.domain.ontology import OntologyRegistry
    from context_graph.retrieval.artifacts import ArtifactRetriever


class AnswerReading(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    node_type: str | None = None
    reasons: list[str] = Field(default_factory=list)


class EvalQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    id: str
    query: str = Field(min_length=1)
    expected: list[str]
    answer: AnswerReading = Field(default_factory=AnswerReading)
    intent: str | None = None
    seed_node_ids: list[str] = Field(default_factory=list)


class EvalSet(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    pack: str
    min_f1: float = Field(default=0.8, ge=0.0, le=1.0)
    questions: list[EvalQuestion] = Field(min_length=1)


@dataclass
class QuestionResult:
    id: str
    f1: float
    found: list[str]
    expected: list[str]


@dataclass
class EvalReport:
    pack: str
    min_f1: float
    mean_f1: float = 0.0
    results: list[QuestionResult] = field(default_factory=list)
    problem: str | None = None

    @property
    def passed(self) -> bool:
        return self.problem is None and self.mean_f1 >= self.min_f1

    def as_dict(self) -> dict[str, Any]:
        return {
            "pack": self.pack,
            "passed": self.passed,
            "mean_f1": round(self.mean_f1, 4),
            "min_f1": self.min_f1,
            "problem": self.problem,
            "questions": [
                {"id": r.id, "f1": round(r.f1, 4), "found": r.found, "expected": r.expected}
                for r in self.results
            ],
        }


def f1_score(found: set[str], expected: set[str]) -> float:
    """F1 of a found set against the expected one; two empty sets agree."""
    if not found and not expected:
        return 1.0
    hit = len(found & expected)
    if hit == 0:
        return 0.0
    precision, recall = hit / len(found), hit / len(expected)
    return 2 * precision * recall / (precision + recall)


def load_eval_set(path: Path) -> EvalSet:
    data = load_yaml(path.read_text(encoding="utf-8"), str(path))
    try:
        return EvalSet.model_validate(data)
    except ValidationError as exc:
        raise OntologyError(
            [f"{path}: {'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        ) from exc


def packs_needing_eval(registry: OntologyRegistry) -> list[str]:
    """Active packs, beyond today's, that declare retrieval intents."""
    return [p.name for p in registry.packs if p.name not in OPEN_PACKS and p.retrieval.intents]


def _reading(response: AtlasResponse, reading: AnswerReading) -> set[str]:
    return {
        key
        for key, node in response.nodes.items()
        if (reading.node_type is None or node.node_type == reading.node_type)
        and (not reading.reasons or node.retrieval_reason in reading.reasons)
    }


async def run_eval_set(
    eval_set: EvalSet, retriever: ArtifactRetriever, *, max_nodes: int
) -> EvalReport:
    report = EvalReport(eval_set.pack, eval_set.min_f1)
    for question in eval_set.questions:
        response = await retriever.retrieve(
            ArtifactQuery(
                question.query,
                seed_node_ids=tuple(question.seed_node_ids),
                intent=question.intent,
                max_nodes=max_nodes,
            )
        )
        found = _reading(response, question.answer)
        report.results.append(
            QuestionResult(
                question.id,
                f1_score(found, set(question.expected)),
                sorted(found),
                sorted(question.expected),
            )
        )
    report.mean_f1 = sum(r.f1 for r in report.results) / len(report.results)
    return report


def check_eval_sets(registry: OntologyRegistry, search_dirs: list[Path]) -> None:
    """Every pack that needs an evaluation set has one that loads; else OntologyError."""
    problems = []
    for name in packs_needing_eval(registry):
        path = find_eval_set(name, search_dirs)
        if path is None:
            problems.append(f"no evaluation set {name}.eval.yaml")
            continue
        try:
            eval_set = load_eval_set(path)
        except OntologyError as exc:
            problems.extend(exc.problems)
            continue
        if eval_set.pack != name:
            problems.append(f"{path} is for pack {eval_set.pack}")
    if problems:
        raise OntologyError(problems)


async def run_gate(
    registry: OntologyRegistry,
    retriever: ArtifactRetriever,
    search_dirs: list[Path],
    *,
    max_nodes: int,
) -> list[EvalReport]:
    """The evaluation set of every pack that needs one; a missing set is a failed report."""
    reports = []
    for name in packs_needing_eval(registry):
        path = find_eval_set(name, search_dirs)
        if path is None:
            reports.append(EvalReport(name, 1.0, problem=f"no evaluation set {name}.eval.yaml"))
            continue
        eval_set = load_eval_set(path)
        if eval_set.pack != name:
            reports.append(EvalReport(name, 1.0, problem=f"{path} is for pack {eval_set.pack}"))
            continue
        reports.append(await run_eval_set(eval_set, retriever, max_nodes=max_nodes))
    return reports
