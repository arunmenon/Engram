"""Customer-owned Spanner setup and launch, without experiment harness imports.

Run ``python -m context_graph.deployment --help``. Preparation freezes private
settings once; all processes consume that artifact and verify packaged source.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import stat
import tempfile
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from context_graph.settings import Settings
from context_graph.tenancy import (
    CredentialGrant,
    Principal,
    TenantBinding,
    TenantCatalog,
    TenantConfigurationError,
)

PORTS = ("event_log", "subscription", "graph", "keyword_index", "vector_index")


class DeploymentError(ValueError):
    """Operator error whose message contains no private configuration values."""


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class TenantSpec(_Strict):
    tenant_id: str
    binding_id: str
    epoch: Literal[1] = 1
    settings: dict[str, Any]


class CredentialSpec(_Strict):
    credential_id: str
    tenant_id: str
    roles: list[Literal["api", "admin"]] = Field(min_length=1)
    source_id: str
    token_env: str

    def principal(self) -> Principal:
        return Principal(self.credential_id, self.tenant_id, frozenset(self.roles), self.source_id)


class Manifest(_Strict):
    version: Literal[1]
    tenants: list[TenantSpec] = Field(min_length=1, max_length=32)
    credentials: list[CredentialSpec] = Field(min_length=1)


class ResolvedTenant(TenantSpec):
    bundle_digest: str


class Resolved(_Strict):
    version: Literal[1]
    runtime_sha256: str
    package_version: str
    tenants: list[ResolvedTenant] = Field(min_length=1, max_length=32)
    credentials: list[CredentialSpec] = Field(min_length=1)


def runtime_identity() -> tuple[str, str]:
    """Hash shipped Python/manifests; does not rely on a caller's version label or Git."""
    root = Path(__file__).resolve().parent
    files = sorted([*root.rglob("*.py"), *root.rglob("*.yaml")])
    if not files:
        raise DeploymentError("Cannot establish installed runtime source identity")
    entries = [
        (str(p.relative_to(root)), hashlib.sha256(p.read_bytes()).hexdigest()) for p in files
    ]
    digest = hashlib.sha256(json.dumps(entries, separators=(",", ":")).encode()).hexdigest()
    try:
        package_version = version("context-graph")
    except PackageNotFoundError:
        package_version = "unavailable (source fingerprint verified separately)"
    return digest, package_version


def _read(path: Path, model: type[Manifest] | type[Resolved]) -> Any:
    try:
        return model.model_validate_json(path.read_bytes())
    except (ValidationError, ValueError) as exc:
        # ValidationError can include secret-bearing input values. Never print it.
        raise DeploymentError("Invalid deployment JSON; check documented fields and types") from exc


def _binding(spec: TenantSpec, digest: str) -> TenantBinding:
    try:
        settings = Settings.model_validate_json(json.dumps(spec.settings))
        if settings.embedding.dimensions != settings.spanner.embedding_dimensions:
            raise DeploymentError("Embedding and Spanner vector dimensions must match")
        return TenantBinding.from_settings(
            spec.tenant_id,
            spec.binding_id,
            spec.epoch,
            settings,
            engine_revision="source-sha256:" + digest,
        )
    except (ValueError, TypeError, KeyError) as exc:
        raise DeploymentError("Invalid tenant settings or pack configuration") from exc


def _validate_structure(bindings: list[TenantBinding], credentials: list[CredentialSpec]) -> None:
    for name in ("tenant_id", "binding_id", "database_resource"):
        values = [getattr(b, name) for b in bindings]
        if len(set(values)) != len(values):
            raise DeploymentError("Duplicate tenant, binding or database mapping")
    ids = [c.credential_id for c in credentials]
    envs = [c.token_env for c in credentials]
    if len(set(ids)) != len(ids) or len(set(envs)) != len(envs):
        raise DeploymentError("Ambiguous credential references")
    tenants = {b.tenant_id for b in bindings}
    if tenants != {c.tenant_id for c in credentials}:
        raise DeploymentError(
            "Every credential must map to a tenant; every tenant needs credentials"
        )
    for credential in credentials:
        credential.principal()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", credential.token_env):
            raise DeploymentError("Invalid credential environment-variable name")
    from context_graph.worker.__main__ import CONSUMER_SUBSCRIPTIONS

    for binding in bindings:
        consumer = binding.settings().consumer
        groups = [getattr(consumer, field) for field, _ in CONSUMER_SUBSCRIPTIONS.values()]
        if any(not group.strip() for group in groups) or len(set(groups)) != 5:
            raise DeploymentError("Five distinct nonempty consumer groups required")
    namespaces = [b.archive_namespace for b in bindings if b.archive_namespace is not None]
    for i, first in enumerate(namespaces):
        for second in namespaces[i + 1 :]:
            if first[: len(second)] == second or second[: len(first)] == first:
                raise DeploymentError("Overlapping archive namespaces")


def _require_explicit(spec: TenantSpec) -> None:
    required = {
        "spanner": ("project", "instance", "database"),
        "storage": PORTS,
        "ontology": ("packs", "builtin_packs"),
        "llm": ("model_id",),
        "embedding": ("model_name", "dimensions"),
    }
    if any(
        not isinstance(spec.settings.get(section), dict)
        or any(key not in spec.settings[section] for key in keys)
        for section, keys in required.items()
    ):
        raise DeploymentError(
            "Explicit Spanner, backend, pack, model and embedding selections required"
        )


def write_private_json(path: Path, payload: dict[str, Any]) -> None:
    """Atomically publish a 0600 operator artifact without overwriting any file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError as exc:
            raise DeploymentError("Output exists; choose a new output path") from exc
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def _require_real_endpoint() -> None:
    if os.environ.get("SPANNER_EMULATOR_HOST"):
        raise DeploymentError("Customer tenant deployment cannot use SPANNER_EMULATOR_HOST")


def prepare(manifest: Path, output: Path) -> None:
    _require_real_endpoint()
    definition = _read(manifest, Manifest)
    digest, package_version = runtime_identity()
    bindings = []
    tenants = []
    for spec in definition.tenants:
        _require_explicit(spec)
        binding = _binding(spec, digest)
        bindings.append(binding)
        # This private operator artifact contains the exact frozen settings,
        # including legacy settings secrets. Never print or commit its contents.
        tenants.append(
            ResolvedTenant(
                tenant_id=spec.tenant_id,
                binding_id=spec.binding_id,
                epoch=spec.epoch,
                settings=json.loads(binding._settings_json),
                bundle_digest=binding.bundle_digest,
            )
        )
    _validate_structure(bindings, definition.credentials)
    write_private_json(
        output,
        Resolved(
            version=1,
            runtime_sha256=digest,
            package_version=package_version,
            tenants=tenants,
            credentials=definition.credentials,
        ).model_dump(),
    )


class Deployment:
    def __init__(self, path: Path):
        _require_real_endpoint()
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode) or stat.S_IMODE(mode) & 0o077:
            raise DeploymentError("Resolved configuration must be a private 0400/0600 regular file")
        self.resolved: Resolved = _read(path, Resolved)
        digest, _ = runtime_identity()
        if self.resolved.runtime_sha256 != digest:
            raise DeploymentError("Installed runtime differs from the prepared source fingerprint")
        self.bindings = [_binding(t, digest) for t in self.resolved.tenants]
        _validate_structure(self.bindings, self.resolved.credentials)
        if any(
            b.bundle_digest != t.bundle_digest
            for b, t in zip(self.bindings, self.resolved.tenants, strict=True)
        ):
            raise DeploymentError("Resolved settings or pack contents changed")

    def binding(self, tenant: str) -> TenantBinding:
        for binding in self.bindings:
            if binding.tenant_id == tenant:
                return binding
        raise DeploymentError("Unknown selected tenant")

    def catalog(self) -> TenantCatalog:
        grants = []
        for spec in self.resolved.credentials:
            token = os.environ.get(spec.token_env)
            if token is None:
                raise DeploymentError("Missing credential environment variable: " + spec.token_env)
            grants.append(CredentialGrant.from_token(spec.principal(), token))
        return TenantCatalog(tuple(self.bindings), tuple(grants))

    def inspect(self) -> dict[str, Any]:
        return {
            "runtime_sha256": self.resolved.runtime_sha256,
            "package_version": self.resolved.package_version,
            "tenants": [
                dict(
                    tenant_id=b.tenant_id,
                    database=b.database_resource,
                    binding_id=b.binding_id,
                    epoch=b.epoch,
                    bundle_digest=b.bundle_digest,
                    packs=[p.name for p in b.bundle.registry.packs],
                    model=b.settings().llm.model_id,
                    unevaluated_override=b.settings().ontology.serve_unevaluated,
                )
                for b in self.bindings
            ],
            "credential_env": [s.token_env for s in self.resolved.credentials],
        }


def check_binding(binding: TenantBinding, *, initialize: bool = False) -> dict[str, Any]:
    """Read schema/ownership/delivery state; initialization only bootstraps exact ownership."""
    from context_graph.adapters.spanner.lifecycle import close_database
    from context_graph.adapters.spanner.schema import open_database
    from context_graph.adapters.spanner.tenant_control import TenantFence, verify_control_schema

    database = open_database(binding.settings().spanner)
    try:
        fence = TenantFence.from_binding(binding)
        fence.check_database(database)
        verify_control_schema(database)
        if initialize:
            fence.bootstrap(
                database
            )  # no adoption, epoch transition, schema installation or repair
        with database.snapshot(multi_use=True) as snapshot:
            fence.check(snapshot, operation="read")
            pending = next(iter(snapshot.execute_sql("SELECT COUNT(*) FROM ConsumerDeliveries")))[0]
            dead = next(iter(snapshot.execute_sql("SELECT COUNT(*) FROM ConsumerDeadLetters")))[0]
            groups = [r[0] for r in snapshot.execute_sql("SELECT group_name FROM ConsumerGroups")]
        return dict(
            tenant_id=binding.tenant_id,
            database=binding.database_resource,
            ownership="active-and-matching",
            pending=pending,
            dead_letters=dead,
            registered_groups=sorted(groups),
            scope="schema/ownership/delivery snapshot, not proof that workers are running",
        )
    finally:
        close_database(database)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare", help="Freeze private settings once; no cloud calls")
    prep.add_argument("--manifest", required=True, type=Path)
    prep.add_argument("--output", required=True, type=Path)
    for command in ("inspect", "schema", "initialize", "check", "serve", "worker"):
        sub = commands.add_parser(command)
        sub.add_argument("--config", required=True, type=Path)
        if command in {"schema", "initialize", "worker"}:
            sub.add_argument("--tenant", required=True)
        if command == "initialize":
            sub.add_argument("--confirm-database", required=True)
        if command == "serve":
            sub.add_argument("--host", default="127.0.0.1")
            sub.add_argument("--port", type=int, default=8000)
        if command == "worker":
            from context_graph.worker.__main__ import VALID_CONSUMERS

            sub.add_argument("--consumer", choices=VALID_CONSUMERS, required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            prepare(args.manifest, args.output)
            print("Private resolved configuration created; use it for every process")
            return
        deployment = Deployment(args.config)
        if args.command == "inspect":
            print(json.dumps(deployment.inspect(), indent=2))
        elif args.command == "schema":
            from context_graph.adapters.spanner.schema import schema_statements
            from context_graph.adapters.spanner.tenant_control import TENANT_CONTROL_DDL

            binding = deployment.binding(args.tenant)
            print(
                ";\n\n".join(
                    [
                        *schema_statements(binding.settings().spanner.embedding_dimensions),
                        TENANT_CONTROL_DDL,
                    ]
                )
                + ";"
            )
        elif args.command == "initialize":
            binding = deployment.binding(args.tenant)
            if args.confirm_database != binding.database_resource:
                raise DeploymentError("Confirmation does not match the selected database resource")
            print(json.dumps(check_binding(binding, initialize=True)))
        elif args.command == "check":
            print(json.dumps([check_binding(b) for b in deployment.bindings], indent=2))
        elif args.command == "serve":
            import uvicorn

            from context_graph.api.tenants import create_tenant_app

            uvicorn.run(create_tenant_app(deployment.catalog()), host=args.host, port=args.port)
        else:
            from context_graph.worker.__main__ import run_worker

            binding = deployment.binding(args.tenant)
            asyncio.run(run_worker(args.consumer, tenant_binding=binding))
    except (DeploymentError, TenantConfigurationError) as exc:
        parser.exit(1, str(exc) + "\n")
    except Exception as exc:
        # SDK/provider errors can contain request data. Return a failure without
        # dumping the private settings or credentials; inspection names the target.
        parser.exit(
            1,
            f"{type(exc).__name__}: deployment operation failed; check credentials, "
            "schema and ownership on the inspected target\n",
        )


if __name__ == "__main__":
    main()
