# Starting the tenant API

`context_graph.api.tenants.create_tenant_app(catalog)` now creates the shared
ASGI application rather than refusing unconditionally. Supply a validated
`TenantCatalog` containing immutable bindings and server-owned credential grants.
An ASGI server must run its lifespan; constructing the application alone does not
make it ready. The existing single-configuration entry point is unchanged.

Every tenant child uses its pinned settings and bundle to open Spanner stores.
The store factory checks schema, database identity, durable owner, epoch and
bundle fingerprint. The dispatcher then requires a fresh active read check
before marking the service ready. Missing or mismatched ownership is refused;
startup never adopts a database or changes its active bundle. If any child fails,
all opened children are closed and startup fails.

Authenticated credentials select the tenant. Tenant hints cannot override that
identity. API/admin role checks and the response guard remain enabled. Webhooks,
streaming imports, cursor queries and tenant metrics remain restricted as in the
existing dispatcher/guard. The factory starts no workers and performs no pack
activation. Workers must separately use the exact authorized tenant binding.

The catalog is fixed for the process lifetime. Configuration changes require
coordinated drain and restart. Shutdown drains the entire dispatcher; independent
tenant lifecycle and dynamic onboarding are not implemented by this change.

## Validation boundary

The public-factory tests exercise startup authorization failure/cleanup and
credential routing, hint mismatch, role separation and restricted paths using
recording children. Existing bound-child/store tests cover pinned construction
and database handshake refusal. These are local tests, not deployment evidence.

The earlier 2026-10-30 live checks against `engram-compat-target` verified database
fences and the HTTP response guard without changing existing rows or ownership.
They predate this factory change and do not establish public-service or two-tenant
cloud acceptance. Enabling this code does not deploy an API process or change the
existing database's active configuration.
