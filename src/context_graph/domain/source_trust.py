"""Authenticated producer attribution, carried separately from caller JSON.

Only a fenced accepted-record reader establishes provenance. These types guard
trusted composition, not against arbitrary malicious code inside the process.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from context_graph.domain.event_acceptance import (
    EventAcceptance,
    EventInterpretation,
    EventInterpretationError,
    validate_accepted_document,
)

if TYPE_CHECKING:
    from context_graph.domain.models import Event
    from context_graph.tenancy import TenantBinding


@dataclass(frozen=True)
class VerifiedSourceProvenance:
    event_id: str
    acceptance: EventAcceptance


@dataclass(frozen=True)
class AcceptedRecord:
    document: dict[str, Any]
    provenance: VerifiedSourceProvenance


@dataclass(frozen=True)
class SourceTrustPolicy:
    authority: EventInterpretation
    trusted_source_ids: frozenset[str]
    ontology_version: str

    @classmethod
    def from_binding(cls, binding: TenantBinding) -> SourceTrustPolicy:
        return cls(
            EventInterpretation(
                binding.tenant_id,
                binding.database_resource,
                binding.binding_id,
                binding.epoch,
                binding.bundle_digest,
                binding.engine_revision,
            ),
            frozenset(binding.settings().ontology.trusted_source_ids),
            binding.bundle.registry.version,
        )

    def trusted(
        self, event: Event, document: dict[str, Any], provenance: VerifiedSourceProvenance | None
    ) -> bool:
        if not isinstance(provenance, VerifiedSourceProvenance) or not isinstance(
            provenance.acceptance, EventAcceptance
        ):
            raise EventInterpretationError("Authenticated source provenance is required")
        if provenance.event_id != str(event.event_id):
            raise EventInterpretationError("Source provenance belongs to another event")
        validated, receipt = validate_accepted_document(
            self.authority,
            provenance.event_id,
            document,
            provenance.acceptance.model_dump(),
        )
        # Do not allow a caller to supply a different Event beside a valid document.
        if event.model_dump(exclude={"global_position"}) != validated.model_dump(
            exclude={"global_position"}
        ):
            raise EventInterpretationError("Event differs from accepted source document")
        return receipt.source_id in self.trusted_source_ids
