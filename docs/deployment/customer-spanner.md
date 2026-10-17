# Run Engram against customer-owned Spanner

This operator path uses Engram's existing API, tenant bindings, storage adapters and
workers. It does not import pilot scripts, choose a Portiq target, provision cloud
resources or insert graph artifacts. Tracked by [#86](https://github.com/arunmenon/Engram/issues/86).

## Prerequisites

Before running cloud commands, the operator must supply:

- An authorized GCP project, instance and **dedicated empty GoogleSQL database**.
  Required Graph, full-text and vector capabilities must be available. This is an
  initial deployment workflow, not adoption of populated data or an upgrade tool.
- Customer-approved Application Default Credentials (ADC) and network access from
  the API and every worker to that target. No service-account key is bundled.
  Schema installation requires DDL authority; runtime needs database reads/writes,
  transactions and schema inspection. The operator assigns permissions according
  to its IAM policy; this tool does not grant them. Runtime must not have authority
  to select another tenant's database.
- A Python 3.12+ source checkout and its locked dependencies. From the checkout run
  `uv sync --frozen --extra dev --extra embedding --extra spanner`, then activate
  `.venv`. Use the same installed source and packs in every process.
- Model-provider credentials/environment supported by the selected LLM provider,
  outbound provider access and the selected embedding model downloaded/available.
  The example selects `gpt-6-luna`; access must be authorized by the hosting
  organization. No call-count or spending limit is introduced here.
- A high-entropy producer bearer token supplied through the named environment
  variable (`CUSTOMER_A_TOKEN` in the example), on the API and verification host.
  Do not paste real tokens into manifests, Git or shell history. Load them through
  the organization's secret mechanism. ADC and model credentials are separate.
- A private configuration directory/volume and process supervision for the API
  and **five independent worker processes**. TLS, enterprise identity integration,
  ingress and managed supervision are hosting responsibilities, not provided by
  these local commands. The default API binds only to loopback.

A missing prerequisite is a failure to resolve, not permission to fall back to a
pilot database, emulator, in-memory backend or another model.

## 1. Prepare one configuration

Copy [the example manifest](customer-spanner.example.json) to a private operator
location, replace the resource placeholders and choose the tenant identity. The
example uses mandatory Core alone: empty optional pack lists do not remove Core.
Select optional packs using the existing `ontology.packs`/`builtin_packs` settings
and their actual declarations; do not infer a capability from a pack name.

```sh
python -m context_graph.deployment prepare \
  --manifest /private/customer.json \
  --output /private/customer.engram-resolved.json
python -m context_graph.deployment inspect \
  --config /private/customer.engram-resolved.json
```

Preparation makes **no cloud calls**. It validates the binding and saves resolved
settings once, including any settings inherited from the preparation environment.
Review that environment before preparing. Later `CG_*` changes cannot redirect
that artifact. All five storage ports must select Spanner; schema checking stays
on and implicit creation stays off. An ambient `SPANNER_EMULATOR_HOST` is refused.

The resulting file is atomically created owner-private (0600), never overwritten,
and ignored by Git when named `*.engram-resolved.json`. It can contain sensitive
settings: do not publish or print it. `inspect` shows safe target/pack/model/hash
metadata and token variable **names**, not their values. Protect backups and mount
copies with the same owner-private permissions. API bearer tokens remain env
references. Provider and ADC secrets stay in the approved runtime environment.

The artifact pins packaged Python/YAML source and the composed bundle digest.
Changes to source, packs or frozen settings are refused. Repreparing a new file
**does not authorize replacing an existing database owner**. This initial-deploy
CLI does not implement epoch transitions, adoption, migration or upgrades.

## 2. Install schema and establish ownership

Print DDL for the exact selected embedding dimensions and tenant-control table:

```sh
python -m context_graph.deployment schema \
  --config /private/customer.engram-resolved.json --tenant customer-a \
  > /private/customer-schema.sql
```

Review it, then explicitly apply it to the authorized empty database using your
DDL credentials. This command is an example with placeholders, not an instruction
to create resources in an arbitrary project:

```sh
gcloud spanner databases ddl update customer-a \
  --project=customer-project --instance=customer-instance \
  --ddl-file=/private/customer-schema.sql
```

Then initialize and inspect ownership using the same resolved configuration:

```sh
python -m context_graph.deployment initialize \
  --config /private/customer.engram-resolved.json --tenant customer-a \
  --confirm-database projects/customer-project/instances/customer-instance/databases/customer-a
python -m context_graph.deployment check \
  --config /private/customer.engram-resolved.json
```

Initialization validates the existing schema and bootstraps the ownership fence.
A matching active owner is idempotent. Wrong owner/epoch, incompatible schema or
populated unowned data is refused. It never installs/repairs DDL, clears data or
adopts an occupied database. `check` reads ownership, registered consumer groups,
pending deliveries and dead letters. It is a snapshot; zero pending work alone
cannot prove worker execution or correct retrieval.

## 3. Start the API and all workers

On every host mount the same private file and install the same source/model assets.
The API needs the bearer variables for its catalog; workers need their database
and provider credentials, not the application's bearer token.

```sh
python -m context_graph.deployment serve \
  --config /private/customer.engram-resolved.json --host 127.0.0.1 --port 8000
```

Run each of these as a separate supervised process (not sequentially in one shell):

```sh
python -m context_graph.deployment worker --config /private/customer.engram-resolved.json --tenant customer-a --consumer projection
python -m context_graph.deployment worker --config /private/customer.engram-resolved.json --tenant customer-a --consumer enrichment
python -m context_graph.deployment worker --config /private/customer.engram-resolved.json --tenant customer-a --consumer extraction
python -m context_graph.deployment worker --config /private/customer.engram-resolved.json --tenant customer-a --consumer consolidation
python -m context_graph.deployment worker --config /private/customer.engram-resolved.json --tenant customer-a --consumer pack_extraction
```

These are Engram loops polling through the subscription adapter; Spanner stores
events and delivery state, not executing workers. The API and workers independently
verify the same database/binding fence. Shutdown uses their existing SIGTERM/SIGINT
handling and closes stores. Start-up schema/ownership/provider failures must be
investigated; changing the target to make a health check pass is not recovery.

For multiple tenants add distinct tenant/binding/database entries and credential
references, repeat initialization per tenant, serve the catalog once, and launch
five workers per tenant. The manifest rejects duplicate databases, bindings,
credential IDs and token-variable references. This setup does not establish
fine-grained team/repo authorization within a tenant.

## 4. Application touchpoints

Clients send `Authorization: Bearer <producer token>`. The catalog determines the
tenant and source identity. Optional `X-Tenant-ID` is only a consistency hint;
clients cannot supply a project, instance or database to route a request.

| Operation | Interface and interpretation |
|---|---|
| Submit an event/batch | `POST /v1/events`, `POST /v1/events/batch`; accepted ledger input is not yet a processed graph |
| Read event graph | `POST /v1/query/subgraph`; check typed nodes, links and provenance, not just HTTP 200 |
| Read a session | `GET /v1/context/{session_id}`; only data supported by bound capabilities |
| Read domain artifacts | `POST /v1/query/artifacts`; requires applicable packs and bundle qualification |
| Read User information | `/v1/users/{user_id}/...`; User capability and current admin-role requirement apply |
| Inspect bound service | `/v1/health`, `/v1/ontology`; auth and tenant binding still apply |
| Delivery snapshot | Operator `check`; group registration/pending/DLQ are not a public processing guarantee |

The tenant factory's global `/health` reports readiness. Its global metrics and
unbound webhook routes are deliberately unavailable; do not assume legacy import,
maintenance or native webhook routes work through this factory. Artifact serving
keeps its evaluation gate. If an operator explicitly selects a development-only
unevaluated override, record it; it is not pack-wide qualification.

Bearer rotation can reload catalog grants without changing the bundle binding
(restart the API). Frozen settings/source changes require a new reviewed artifact
and the appropriate ownership transition workflow; do not edit the resolved JSON.

## 5. Run and retain a deployment proof

With all processes running on a dedicated quiet target:

```sh
python -m context_graph.deployment_verify \
  --config /private/customer.engram-resolved.json --tenant customer-a \
  --base-url http://127.0.0.1:8000 \
  --confirm-database projects/customer-project/instances/customer-instance/databases/customer-a \
  --output /private/customer-proof-01.json
```

The verifier sends one fresh observation through HTTP, waits for its exact Event
and enrichment to be retrieved through HTTP, checks its Spanner provenance and
ledger receipt, and audits all five groups for zero lag/pending/dead letters.
Read-only storage inspection provides corroborating evidence; it does not create
or repair graph state. Then it tests exact replay, conflicting content and a wrong
tenant hint. A failed check/timeout fails the proof and retains private evidence.
HTTP redirects are refused. Inputs and output remain in the database/report; no
cleanup occurs. Choose a fresh evidence filename on each attempt.

This proves a Core deployment/delivery path, **not** optional pack behavior, LLM
extraction quality, ANN performance, two-tenant concurrent isolation or enterprise
identity integration. An ACK may mean no applicable extraction. Those claims
require their own declared journeys. This proof must run on an authorized
**non-Portiq project** to satisfy #86. Local tests and the earlier Portiq pilot do
not fulfill that acceptance gate. No such target has yet been supplied.
