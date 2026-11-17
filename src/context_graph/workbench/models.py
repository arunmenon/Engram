"""Bounded intake documents and explicit review records."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from context_graph.workbench.catalog import pack_names


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Source(Strict):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=160)
    kind: Literal["specification", "schema", "samples"]
    text: str = Field(min_length=1, max_length=40000)


class Question(Strict):
    id: str = Field(min_length=1, max_length=80)
    query: str = Field(min_length=1, max_length=2000)
    expected: list[str] = Field(default_factory=list, max_length=100)
    intent: str | None = None
    seed_node_ids: list[str] = Field(default_factory=list, max_length=100)
    seed_mode: Literal["discover", "explicit"] = "discover"
    node_type: str | None = None
    reviewed: bool = False
    expectation_statement: str | None = Field(default=None, max_length=4000)


class Content(Strict):
    name: str = Field(min_length=1, max_length=100)
    environment: str = Field(min_length=1, max_length=60)
    roots: list[Literal["memory", "user"]] = Field(default_factory=list, max_length=2)
    existing_packs: list[str] = Field(default_factory=list, max_length=16)
    scope: str = Field(default="", max_length=4000)
    data_policy: Literal["undecided", "local_only", "provider_allowed"] = "undecided"
    redaction_confirmed: bool = False
    sources: list[Source] = Field(default_factory=list, max_length=20)
    decisions: dict[str, str] = Field(default_factory=dict, max_length=50)
    questions: list[Question] = Field(default_factory=list, max_length=50)
    expected_nodes: list[str] = Field(default_factory=list, max_length=200)
    forbidden_nodes: list[str] = Field(default_factory=list, max_length=200)
    graph_reviewed: bool = False
    min_f1: float = Field(default=0.8, ge=0, le=1)
    producer_ids: list[str] = Field(default_factory=list, max_length=30)
    trusted_ids: list[str] = Field(default_factory=list, max_length=30)
    trust_reviewed: bool = False
    instruction: str = Field(default="", max_length=4000)

    @model_validator(mode="after")
    def unique_ids(self) -> Content:
        unavailable = set(self.existing_packs) - set(pack_names())
        if unavailable:
            raise ValueError(f"Unavailable domain packs: {sorted(unavailable)}")
        if len(set(self.existing_packs)) != len(self.existing_packs):
            raise ValueError("Select each domain pack only once")
        for values in ([s.id for s in self.sources], [q.id for q in self.questions]):
            if len(set(values)) != len(values):
                raise ValueError("Source and question IDs must be unique within their list")
        if not set(self.trusted_ids).issubset(self.producer_ids):
            raise ValueError("Trusted sources must be declared producer identities")
        if any(not v.strip() for v in self.decisions.values()):
            raise ValueError("Decision answers cannot be blank")
        return self


class Citation(Strict):
    source_id: str
    quote: str = Field(min_length=1, max_length=2000)


class Fact(Strict):
    id: str
    concept: str = Field(min_length=1, max_length=200)
    explanation: str = Field(min_length=1, max_length=2000)
    basis: Literal["source", "inference", "operator"]
    citations: list[Citation] = Field(default_factory=list, max_length=10)
    pack_paths: list[str] = Field(default_factory=list, max_length=100)
    decision_ids: list[str] = Field(default_factory=list, max_length=50)
    trusted_producers: list[str] | None = Field(
        default=None,
        max_length=30,
        description="Snapshot of inputs.trusted_ids; valid only when trust_reviewed is true.",
    )
    instruction_quote: str | None = Field(
        default=None,
        min_length=1,
        max_length=4000,
        description="Exact excerpt of the current revision request supporting this fact.",
    )


class Decision(Strict):
    id: str
    question: str = Field(min_length=1, max_length=500)
    effect: str = Field(min_length=1, max_length=1500)


class Proposal(Strict):
    summary: str = Field(min_length=1, max_length=4000)
    facts: list[Fact] = Field(default_factory=list, max_length=60)
    decisions: list[Decision] = Field(
        default_factory=list,
        max_length=30,
        description=(
            "Blocking questions that remain UNRESOLVED after reading all operator answers. "
            "Do not list decisions already supplied, confirmed or implemented. "
            "Return an empty list when no new operator choice is needed."
        ),
    )
    pack: dict[str, Any] | None = None
    limitations: list[str] = Field(default_factory=list, max_length=30)
    repair_removals: list[str] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def unique_ids(self) -> Proposal:
        for items in (self.facts, self.decisions):
            if len({item.id for item in items}) != len(items):
                raise ValueError("Proposal IDs must be unique")
        return self


class Save(Strict):
    revision: int = Field(ge=1)
    content: Content


class Revision(Strict):
    revision: int = Field(ge=1)


class StoryReview(Revision):
    accepted_checks: list[str] = Field(default_factory=list, max_length=150)


class Review(Revision):
    accepted_facts: list[str] = Field(max_length=60)
    rejected_facts: list[str] = Field(default_factory=list, max_length=60)
    pack_accepted: bool = False
    accepted_removals: list[str] = Field(default_factory=list, max_length=500)
    accepted_changes: list[str] = Field(default_factory=list, max_length=5000)
    confirmed_policies: list[Literal["identity", "lifecycle"]] = Field(
        default_factory=list, max_length=2
    )
