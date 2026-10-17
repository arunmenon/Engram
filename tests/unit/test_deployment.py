"""Customer target selection and fail-closed operator contracts; no cloud proof."""

import json
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from context_graph import deployment as operator
from context_graph.adapters.registry import open_stores
from context_graph.adapters.spanner.tenant_control import TenantFenceError
from context_graph.tenancy import TenantAuthorizationError, TenantConfigurationError
from tests.unit.test_tenant_store_binding import Database


def manifest():
    return dict(
        version=1,
        tenants=[
            dict(
                tenant_id="customer-a",
                binding_id="customer-a-v1",
                settings=dict(
                    spanner=dict(
                        project="customer-project",
                        instance="customer-instance",
                        database="customer-a",
                    ),
                    storage=dict.fromkeys(operator.PORTS, "spanner"),
                    ontology=dict(packs=[], builtin_packs=[]),
                    llm=dict(model_id="gpt-6-luna"),
                    embedding=dict(model_name="all-MiniLM-L6-v2", dimensions=384),
                    archive=dict(enabled=False),
                ),
            )
        ],
        credentials=[
            dict(
                credential_id="producer-a",
                tenant_id="customer-a",
                roles=["api"],
                source_id="customer-producer",
                token_env="CUSTOMER_A_TOKEN",
            )
        ],
    )


@pytest.fixture
def prepared(tmp_path, monkeypatch):
    monkeypatch.delenv("SPANNER_EMULATOR_HOST", raising=False)
    source = tmp_path / "manifest.json"
    target = tmp_path / "customer.engram-resolved.json"
    source.write_text(json.dumps(manifest()))
    operator.prepare(source, target)
    return source, target


def test_prepare_has_no_sdk_calls_and_pins_private_settings(prepared, monkeypatch):
    _, path = prepared
    original = operator.Deployment(path)
    expected = original.bindings[0].bundle_digest
    monkeypatch.setenv("CG_SPANNER_PROJECT", "unrelated-project")
    monkeypatch.setenv("CG_LLM_MODEL_ID", "unrelated-model")
    monkeypatch.setenv("CG_STORAGE_GRAPH", "redis")
    again = operator.Deployment(path)
    assert again.bindings[0].bundle_digest == expected
    assert again.bindings[0].settings().spanner.project == "customer-project"
    assert again.bindings[0].settings().llm.model_id == "gpt-6-luna"
    assert os.stat(path).st_mode & 0o777 == 0o600


def test_atomic_prepare_refuses_overwrite_without_changing_original(prepared):
    source, target = prepared
    before = target.read_bytes()
    with pytest.raises(operator.DeploymentError, match="exists"):
        operator.prepare(source, target)
    assert target.read_bytes() == before
    assert not list(target.parent.glob(".customer.engram-resolved.json.*"))


def test_private_file_and_source_drift_refused(prepared, monkeypatch):
    _, target = prepared
    target.chmod(0o644)
    with pytest.raises(operator.DeploymentError, match="private"):
        operator.Deployment(target)
    target.chmod(0o600)
    monkeypatch.setattr(operator, "runtime_identity", lambda: ("different-runtime", "test"))
    with pytest.raises(operator.DeploymentError, match="runtime differs"):
        operator.Deployment(target)


def test_resolved_setting_or_pack_drift_refused(prepared):
    _, target = prepared
    data = json.loads(target.read_text())
    data["tenants"][0]["settings"]["spanner"]["database"] = "unrelated-database"
    target.write_text(json.dumps(data))
    with pytest.raises(operator.DeploymentError, match="settings or pack"):
        operator.Deployment(target)


def test_token_refs_resolve_only_for_catalog_and_rotate_without_rebinding(prepared, monkeypatch):
    _, target = prepared
    deployment = operator.Deployment(target)
    monkeypatch.delenv("CUSTOMER_A_TOKEN", raising=False)
    with pytest.raises(operator.DeploymentError, match="Missing credential"):
        deployment.catalog()
    first, second = "first-customer-token-123", "rotated-customer-token-456"
    monkeypatch.setenv("CUSTOMER_A_TOKEN", first)
    before = deployment.bindings[0].bundle_digest
    assert deployment.catalog().authenticate(first).tenant_id == "customer-a"
    monkeypatch.setenv("CUSTOMER_A_TOKEN", second)
    catalog = deployment.catalog()
    assert catalog.authenticate(second).tenant_id == "customer-a"
    with pytest.raises(TenantAuthorizationError):
        catalog.authenticate(first)
    assert deployment.bindings[0].bundle_digest == before
    assert first not in target.read_text() and second not in json.dumps(deployment.inspect())


@pytest.mark.parametrize(
    "mutation",
    [
        lambda m: m.update(unrecognized="secret-value-do-not-print"),
        lambda m: m["tenants"][0]["settings"]["spanner"].pop("project"),
        lambda m: m["tenants"][0]["settings"]["storage"].update(graph="memory"),
        lambda m: m["tenants"][0]["settings"]["spanner"].update(check_schema=False),
        lambda m: m["tenants"][0]["settings"]["spanner"].update(create_if_missing=True),
        lambda m: m["tenants"][0]["settings"]["spanner"].update(emulator_host="localhost:9010"),
        lambda m: m["tenants"][0]["settings"]["embedding"].update(dimensions=768),
        lambda m: m["credentials"][0].update(roles=["superuser"]),
        lambda m: m["credentials"][0].update(tenant_id="unknown"),
        lambda m: m["credentials"][0].update(token_env="not-an-env-name"),
    ],
)
def test_invalid_manifest_refused_before_cloud(tmp_path, mutation, monkeypatch):
    monkeypatch.delenv("SPANNER_EMULATOR_HOST", raising=False)
    data = manifest()
    mutation(data)
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(data))
    with patch("google.cloud.spanner.Client") as client:
        with pytest.raises((operator.DeploymentError, TenantConfigurationError)):
            operator.prepare(path, tmp_path / "bad.engram-resolved.json")
        client.assert_not_called()


def test_unknown_nested_setting_and_duplicates_are_refused(tmp_path):
    source = tmp_path / "manifest.json"
    data = manifest()
    data["tenants"][0]["settings"]["spanner"]["wrong_field"] = "private-data"
    source.write_text(json.dumps(data))
    with pytest.raises(operator.DeploymentError):
        operator.prepare(source, tmp_path / "one.json")
    data = manifest()
    data["tenants"].append(data["tenants"][0].copy())
    source.write_text(json.dumps(data))
    with pytest.raises(operator.DeploymentError, match="Duplicate"):
        operator.prepare(source, tmp_path / "two.json")


def test_ambient_emulator_never_redirects_customer_binding(prepared, monkeypatch):
    source, target = prepared
    monkeypatch.setenv("SPANNER_EMULATOR_HOST", "localhost:9010")
    with pytest.raises(operator.DeploymentError, match="EMULATOR"):
        operator.Deployment(target)
    with pytest.raises(operator.DeploymentError, match="EMULATOR"):
        operator.prepare(source, target.with_name("another.json"))


async def test_all_five_ports_share_the_selected_customer_handle(prepared):
    binding = operator.Deployment(prepared[1]).bindings[0]
    database = Database(binding)
    with (
        patch(
            "context_graph.adapters.spanner.schema.open_database", return_value=database
        ) as opener,
        patch("context_graph.adapters.spanner.lifecycle.close_database") as close,
    ):
        stores = await open_stores(binding.settings(), tenant_binding=binding)
        try:
            assert opener.call_args.args[0].project == "customer-project"
            assert stores.event_log.database is database
            assert stores.graph._database is database
            assert stores.subscription("custom-group", "worker")._database is database
            assert stores.keyword_index._event_log is stores.event_log
            assert stores.vector_index._graph_store is stores.graph
        finally:
            await stores.close()
        close.assert_called_once_with(database)


def test_google_sdk_uses_configured_project_instance_database_and_adc(prepared):
    from context_graph.adapters.spanner.schema import open_database

    settings = operator.Deployment(prepared[1]).bindings[0].settings().spanner
    with (
        patch("google.cloud.spanner.Client") as client,
        patch("context_graph.adapters.spanner.lifecycle.prepare_cleanup"),
        patch("context_graph.adapters.spanner.schema.schema_differences", return_value=[]),
    ):
        client.return_value.instance.return_value.database.return_value.exists.return_value = True
        database = open_database(settings)
        client.assert_called_once_with(project="customer-project")  # ADC, no pilot token injection
        client.return_value.instance.assert_called_once_with("customer-instance")
        assert client.return_value.instance.return_value.database.call_args.args == ("customer-a",)
        assert database is client.return_value.instance.return_value.database.return_value


async def test_api_and_worker_refuse_same_mismatched_owner_and_close(prepared, monkeypatch):
    from context_graph.api.tenants import create_tenant_app
    from context_graph.worker.__main__ import _build_consumer

    deployment = operator.Deployment(prepared[1])
    binding = deployment.bindings[0]
    database = Database(binding)
    database.row[3] += 1
    monkeypatch.setenv("CUSTOMER_A_TOKEN", "customer-owner-test-token-1234")
    with (
        patch("context_graph.adapters.spanner.schema.open_database", return_value=database),
        patch("context_graph.adapters.spanner.lifecycle.close_database") as close,
        patch("context_graph.adapters.embedding.service.SentenceTransformerEmbedder"),
        patch("context_graph.adapters.llm.client.LLMExtractionClient"),
    ):
        with pytest.raises(TenantFenceError):
            await create_tenant_app(deployment.catalog())._start()
        with pytest.raises(TenantFenceError):
            await _build_consumer("projection", binding.settings(), tenant_binding=binding)
        assert close.call_count == 2


def test_initialize_requires_exact_confirmation_before_database_open(prepared, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "deploy",
            "initialize",
            "--config",
            str(prepared[1]),
            "--tenant",
            "customer-a",
            "--confirm-database",
            "wrong",
        ],
    )
    with patch.object(operator, "check_binding") as check:
        with pytest.raises(SystemExit) as error:
            operator.main()
        assert error.value.code == 1
        check.assert_not_called()


def test_bootstrap_is_nonadopting_and_failure_closes_handle(prepared):
    binding = operator.Deployment(prepared[1]).bindings[0]
    database = MagicMock(name="customer-database")
    database.name = binding.database_resource
    with (
        patch("context_graph.adapters.spanner.schema.open_database", return_value=database),
        patch("context_graph.adapters.spanner.tenant_control.verify_control_schema"),
        patch(
            "context_graph.adapters.spanner.tenant_control.TenantFence.bootstrap",
            side_effect=TenantFenceError("Populated tenant database requires explicit adoption"),
        ) as boot,
        patch("context_graph.adapters.spanner.lifecycle.close_database") as close,
    ):
        with pytest.raises(TenantFenceError):
            operator.check_binding(binding, initialize=True)
        boot.assert_called_once_with(database)
        close.assert_called_once_with(database)
        database.update_ddl.assert_not_called()


def test_inspection_and_cli_errors_never_print_credentials(prepared, monkeypatch, capsys):
    secret = "do-not-print-token-123456"
    monkeypatch.setenv("CUSTOMER_A_TOKEN", secret)
    monkeypatch.setattr(sys, "argv", ["deploy", "inspect", "--config", str(prepared[1])])
    operator.main()
    assert secret not in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["deploy", "check", "--config", str(prepared[1])])
    with (
        patch.object(operator, "check_binding", side_effect=PermissionError(secret)),
        pytest.raises(SystemExit),
    ):
        operator.main()
    output = capsys.readouterr()
    assert secret not in output.out + output.err
    assert "PermissionError" in output.err


@pytest.mark.parametrize("command", ["serve", "worker", "schema"])
def test_operator_delegates_same_resolved_binding(prepared, monkeypatch, capsys, command):
    _, target = prepared
    monkeypatch.setenv("CUSTOMER_A_TOKEN", "operator-producer-token-123")
    args = ["deployment", command, "--config", str(target)]
    if command != "serve":
        args += ["--tenant", "customer-a"]
    if command == "worker":
        args += ["--consumer", "projection"]
    monkeypatch.setattr(sys, "argv", args)
    if command == "serve":
        with patch("uvicorn.run") as launch:
            operator.main()
            assert launch.call_args.kwargs == {"host": "127.0.0.1", "port": 8000}
    elif command == "worker":
        from unittest.mock import AsyncMock

        with patch("context_graph.worker.__main__.run_worker", new_callable=AsyncMock) as launch:
            operator.main()
            assert launch.call_args.args == ("projection",)
            binding = launch.call_args.kwargs["tenant_binding"]
            assert binding.settings().spanner.project == "customer-project"
    else:
        operator.main()
        ddl = capsys.readouterr().out
        assert "CREATE TABLE Events" in ddl
        assert "Tenant" in ddl


def test_duplicate_consumer_groups_refused(tmp_path, monkeypatch):
    monkeypatch.delenv("SPANNER_EMULATOR_HOST", raising=False)
    data = manifest()
    data["tenants"][0]["settings"]["consumer"] = {
        "group_projection": "shared",
        "group_enrichment": "shared",
    }
    source = tmp_path / "manifest.json"
    source.write_text(json.dumps(data))
    with pytest.raises(operator.DeploymentError, match="distinct"):
        operator.prepare(source, tmp_path / "private.engram-resolved.json")
