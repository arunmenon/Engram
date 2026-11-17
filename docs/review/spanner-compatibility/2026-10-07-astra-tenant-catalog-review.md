# Tenant catalog substrate review

2026-10-07. Read-only review of tenancy.py and focused tests against the approved tenant-routing design. No tests/cloud executed.

**Verdict: approve the pure catalog substrate for local development; no production tenant-service approval.** No blocking defect identified in its normal `TenantBinding.from_settings` construction and current non-serving scope.

Bindings retain immutable serialized settings and a detached ActiveBundle; fresh settings reconstruction does not borrow caller collections. Manifest loading bypasses path-keyed caches and the digest includes full pinned canonical manifests, selected processing, policy and engine revision. Manifest edits at unchanged paths/names/versions therefore produce a new identity without changing the original binding. Future runtime construction must consume `binding.bundle`; passing `binding.settings()` to the current factory alone would reload mutable files and lose that guarantee.

Catalog checks reject duplicated tenant/binding/database strings, unknown or uncredentialed tenants, duplicate credential IDs or token digests, excessive configured tenant count and overlapping normalized archive namespaces. Rotation with separate credential IDs for one tenant is permitted without cross-tenant ambiguity. API/admin roles remain explicit; authentication returns one principal or rejects, including mismatched hints. Stored token digests are hidden from repr and compared with constant-time equality. Explicit all-Spanner/schema-check/no-create validation is consistent with the planned fail-closed tenant mode.

Two nonblocking follow-ups before runtime integration:

- The digest excludes API/admin and webhook secrets, but still includes inactive Redis/Neo4j passwords because the remaining Settings JSON is hashed wholesale. Rotating those unused credentials changes interpretation identity. Either exclude all credential-only fields or document the digest's deliberately conservative behavior; the current rotation test proves only the explicitly excluded credentials.
- Filesystem namespace validation resolves an absolute path, while the retained settings preserve the original potentially relative path. Normalize the consumed archive path to that validated absolute value before future runtime construction, and keep archive-target policy server-owned. This slice does not freeze filesystem symlink changes or establish durable archive ownership.

Inspected local run `20261007-local-tenant-catalog-03/pytest.log`: **46 passed, 1 warning**, 4.37 seconds. Tests cover caller/env mutation, secret repr, manifest pinning, selection equivalence, credential rotation/ambiguity, unsafe database settings, epoch validation and namespace overlap. Additional useful cases are duplicate binding IDs independently of tenant IDs, distinct nonoverlapping archive prefixes, configured cardinality overflow, and direct-constructor rejection of inconsistent manually supplied settings/bundles if that constructor will be exposed beyond trusted code.

The settings snapshot contains credentials intentionally and must not be serialized into public catalog evidence. No dispatcher, source-signature bindings, production tenant startup, protected database ownership, epoch fences or durable two-database isolation are provided or claimed by this approval.

## Nonblocking refinement recheck

Both follow-ups are resolved in the intended factory path: unused Redis/Neo4j username/password fields are excluded from interpretation policy hashing, and `from_settings` stores the resolved absolute filesystem archive path in the consumed snapshot. GCS prefixes likewise retain the normalized outer-slash form used for namespace validation. Added regressions cover unused credential rotation, consumed filesystem path agreement, independent duplicate binding IDs and tenant-count overflow.

Inspected `20261007-local-tenant-catalog-04/pytest.log`: **49 passed, 1 warning**, 4.44 seconds. No tests/cloud executed by this reviewer. Approval of the pure catalog substrate remains unchanged; future runtimes must consume the pinned bundle, and production tenant isolation/fencing remains outside this disposition.
