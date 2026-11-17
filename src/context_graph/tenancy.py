"""Immutable tenant configuration and authentication substrate.

No production dispatcher is enabled here. Durable database ownership, epoch
fences and source-signature bindings remain prerequisites for tenant service.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import SecretStr

from context_graph.domain.pack_bundle import ActiveBundle, resolve_bundle
from context_graph.ontology.loader import load_registry
from context_graph.settings import Settings

if TYPE_CHECKING:
    from context_graph.domain.event_acceptance import AdmissionContext


class TenantConfigurationError(ValueError):
    """Invalid server-owned routing configuration; never includes credentials."""


class TenantAuthorizationError(PermissionError):
    """No unambiguous authorized tenant; no default fallback."""


def _identifier(value: str) -> bool:
    return (
        isinstance(value, str)
        and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", value) is not None
    )


def _secret_json(value: Any) -> Any:
    if isinstance(value, SecretStr):
        return value.get_secret_value()
    if isinstance(value, dict):
        return {key: _secret_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_secret_json(item) for item in value]
    return value


def _database(settings: Settings) -> str:
    parts = (settings.spanner.project, settings.spanner.instance, settings.spanner.database)
    if not all(re.fullmatch(r"[a-z0-9][a-z0-9-]*", part) for part in parts):
        raise TenantConfigurationError("Invalid Spanner resource components")
    return f"projects/{parts[0]}/instances/{parts[1]}/databases/{parts[2]}"


def _archive(settings: Settings) -> tuple[str, ...] | None:
    if not settings.archive.enabled:
        return None
    if settings.storage.archive == "fs":
        return ("fs", *Path(settings.archive.fs_base_path).resolve().parts)
    if settings.storage.archive == "gcs":
        prefix = settings.archive.gcs_prefix.strip("/")
        if (
            not settings.archive.gcs_bucket
            or not prefix
            or any(part in ("", ".", "..") for part in prefix.split("/"))
        ):
            raise TenantConfigurationError("Archive requires an explicit isolated namespace")
        return ("gcs", settings.archive.gcs_bucket, *prefix.split("/"))
    raise TenantConfigurationError("Unsupported tenant archive backend")


@dataclass(frozen=True)
class TenantBinding:
    tenant_id: str
    binding_id: str
    epoch: int
    engine_revision: str
    _settings_json: str = field(repr=False)
    bundle: ActiveBundle = field(repr=False)
    database_resource: str = field(init=False)
    bundle_digest: str = field(init=False)
    archive_namespace: tuple[str, ...] | None = field(init=False)

    def __post_init__(self) -> None:
        if not _identifier(self.tenant_id) or not _identifier(self.binding_id):
            raise TenantConfigurationError("Invalid tenant/binding identity")
        if type(self.epoch) is not int or self.epoch < 1 or not self.engine_revision:
            raise TenantConfigurationError("Positive epoch and explicit engine revision required")
        settings = self.settings()
        if any(
            getattr(settings.storage, port) != "spanner"
            for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index")
        ):
            raise TenantConfigurationError("Tenant durable runtime ports must all use Spanner")
        if settings.spanner.emulator_host or not settings.spanner.check_schema:
            raise TenantConfigurationError("Tenant binding requires real Spanner schema validation")
        if settings.spanner.create_if_missing or settings.spanner.allow_create_on_instance:
            raise TenantConfigurationError("Tenant startup cannot create a database")
        policy = json.loads(self._settings_json)
        # Credential rotation has its own identity; it is not reinterpretation.
        policy.pop("auth", None)
        for backend in ("redis", "neo4j"):
            for credential in ("username", "password"):
                policy[backend].pop(credential, None)
        for secret_name in ("github_secret", "jira_secret"):
            policy["webhooks"].pop(secret_name, None)
        for selection in ("packs", "builtin_packs", "trusted_sources", "trusted_source_ids"):
            policy["ontology"][selection] = sorted(set(policy["ontology"][selection]))
        digest_input = {
            "engine_revision": self.engine_revision,
            "packs": [
                pack.canonical_json()
                for pack in sorted(self.bundle.registry.packs, key=lambda pack: pack.name)
            ],
            "processing": self.bundle.processing,
            "policy": policy,
        }
        digest = hashlib.sha256(json.dumps(digest_input, sort_keys=True).encode()).hexdigest()
        object.__setattr__(self, "database_resource", _database(settings))
        object.__setattr__(self, "archive_namespace", _archive(settings))
        object.__setattr__(self, "bundle_digest", "sha256:" + digest)

    @classmethod
    def from_settings(
        cls,
        tenant_id: str,
        binding_id: str,
        epoch: int,
        settings: Settings,
        *,
        engine_revision: str,
    ) -> TenantBinding:
        snapshot = settings.model_copy(deep=True)
        if snapshot.archive.enabled and snapshot.storage.archive == "fs":
            snapshot.archive.fs_base_path = str(Path(snapshot.archive.fs_base_path).resolve())
        if snapshot.archive.enabled and snapshot.storage.archive == "gcs":
            snapshot.archive.gcs_prefix = snapshot.archive.gcs_prefix.strip("/")
        # Bypass path-keyed runtime caches: pin the actual manifests now.
        bundle = resolve_bundle(
            load_registry(
                snapshot.ontology.packs,
                [Path(path) for path in snapshot.ontology.pack_dirs],
                builtin_packs=snapshot.ontology.builtin_packs,
            )
        )
        return cls(
            tenant_id,
            binding_id,
            epoch,
            engine_revision,
            json.dumps(_secret_json(snapshot.model_dump(mode="python")), sort_keys=True),
            bundle,
        )

    def settings(self) -> Settings:
        """A fresh private value, including secrets, never a borrowed mutable object."""
        return Settings.model_validate_json(self._settings_json)

    def runtime_configuration(
        self, settings: Settings | None = None, bundle: ActiveBundle | None = None
    ) -> tuple[Settings, ActiveBundle]:
        """Validate supplied values, then return the binding's private configuration."""
        private = self.settings()
        if settings is not None and settings.model_dump() != private.model_dump():
            raise TenantConfigurationError("Runtime settings differ from the pinned tenant binding")
        if bundle is not None and bundle is not self.bundle:
            raise TenantConfigurationError("Runtime bundle differs from the pinned tenant binding")
        return private, self.bundle

    def admission_context(self, principal: Principal) -> AdmissionContext:
        """Build immutable acceptance authority from server-authenticated identity."""
        from context_graph.domain.event_acceptance import AdmissionContext

        if (
            not isinstance(principal, Principal)
            or principal.tenant_id != self.tenant_id
            or "api" not in principal.roles
            or principal.source_id is None
        ):
            raise TenantAuthorizationError("Authenticated admission source is required")
        return AdmissionContext(
            tenant_id=self.tenant_id,
            database_resource=self.database_resource,
            binding_id=self.binding_id,
            accepted_epoch=self.epoch,
            bundle_digest=self.bundle_digest,
            engine_revision=self.engine_revision,
            source_id=principal.source_id,
        )


@dataclass(frozen=True)
class Principal:
    credential_id: str
    tenant_id: str
    roles: frozenset[str]
    source_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", frozenset(self.roles))
        if not _identifier(self.credential_id) or not _identifier(self.tenant_id):
            raise TenantConfigurationError("Invalid credential principal identity")
        if not self.roles or self.roles - {"api", "admin"}:
            raise TenantConfigurationError("Invalid credential roles")
        if self.source_id is not None and not _identifier(self.source_id):
            raise TenantConfigurationError("Invalid authenticated source identity")


@dataclass(frozen=True)
class CredentialGrant:
    principal: Principal
    token_digest: bytes = field(repr=False)

    @classmethod
    def from_token(cls, principal: Principal, token: str) -> CredentialGrant:
        if (
            not isinstance(token, str)
            or len(token) < 16
            or not token.isascii()
            or any(char.isspace() for char in token)
        ):
            raise TenantConfigurationError("Credential must be a nonempty opaque ASCII token")
        return cls(principal, hashlib.sha256(token.encode()).digest())

    def __post_init__(self) -> None:
        if not isinstance(self.token_digest, bytes) or len(self.token_digest) != 32:
            raise TenantConfigurationError("Invalid credential digest")


@dataclass(frozen=True)
class TenantCatalog:
    bindings: tuple[TenantBinding, ...]
    credentials: tuple[CredentialGrant, ...]
    max_tenants: int = 32

    def __post_init__(self) -> None:
        object.__setattr__(self, "bindings", tuple(self.bindings))
        object.__setattr__(self, "credentials", tuple(self.credentials))
        if (
            type(self.max_tenants) is not int
            or self.max_tenants < 1
            or not self.bindings
            or len(self.bindings) > self.max_tenants
        ):
            raise TenantConfigurationError("Tenant catalog is empty or exceeds configured bound")
        for field_name in ("tenant_id", "binding_id", "database_resource"):
            values = [getattr(binding, field_name) for binding in self.bindings]
            if len(values) != len(set(values)):
                raise TenantConfigurationError(f"Duplicate catalog {field_name}")
        tenants = {binding.tenant_id for binding in self.bindings}
        ids, digests = set(), set()
        for grant in self.credentials:
            if grant.principal.source_id is None:
                raise TenantConfigurationError("Tenant credentials require an explicit source_id")
            if grant.principal.tenant_id not in tenants:
                raise TenantConfigurationError("Credential references unknown tenant")
            if grant.principal.credential_id in ids or grant.token_digest in digests:
                raise TenantConfigurationError("Ambiguous credential assignment")
            ids.add(grant.principal.credential_id)
            digests.add(grant.token_digest)
        if tenants != {grant.principal.tenant_id for grant in self.credentials}:
            raise TenantConfigurationError("Every tenant requires an explicit credential binding")
        namespaces = [
            binding.archive_namespace
            for binding in self.bindings
            if binding.archive_namespace is not None
        ]
        for index, first in enumerate(namespaces):
            for second in namespaces[index + 1 :]:
                if first[: len(second)] == second or second[: len(first)] == first:
                    raise TenantConfigurationError("Overlapping tenant archive namespaces")

    def authenticate(self, token: str, *, tenant_hint: str | None = None) -> Principal:
        if not isinstance(token, str):
            raise TenantAuthorizationError("Unauthorized tenant credential")
        digest = hashlib.sha256(token.encode()).digest()
        matches = [
            grant.principal
            for grant in self.credentials
            if hmac.compare_digest(digest, grant.token_digest)
        ]
        if len(matches) != 1 or (tenant_hint is not None and matches[0].tenant_id != tenant_hint):
            raise TenantAuthorizationError("Unauthorized tenant credential")
        return matches[0]

    def binding(self, tenant_id: str) -> TenantBinding:
        for binding in self.bindings:
            if binding.tenant_id == tenant_id:
                return binding
        raise TenantAuthorizationError("Unknown tenant")
