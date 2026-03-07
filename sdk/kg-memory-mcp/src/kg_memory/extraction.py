"""LLM semantic extraction for ADR documents and CLAUDE.md config files.

Uses litellm for multi-provider LLM routing with JSON mode. Extracts
decisions, concepts, trade-offs, and conventions into structured Pydantic
models, then wires them into the knowledge graph.
"""

from __future__ import annotations

import hashlib
from typing import Any

import orjson
from pydantic import BaseModel, Field

from kg_memory.graph import Edge, EdgeType, KnowledgeGraph, Node, NodeType

# ---------------------------------------------------------------------------
# Extraction models
# ---------------------------------------------------------------------------


class Decision(BaseModel):
    statement: str
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0, default=0.8)


class Concept(BaseModel):
    name: str
    definition: str
    category: str = "term"  # algorithm, pattern, principle, term


class TradeOff(BaseModel):
    option_chosen: str
    option_rejected: str
    reason: str


class ADRExtraction(BaseModel):
    decisions: list[Decision] = []
    concepts: list[Concept] = []
    trade_offs: list[TradeOff] = []
    modules_governed: list[str] = []
    principles: list[str] = []
    related_adrs: list[str] = []


class ConfigExtraction(BaseModel):
    conventions: list[str] = []
    concepts: list[Concept] = []
    modules_referenced: list[str] = []


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_ADR_EXTRACTION_SYSTEM = """You are a knowledge extraction system that analyzes Architecture Decision Records (ADRs).

ADRs follow this structure:
- Title and status (accepted, proposed, etc.)
- Context: background and problem statement
- Decision: what was decided and why
- Consequences: trade-offs, impacts, and follow-up actions

Extract the following from the ADR text:

1. **decisions**: Each concrete architectural decision made.
   - statement: A clear summary of what was decided
   - rationale: Why this decision was made
   - confidence: 0.0-1.0 how clearly stated the decision is

2. **concepts**: Technical concepts, patterns, or terms defined or referenced.
   - name: The concept name
   - definition: Brief definition in context of this ADR
   - category: One of "algorithm", "pattern", "principle", "term"

3. **trade_offs**: Explicit trade-offs where one option was chosen over another.
   - option_chosen: What was selected
   - option_rejected: What was rejected or deprioritized
   - reason: Why the chosen option won

4. **modules_governed**: File paths or module names this ADR governs (e.g., "domain/scoring.py", "worker/projection.py")

5. **principles**: High-level design principles stated in the ADR (e.g., "Immutable events", "Derived projection")

6. **related_adrs**: References to other ADRs (e.g., "ADR-0003", "ADR-0010")

Return ONLY valid JSON matching this schema:
{
  "decisions": [{"statement": "...", "rationale": "...", "confidence": 0.9}],
  "concepts": [{"name": "...", "definition": "...", "category": "..."}],
  "trade_offs": [{"option_chosen": "...", "option_rejected": "...", "reason": "..."}],
  "modules_governed": ["path/to/module.py"],
  "principles": ["Principle statement"],
  "related_adrs": ["ADR-0003"]
}

Use empty arrays for any category with no results."""

_CONFIG_EXTRACTION_SYSTEM = """You are a knowledge extraction system that analyzes project configuration files (like CLAUDE.md).

These files contain:
- Coding conventions and style rules
- Architecture descriptions and module layouts
- Dependency lists and technology choices
- Design principles and patterns

Extract the following:

1. **conventions**: Specific coding rules and style conventions.
   Examples: "Use descriptive variable names", "Use orjson for JSON serialization"

2. **concepts**: Technical concepts, patterns, or architectural terms defined.
   - name: The concept name
   - definition: Brief definition
   - category: One of "algorithm", "pattern", "principle", "term"

3. **modules_referenced**: File paths or module names mentioned (e.g., "domain/models.py", "api/routes/")

Return ONLY valid JSON matching this schema:
{
  "conventions": ["Convention statement"],
  "concepts": [{"name": "...", "definition": "...", "category": "..."}],
  "modules_referenced": ["path/to/module.py"]
}

Use empty arrays for any category with no results."""

_ENTITY_RECONCILIATION_SYSTEM = """You are an entity reconciliation system. Given two concept names and their context, determine if they refer to the same thing.

Return ONLY valid JSON:
{
  "similarity": 0.85,
  "reasoning": "Brief explanation"
}

similarity should be 0.0-1.0:
- 0.9-1.0: Definitely the same concept (different names for the same thing)
- 0.7-0.89: Closely related but distinct concepts
- 0.4-0.69: Somewhat related
- 0.0-0.39: Unrelated"""


# ---------------------------------------------------------------------------
# Per-item validation helper
# ---------------------------------------------------------------------------


def _parse_items(
    raw_list: list[dict[str, Any]],
    model_cls: type[BaseModel],
    label: str = "item",
) -> list[Any]:
    """Validate each item individually so one bad item doesn't drop all results."""
    valid = []
    for item in raw_list:
        try:
            valid.append(model_cls.model_validate(item))
        except Exception:
            print(f"[extraction] {label} validation failed: {str(item)[:200]}")
    return valid


# ---------------------------------------------------------------------------
# LLM Extractor
# ---------------------------------------------------------------------------


class LLMExtractor:
    """Extracts structured knowledge from documents using LLM calls."""

    def __init__(
        self,
        model_id: str = "claude-sonnet-4-6",
        temperature: float = 0.1,
        max_tokens: int = 4096,
        timeout: int = 60,
    ) -> None:
        self._model_id = model_id
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._timeout = timeout

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        """Call the LLM and return parsed JSON response."""
        import litellm

        response = await litellm.acompletion(
            model=self._model_id,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
            temperature=self._temperature,
            max_tokens=self._max_tokens,
            timeout=self._timeout,
        )
        raw = response.choices[0].message.content
        text = str(raw) if raw is not None else "{}"
        return orjson.loads(text)

    async def extract_adr(self, adr_text: str, adr_path: str) -> ADRExtraction:
        """Extract decisions, concepts, trade-offs from an ADR document."""
        user_prompt = f"ADR file: {adr_path}\n\n{adr_text}"
        try:
            parsed = await self._call_llm(_ADR_EXTRACTION_SYSTEM, user_prompt)
        except Exception as exc:
            print(f"[extraction] ADR extraction failed for {adr_path}: {exc}")
            return ADRExtraction()

        decisions = _parse_items(parsed.get("decisions", []), Decision, "decision")
        concepts = _parse_items(parsed.get("concepts", []), Concept, "concept")
        trade_offs = _parse_items(parsed.get("trade_offs", []), TradeOff, "trade_off")

        return ADRExtraction(
            decisions=decisions,
            concepts=concepts,
            trade_offs=trade_offs,
            modules_governed=parsed.get("modules_governed", []),
            principles=parsed.get("principles", []),
            related_adrs=parsed.get("related_adrs", []),
        )

    async def extract_config(self, config_text: str) -> ConfigExtraction:
        """Extract conventions and concepts from CLAUDE.md."""
        try:
            parsed = await self._call_llm(_CONFIG_EXTRACTION_SYSTEM, config_text)
        except Exception as exc:
            print(f"[extraction] Config extraction failed: {exc}")
            return ConfigExtraction()

        concepts = _parse_items(parsed.get("concepts", []), Concept, "concept")

        return ConfigExtraction(
            conventions=parsed.get("conventions", []),
            concepts=concepts,
            modules_referenced=parsed.get("modules_referenced", []),
        )

    async def reconcile_entities(
        self,
        entity_a: str,
        entity_b: str,
        context_a: str,
        context_b: str,
    ) -> float:
        """LLM-powered semantic similarity check. Returns 0.0-1.0."""
        user_prompt = (
            f"Entity A: {entity_a}\nContext A: {context_a}\n\n"
            f"Entity B: {entity_b}\nContext B: {context_b}"
        )
        try:
            parsed = await self._call_llm(_ENTITY_RECONCILIATION_SYSTEM, user_prompt)
            score = float(parsed.get("similarity", 0.0))
            return max(0.0, min(1.0, score))
        except Exception as exc:
            print(f"[extraction] Entity reconciliation failed: {exc}")
            return 0.0

    async def answer_question(self, question: str, context: str) -> str:
        """Answer a question given graph context. For kg_ask tool."""
        import litellm

        system_prompt = (
            "You are a knowledgeable assistant that answers questions about a software project "
            "using the provided context from a knowledge graph. Be precise and cite specific "
            "decisions, concepts, or trade-offs when relevant. If the context does not contain "
            "enough information to answer, say so clearly."
        )
        user_prompt = f"Context:\n{context}\n\nQuestion: {question}"
        try:
            response = await litellm.acompletion(
                model=self._model_id,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
                max_tokens=self._max_tokens,
                timeout=self._timeout,
            )
            raw = response.choices[0].message.content
            return str(raw) if raw is not None else "No answer generated."
        except Exception as exc:
            return f"Error generating answer: {exc}"


# ---------------------------------------------------------------------------
# Graph wiring
# ---------------------------------------------------------------------------


def _stable_id(prefix: str, text: str) -> str:
    """Generate a stable deterministic node ID from a prefix and text."""
    digest = hashlib.sha256(text.encode()).hexdigest()[:12]
    return f"{prefix}:{digest}"


def apply_extraction_to_graph(
    graph: KnowledgeGraph,
    adr_node_id: str,
    extraction: ADRExtraction,
) -> None:
    """Apply LLM extraction results to the graph.

    Creates decision, concept, trade_off nodes and links them
    to the source ADR via decided_in, defines, considered edges.
    Also creates governs edges from ADR to referenced modules.
    """
    adr_node = graph.get_node(adr_node_id)
    if adr_node is None:
        return

    source_file = adr_node.properties.get("path", adr_node_id)

    # Decisions
    for decision in extraction.decisions:
        node_id = _stable_id("decision", decision.statement)
        graph.add_node(
            Node(
                id=node_id,
                node_type=NodeType.DECISION,
                name=decision.statement,
                properties={
                    "rationale": decision.rationale,
                    "confidence": decision.confidence,
                    "source_file": source_file,
                },
            )
        )
        graph.add_edge(
            Edge(
                source=node_id,
                target=adr_node_id,
                edge_type=EdgeType.DECIDED_IN,
                properties={"confidence": decision.confidence},
            )
        )

    # Concepts
    for concept in extraction.concepts:
        node_id = _stable_id("concept", concept.name)
        graph.add_node(
            Node(
                id=node_id,
                node_type=NodeType.CONCEPT,
                name=concept.name,
                properties={
                    "definition": concept.definition,
                    "category": concept.category,
                    "source_file": source_file,
                },
            )
        )
        graph.add_edge(
            Edge(
                source=adr_node_id,
                target=node_id,
                edge_type=EdgeType.DEFINES,
                properties={"category": concept.category},
            )
        )

    # Trade-offs
    for trade_off in extraction.trade_offs:
        node_id = _stable_id("tradeoff", f"{trade_off.option_chosen}|{trade_off.option_rejected}")
        graph.add_node(
            Node(
                id=node_id,
                node_type=NodeType.TRADE_OFF,
                name=f"{trade_off.option_chosen} over {trade_off.option_rejected}",
                properties={
                    "option_chosen": trade_off.option_chosen,
                    "option_rejected": trade_off.option_rejected,
                    "reason": trade_off.reason,
                    "source_file": source_file,
                },
            )
        )
        graph.add_edge(
            Edge(
                source=node_id,
                target=adr_node_id,
                edge_type=EdgeType.CONSIDERED,
                properties={"outcome": "chosen"},
            )
        )

    # Governs edges from ADR to existing module nodes
    for module_path in extraction.modules_governed:
        module_node = graph.get_node_by_path(module_path)
        if module_node is not None:
            graph.add_edge(
                Edge(
                    source=adr_node_id,
                    target=module_node.id,
                    edge_type=EdgeType.GOVERNS,
                )
            )
        else:
            # Try fuzzy path matching via name index
            candidates = graph.get_nodes_by_name(module_path.split("/")[-1].replace(".py", ""))
            for candidate in candidates:
                if candidate.node_type in (NodeType.MODULE, NodeType.FILE):
                    graph.add_edge(
                        Edge(
                            source=adr_node_id,
                            target=candidate.id,
                            edge_type=EdgeType.GOVERNS,
                        )
                    )
                    break

    # Principles stored as properties on the ADR node
    if extraction.principles:
        adr_node.properties["principles"] = extraction.principles

    # Related ADRs — link to other ADR nodes if they exist
    for related_ref in extraction.related_adrs:
        normalized = related_ref.lower().replace("-", "").replace(" ", "")
        for candidate_id in graph.type_index.get(NodeType.ADR, set()):
            candidate = graph.get_node(candidate_id)
            if candidate is None:
                continue
            candidate_norm = candidate.name.lower().replace("-", "").replace(" ", "")
            if normalized in candidate_norm or candidate_norm in normalized:
                graph.add_edge(
                    Edge(
                        source=adr_node_id,
                        target=candidate_id,
                        edge_type=EdgeType.RELATED_TO,
                        properties={"source": "adr_reference"},
                    )
                )
                break


def apply_config_extraction_to_graph(
    graph: KnowledgeGraph,
    config_node_id: str,
    extraction: ConfigExtraction,
) -> None:
    """Apply config extraction results to the graph.

    Creates concept nodes from CLAUDE.md and links them to the config node.
    Stores conventions as a property on the config node.
    """
    config_node = graph.get_node(config_node_id)
    if config_node is None:
        return

    source_file = config_node.properties.get("path", config_node_id)

    for concept in extraction.concepts:
        node_id = _stable_id("concept", concept.name)
        graph.add_node(
            Node(
                id=node_id,
                node_type=NodeType.CONCEPT,
                name=concept.name,
                properties={
                    "definition": concept.definition,
                    "category": concept.category,
                    "source_file": source_file,
                },
            )
        )
        graph.add_edge(
            Edge(
                source=config_node_id,
                target=node_id,
                edge_type=EdgeType.DEFINES,
            )
        )

    if extraction.conventions:
        config_node.properties["conventions"] = extraction.conventions

    for module_path in extraction.modules_referenced:
        module_node = graph.get_node_by_path(module_path)
        if module_node is not None:
            graph.add_edge(
                Edge(
                    source=config_node_id,
                    target=module_node.id,
                    edge_type=EdgeType.REFERENCES,
                )
            )
