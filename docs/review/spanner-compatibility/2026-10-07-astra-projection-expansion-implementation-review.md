# Projection expansion implementation review

2026-10-07 — Astra low, source-only review against the bounded expansion design. No tests/cloud executed.

**Verdict: one P2 preallocation path remains.**

`src/context_graph/domain/pack_projection.py:584` converts an arbitrary list-valued `match_any_prefix` into a tuple of strings without a prospective count check. A single known endpoint plus a huge prefix list can allocate the full projector-owned tuple while producing only one counted lookup. The approved design explicitly included this copy. Call `_check_expansion_count(len(value))` before tuple construction; add a small-limit regression demonstrating overflow before string conversion/materialization. Conservative rejection before filtering null entries is consistent with the other candidate limits.

The remaining reviewed paths use a fresh event-local plan shared across all subscriber rules, with incremental accounting for nodes, provenance edges, lifecycle states, endpoint stubs and lookup instructions. Direct Cartesian candidate size is checked before lazy pairing/property evaluation. Equal-length fanned endpoints use an index join that preserves original positions across invalid-key gaps. Strict key-list length rejection and empty/scalar behavior match the approved semantics. Exceptions discard the local plan rather than returning a partial domain plan.

The memory-worker regression checks common Event retention, absent bad-event domain writes, valid sibling output, DLQ and no pending deliveries. This supports event-local planning failure behavior, not atomic rollback of common writes or later adapter/application failures.

The bound is 10,000 planned operations, not unique rows, actual lookup-expanded edges, a whole flush, all expression allocations or total CPU/memory. Property-list alignment, null/order/ownership semantics and full #36 remain outside scope. Bound cloud execution must use an explicit new engine/binding transition; no old-owner adoption or cloud acceptance is implied.

## Prefix expansion recheck

**P2 resolved.** `_plan_lookup` now checks the candidate list length before filtering/string conversion or tuple construction. The new `NoConversion` string-subclass regression exercises four prefixes against a cap of three and requires the stable expansion refusal before `__str__` can run. Recorded local run05 ends **162 passed**.

**Approve the bounded projection expansion implementation with this local evidence.** No remaining finding in this recheck; no tests/cloud executed by reviewer. All above distinctions between planned operations, actual lookup-expanded writes, expression costs and broader #36 semantics remain unchanged.
