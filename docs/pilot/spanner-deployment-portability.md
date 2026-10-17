# Deployment portability: customer-owned Spanner

Tracked in [issue #86](https://github.com/arunmenon/Engram/issues/86) under umbrella #34.

Engram must be deployable inside another organization's environment, with that organization's project, Spanner instance, database and credentials. PayPal is an example deployment destination, not an already configured or verified target. Portiq must remain one pilot configuration.

## What the current code establishes

`SpannerSettings` accepts `CG_SPANNER_PROJECT`, `CG_SPANNER_INSTANCE` and `CG_SPANNER_DATABASE`. `open_database` constructs Google's client from the configured project, then selects that instance/database. Credentials come from Application Default Credentials. The storage factory passes the selected handle to the Spanner adapters. A source search found no Portiq project/instance/service-account literals under `src/`. This is code-level configurability, not a completed cross-project deployment test.

Tenant bindings record the complete database resource and verify its ownership/configuration. The tenant ASGI factory accepts an explicit catalog; API startup verifies bound owners and workers use the same bindings separately. A request must resolve through its authorized binding. An application must never choose an arbitrary project/database through a request field.

The pilot/experiment operators are deliberately different: `engram_pilot_first_run.py`, `engram_spanner_empty_activation.py` and `engram_spanner_tenant_control.py` contain Portiq targets and authorization guards. Those guards protect retained experiments; deleting them is not the portable deployment solution. A reusable deployment entrypoint must accept explicit configuration without depending on those scripts or importing their target constants.

For a Spanner deployment, setting the target alone does not select storage backends. The current configuration also requires the five backend selections, for example:

```dotenv
CG_SPANNER_PROJECT=customer-project
CG_SPANNER_INSTANCE=customer-instance
CG_SPANNER_DATABASE=engram-customer
CG_STORAGE_EVENT_LOG=spanner
CG_STORAGE_SUBSCRIPTION=spanner
CG_STORAGE_GRAPH=spanner
CG_STORAGE_KEYWORD_INDEX=spanner
CG_STORAGE_VECTOR_INDEX=spanner
CG_SPANNER_CREATE_IF_MISSING=false
CG_SPANNER_ALLOW_CREATE_ON_INSTANCE=false
CG_SPANNER_CHECK_SCHEMA=true
```

These are configuration placeholders, not a complete launch command: the schema, tenant catalog/owner bindings, credentials, pack/model selection and worker launch must also be supplied. ADC credentials must come from the customer-approved environment, not a bundled Portiq key.

## One bounded portability slice

1. **Define the deployment inputs.** Publish one configuration example with placeholders for project, instance, database, selected packs, authentication/bindings, worker startup and model configuration. No Portiq service account, database or operator script may be required by the product launch path. Use the current settings/adapters first.
2. **Make setup repeatable.** Document and, where absent, supply a supported operator entrypoint for schema/control initialization and API/worker launch. It may be a CLI/configuration interface; business applications do not need a database-provisioning HTTP endpoint. Preserve existing experiment guards.
3. **Document the application APIs.** Show authenticated write, processing readiness and read examples using the same deployed service. State pack applicability, roles, response/evidence contracts and currently unsupported routes. Do not treat a Python constructor as finished enterprise onboarding.
4. **Verify configuration and isolation locally.** Prove the SDK target and all five Spanner storage ports come from the configured binding. Reject mismatched ownership, missing credentials/permissions and incompatible schema with clear failures. No fallback to Portiq or another tenant. Local doubles prove configuration selection only.
5. **Run an authorized second-project proof.** On a customer-approved non-Portiq project/instance/database, use ordinary authenticated ingestion, workers and retrieval. Verify accepted source, typed graph, exact evidence, readiness, replay and tenant refusal behavior. Retain manifests, source/configuration hashes and failures; get independent review. Another database inside Portiq does not satisfy this cross-project proof.

Done means an operator can follow the published launch/setup instructions without the pilot author's hidden worktree or Portiq access, and the second-project proof is recorded. A customer environment that has not been supplied remains an external prerequisite; it must not be reported as passed.

## API touchpoints

| Application need | Current interface to document and verify |
|---|---|
| Submit activity | `POST /v1/events`, `POST /v1/events/batch` |
| Retrieve event/session context | `POST /v1/query/subgraph`, `GET /v1/context/{session_id}` |
| Retrieve PDLC artifacts and relationships | `POST /v1/query/artifacts`, when the bound packs support it |
| Retrieve User information | `/v1/users/{user_id}/...`, when User is enabled and the required role permits the operation |
| Inspect service/ontology state | `/v1/health`, `/v1/ontology`, within the deployed authentication/tenant contract |
| Configure tenant/database ownership and workers | Existing binding/catalog/control and worker interfaces; packaged `context_graph.deployment` manifest/CLI; see operator guide |

These are service APIs. Google's Spanner SDK remains behind Engram's storage ports; integrating applications should not insert graph rows or manipulate worker delivery tables directly.

## Prerequisites for a customer-hosted proof

The operator supplies an authorized target, the current GoogleSQL schema and required Spanner Graph/search/index capabilities, a dedicated schema/database arrangement, credentials and required database permissions, and network access from the API/workers. Provisioning authority and steady-state runtime permissions must be stated separately. Existing nonempty databases must pass schema/ownership checks; “any instance” does not mean silently using arbitrary tables or unsupported features.

The hosting organization must also select permitted model/embedding providers, secret delivery and network access. The pilot's OpenAI/Luna account and impersonated Portiq service account are not customer deployment requirements. Enterprise identity integration, remote service exposure and independent human onboarding must be verified for that deployment rather than inferred from the local pilot. No customer resources are created by this assessment, and no historical-data migration enters the slice.

## Implementation checkpoint — 2026-10-17

The reusable setup/launch surface is now implemented in
`src/context_graph/deployment.py`, with a real-service proof runner in
`src/context_graph/deployment_verify.py`. Follow the
[customer operator guide](../deployment/customer-spanner.md) and its versioned
example manifest. It reuses the existing tenant factory, storage adapters, schema,
ownership fence and workers. Pilot guard scripts remain unchanged.

Preparation freezes private settings once and pins actual shipped Python/YAML
source plus pack/configuration digests. Setup requires explicit full-resource
confirmation and refuses unowned populated databases, schema/owner mismatch,
emulators and implicit creation. No historical migration or privileged
provisioning API was added. All setup/API/worker processes use the same artifact.

Local tests establish configured target selection, ADC client construction, five
storage ports sharing the binding, API/worker owner refusal, private configuration,
secret-safe failures and the proof runner's rejection of false-pass conditions.
These tests use doubles and are not cross-project deployment proof. Independent
review and final test evidence are recorded in `issue86-verification.md`.

**Open acceptance prerequisite:** an authorized non-Portiq project/instance/database
and credential method have not been supplied. No customer resources were created
or modified. #86 stays open until the documented real HTTP/worker/Spanner proof
runs there and its retained evidence is reviewed.
