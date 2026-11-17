"""Pure catalog tests; no database ownership or tenant traffic is enabled."""

from dataclasses import FrozenInstanceError, replace

import pytest
from pydantic import SecretStr

from context_graph.settings import Settings
from context_graph.tenancy import (
    CredentialGrant,
    Principal,
    TenantAuthorizationError,
    TenantBinding,
    TenantCatalog,
    TenantConfigurationError,
)


def configuration(database="tenant-a"):
    settings = Settings()
    for port in ("event_log", "subscription", "graph", "keyword_index", "vector_index"):
        setattr(settings.storage, port, "spanner")
    settings.spanner.project = "portiq-mvp"
    settings.spanner.instance = "engram-experiment"
    settings.spanner.database = database
    settings.spanner.emulator_host = None
    settings.spanner.check_schema = True
    settings.spanner.create_if_missing = False
    settings.spanner.allow_create_on_instance = False
    settings.archive.enabled = False
    settings.ontology.packs = []
    settings.ontology.builtin_packs = []
    return settings


def bind(tenant="a", settings=None, **kwargs):
    return TenantBinding.from_settings(
        tenant,
        "binding-" + tenant,
        1,
        settings or configuration("tenant-" + tenant),
        engine_revision=kwargs.get("engine_revision", "test-engine-revision"),
    )


def grant(tenant="a", token=None, roles=frozenset({"api"}), credential_id=None):
    return CredentialGrant.from_token(
        Principal(
            credential_id or "credential-" + tenant, tenant, roles, source_id="source-" + tenant
        ),
        token or (tenant * 32),
    )


def test_private_settings_preserve_secrets_without_mutable_aliases(monkeypatch):
    settings = configuration()
    settings.webhooks.github_secret = SecretStr("secret-not-for-repr")
    binding = bind(settings=settings)
    settings.spanner.database = "mutated"
    monkeypatch.setenv("CG_SPANNER_DATABASE", "ambient")
    restored = binding.settings()
    assert restored.spanner.database == "tenant-a"
    assert restored.webhooks.github_secret.get_secret_value() == "secret-not-for-repr"
    restored.spanner.database = "also-mutated"
    assert binding.settings().spanner.database == "tenant-a"
    assert "secret-not-for-repr" not in repr(binding)
    assert {name for name, _version in binding.bundle.pack_identities} == {"core"}
    with pytest.raises(FrozenInstanceError):
        binding.epoch = 2


def test_credentials_rotate_without_reinterpreting_but_policy_and_engine_changes_do():
    settings = configuration()
    original = bind(settings=settings)
    settings.auth.api_key = "rotated-key"
    settings.webhooks.github_secret = SecretStr("rotated-secret")
    assert bind(settings=settings).bundle_digest == original.bundle_digest
    settings.webhooks.max_body_bytes += 1
    assert bind(settings=settings).bundle_digest != original.bundle_digest
    assert bind(engine_revision="other-code").bundle_digest != original.bundle_digest


def test_exact_manifest_content_pinned_even_when_name_version_path_are_same(tmp_path):
    path = tmp_path / "lab.pack.yaml"
    path.write_text("pack:\n  name: lab\n  version: 1.0.0\n  description: first\n")
    settings = configuration()
    settings.ontology.pack_dirs = [str(tmp_path)]
    settings.ontology.packs = ["lab"]
    first = bind(settings=settings)
    path.write_text("pack:\n  name: lab\n  version: 1.0.0\n  description: second\n")
    second = bind(settings=settings)
    assert first.bundle_digest != second.bundle_digest
    assert first.bundle.registry.pack("lab").pack.description == "first"


@pytest.mark.parametrize(
    "change",
    [
        lambda s: setattr(s.storage, "subscription", "memory"),
        lambda s: setattr(s.spanner, "check_schema", False),
        lambda s: setattr(s.spanner, "emulator_host", "localhost:9010"),
        lambda s: setattr(s.spanner, "create_if_missing", True),
        lambda s: setattr(s.spanner, "database", "../other"),
    ],
)
def test_unsafe_database_settings_refused(change):
    settings = configuration()
    change(settings)
    with pytest.raises(TenantConfigurationError):
        bind(settings=settings)


@pytest.mark.parametrize("epoch", [True, 0, -1])
def test_invalid_epoch_rejected(epoch):
    with pytest.raises(TenantConfigurationError):
        replace(bind(), epoch=epoch)


def test_catalog_auth_roles_rotation_and_no_fallback():
    catalog = TenantCatalog(
        [bind("a"), bind("b")],
        [
            grant("a"),
            grant("b", roles={"admin"}),
            grant("a", token="rotated" * 8, credential_id="credential-a-rotated"),
        ],
    )
    assert catalog.authenticate("a" * 32).roles == {"api"}
    assert catalog.authenticate("b" * 32).roles == {"admin"}
    assert catalog.authenticate("rotated" * 8).tenant_id == "a"
    assert catalog.binding("b").database_resource.endswith("/databases/tenant-b")
    for token, hint in (("unknown", None), ("a" * 32, "b"), (None, None)):
        with pytest.raises(TenantAuthorizationError):
            catalog.authenticate(token, tenant_hint=hint)
    with pytest.raises(TenantAuthorizationError):
        catalog.binding("missing")
    assert "a" * 32 not in repr(catalog)


@pytest.mark.parametrize(
    "bindings,grants",
    [
        ([bind("a"), bind("a")], [grant("a")]),
        ([bind("a"), bind("b", settings=configuration("tenant-a"))], [grant("a"), grant("b")]),
        ([bind("a"), bind("b")], [grant("a"), grant("b", token="a" * 32)]),
        ([bind("a")], [grant("b")]),
        ([bind("a")], []),
    ],
)
def test_ambiguous_or_uncredentialed_catalog_refused(bindings, grants):
    with pytest.raises(TenantConfigurationError):
        TenantCatalog(bindings, grants)


@pytest.mark.parametrize("backend", ["fs", "gcs"])
def test_nested_archive_namespaces_rejected(backend, tmp_path):
    first, second = configuration("tenant-a"), configuration("tenant-b")
    for settings, suffix in ((first, "root"), (second, "root/child")):
        settings.archive.enabled = True
        settings.storage.archive = backend
        settings.archive.fs_base_path = str(tmp_path / suffix)
        settings.archive.gcs_bucket = "shared-bucket"
        settings.archive.gcs_prefix = suffix
    with pytest.raises(TenantConfigurationError, match="Overlapping"):
        TenantCatalog([bind("a", first), bind("b", second)], [grant("a"), grant("b")])


def test_input_collections_cannot_mutate_catalog():
    bindings, grants = [bind()], [grant()]
    catalog = TenantCatalog(bindings, grants)
    bindings.clear()
    grants.clear()
    assert catalog.authenticate("a" * 32).tenant_id == "a"
    with pytest.raises(TenantConfigurationError):
        TenantCatalog(catalog.bindings, catalog.credentials, max_tenants=0)


def test_pack_selection_reordering_duplicates_and_trust_order_are_equivalent():
    first = configuration()
    first.ontology.pack_dirs = ["tests/fixtures/packs/crm"]
    first.ontology.packs = ["pdlc", "crm"]
    first.ontology.trusted_sources = ["webhook:github", "webhook:jira"]
    second = first.model_copy(deep=True)
    second.ontology.packs = ["crm", "pdlc", "crm"]
    second.ontology.trusted_sources = ["webhook:jira", "webhook:github"]
    assert bind(settings=first).bundle_digest == bind(settings=second).bundle_digest


def test_unused_backend_credential_rotation_does_not_reinterpret():
    settings = configuration()
    first = bind(settings=settings)
    settings.redis.password = SecretStr("rotated-redis-secret")
    settings.neo4j.password = SecretStr("rotated-neo4j-secret")
    settings.neo4j.username = "rotated-user"
    assert bind(settings=settings).bundle_digest == first.bundle_digest


def test_consumed_archive_path_matches_validated_namespace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = configuration()
    settings.archive.enabled = True
    settings.storage.archive = "fs"
    settings.archive.fs_base_path = "relative-archive"
    binding = bind(settings=settings)
    assert binding.settings().archive.fs_base_path == str(tmp_path / "relative-archive")
    assert binding.archive_namespace == ("fs", *(tmp_path / "relative-archive").parts)


def test_independent_duplicate_binding_id_and_cardinality_rejected():
    first, second = bind("a"), bind("b")
    with pytest.raises(TenantConfigurationError, match="binding_id"):
        TenantCatalog(
            [first, replace(second, binding_id=first.binding_id)], [grant("a"), grant("b")]
        )
    with pytest.raises(TenantConfigurationError, match="bound"):
        TenantCatalog([first, second], [grant("a"), grant("b")], max_tenants=1)
