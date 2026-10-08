"""Pack extraction consumer: LLM proposals from prose events (ADR-0018 phase 3).

For each event a pack names as an extraction source, this consumer:

1. takes the prose from the payload (``event_text``);
2. finds existing items the text may link to: the nodes the pack's
   projection rules make from this same event, and nodes of the proposable
   links' target types that share words with the text;
3. asks the model with the pack's generated prompt;
4. checks the answer against the profile (``ExtractionProfile.plan``) and
   writes what passes through the ``PackGraph`` port.

Its own consumer group (``CG_CONSUMER_GROUP_PACK_EXTRACTION``), so model
latency never holds back projection. A failed model call raises, so the
event is retried and, after ``CG_CONSUMER_MAX_RETRIES``, dead-lettered. An
answer that is not JSON is logged and acknowledged: asking again would
cost a model call for the same answer.

Known limits: links to nodes the projection consumer has not written yet
are dropped by ``upsert_edges`` (both endpoints must exist), and a proposal
never fills in a node that already exists, stubs included.

Backend-neutral: uses only the ``EventLog``, ``Subscription`` and
``PackGraph`` ports.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

import structlog

from context_graph.domain.models import Event
from context_graph.domain.pack_extraction import (
    ExtractionAnswerError,
    KnownItem,
    event_text,
    parse_answer,
)
from context_graph.ports.errors import RuntimeFencedError
from context_graph.ports.event_log import AcceptedRecordReader
from context_graph.worker.consumer import BaseConsumer
from context_graph.worker.pack_projection import apply_plan

if TYPE_CHECKING:
    from context_graph.domain.pack_extraction import ExtractionProfile
    from context_graph.domain.pack_projection import PackProjector
    from context_graph.domain.source_trust import VerifiedSourceProvenance
    from context_graph.ports.event_log import EventLog
    from context_graph.ports.extraction import TextGenerator
    from context_graph.ports.pack_graph import PackGraph
    from context_graph.ports.subscription import Subscription
    from context_graph.settings import Settings

log = structlog.get_logger(__name__)

WORD = re.compile(r"[a-z0-9][a-z0-9_.\-/]{3,}")
# Properties shown as a known item's label, first present wins
LABEL_FIELDS = ("title", "statement", "name", "catalog_name", "display_name", "body")


class ModelUnavailableError(RuntimeError):
    """The model returned nothing; the event is retried."""


def search_terms(text: str, limit: int) -> list[str]:
    """Distinct words of the text, longest first (the most specific), at most ``limit``."""
    words = sorted(set(WORD.findall(text.lower())), key=lambda w: (-len(w), w))
    return words[:limit]


def _label(node: dict[str, Any], length: int) -> str:
    for name in LABEL_FIELDS:
        value = node.get(name)
        if isinstance(value, str) and value.strip():
            return value.strip().replace("\n", " ")[:length]
    return ""


class PackExtractionConsumer(BaseConsumer):
    def __init__(
        self,
        subscription: Subscription,
        event_log: EventLog,
        graph: PackGraph,
        profiles: list[ExtractionProfile],
        projector: PackProjector,
        model: TextGenerator,
        settings: Settings,
    ) -> None:
        super().__init__(
            subscription,
            block_timeout_ms=settings.consumer.block_timeout_ms,
            max_retries=settings.consumer.max_retries,
        )
        self._event_log = event_log
        self._graph = graph
        self._profiles = profiles
        self._projector = projector
        self._model = model
        if (
            getattr(event_log, "requires_source_provenance", False) is True
            and projector.requires_provenance is not True
        ):
            raise RuntimeFencedError("Bound ledger requires authenticated extraction policy")
        if projector.requires_provenance is True and not isinstance(
            event_log, AcceptedRecordReader
        ):
            raise RuntimeFencedError("Bound extraction requires an accepted-record reader")
        self._known_limit = settings.ontology.extraction_known_limit
        self._search_terms = settings.ontology.extraction_search_terms
        self._lookup_limit = settings.ontology.lookup_limit
        self._label_chars = settings.ontology.extraction_label_chars

    async def process_message(self, entry_id: str, data: dict[str, str]) -> None:
        event_id = data.get("event_id")
        if event_id is None:
            return
        provenance = None
        document: dict[str, Any] | None
        if self._projector.requires_provenance is True:
            assert isinstance(self._event_log, AcceptedRecordReader)
            (record,) = await self._event_log.get_accepted_records([event_id])
            document, provenance = record.document, record.provenance
        else:
            (document,) = await self._event_log.get_documents([event_id])
        if document is None:
            log.warning("pack_extraction_event_missing", event_id=event_id, entry_id=entry_id)
            return
        event = Event.model_validate(document, strict=False)
        self._projector.source_trusted(event, document, provenance)
        for profile in self._profiles:
            if profile.handles(event.event_type):
                await self._extract(profile, event, document, provenance)

    async def _extract(
        self,
        profile: ExtractionProfile,
        event: Event,
        document: dict[str, Any],
        provenance: VerifiedSourceProvenance | None = None,
    ) -> None:
        text = event_text(document, profile.max_text_chars)
        if not text:
            return
        known = await self._known_items(profile, event, document, text, provenance)
        answer = await self._model.generate_text(profile.prompt(text, known))
        if answer is None:
            raise ModelUnavailableError(f"no answer for event {event.event_id}")
        try:
            raw = parse_answer(answer)
        except ExtractionAnswerError as exc:
            log.warning(
                "pack_extraction_answer_invalid",
                event_id=str(event.event_id),
                pack=profile.pack_name,
                error=str(exc),
            )
            return
        result = profile.plan(
            raw,
            event,
            trusted=self._projector.source_trusted(event, document, provenance),
            known=known,
        )
        written = await apply_plan(self._graph, result.plan, self._lookup_limit)
        log.info(
            "pack_extraction_applied",
            event_id=str(event.event_id),
            pack=profile.pack_name,
            nodes=result.accepted_nodes,
            links=result.accepted_links,
            edges_written=written,
            rejected=result.rejected[:20],
        )

    async def _known_items(
        self,
        profile: ExtractionProfile,
        event: Event,
        document: dict[str, Any],
        text: str,
        provenance: VerifiedSourceProvenance | None = None,
    ) -> list[KnownItem]:
        """Items the text may link to: this event's own nodes, then word matches."""
        known: dict[str, KnownItem] = {}
        own = self._projector.plan(event, document, provenance=provenance).nodes
        refs = [write.ref for write in own if write.ref.key_property == "node_id"]
        found = await self._graph.get_nodes(refs) if refs else {}
        for ref, node in found.items():
            known.setdefault(
                ref.key, KnownItem(ref.key, ref.label, _label(node, self._label_chars))
            )
        terms = search_terms(text, self._search_terms)
        targets = sorted(set().union(*profile.link_targets().values())) if profile.edges else []
        registry = self._projector.registry
        for label in targets:
            if len(known) >= self._known_limit or not terms:
                break
            node_type = registry.node_types[label]
            if node_type.key_property != "node_id" or label in profile.nodes:
                continue  # today's types and the proposable types are not offered by search
            fields = node_type.definition.text_fields or [
                name for name in node_type.key if name in node_type.properties
            ]
            rows = await self._graph.search_nodes(
                label, fields, terms, self._known_limit - len(known)
            )
            for node, _matched in rows:
                node_id = node.get("node_id")
                if isinstance(node_id, str):
                    known.setdefault(
                        node_id, KnownItem(node_id, label, _label(node, self._label_chars))
                    )
        return list(known.values())[: self._known_limit]
