# Runbook: writing and onboarding an ontology pack

A pack teaches Engram a new domain: its types, the events that describe them, how those events become graph writes, and how questions about them are answered (ADR-0018). The engine has no code for any domain pack. This runbook takes a pack from an empty file to answering questions in production.

The worked example is `tests/fixtures/packs/crm/`: a small CRM pack (`crm.pack.yaml`) and its evaluation set (`crm.eval.yaml`). `tests/unit/test_pack_toy_end_to_end.py` runs it end to end on every backend with no other domain pack active. Read the two files alongside this page. `src/context_graph/ontology/packs/pdlc.pack.yaml` is the large real example.

## 0. What you get for free, and what you must not redeclare

Core (`core.pack.yaml`) always loads, together with `memory` and `user`. These three base packs describe the schema the code itself writes. They always load from the built-in directory: a pack directory holding a file with one of their names is refused.

Core provides:

| Thing | What the engine does with it |
|---|---|
| `Lifecycled` interface | The projector writes `status` (the lifecycle's initial state on creation) and `status_changed_at`; transitions move `status`. **A type with a `lifecycle` must use it.** |
| `Sourced` interface | The projector sets `source_trust` to `trusted` or `untrusted` from `CG_ONTOLOGY_TRUSTED_SOURCES`, never from content. The `untrusted_uncorroborated` admission rule reads it. |
| `Claim`, `Anchored`, `Versioned` | Shared property shapes: confidence and method; source URI and hash; version. |
| `DERIVED_FROM` | Every node a rule upserts gets an edge to the Event that wrote it (provenance), without declaring anything. |
| `SUPERSEDES`, `CONTRADICTS` | Declared with no endpoints. Add yours under `extends_core_edges`, as the crm pack does for `SUPERSEDES: {from: [Deal], to: [Deal]}`. |
| `Event`, `Entity` | Use them as edge endpoints with the `core:` prefix (`core:Event`). |

Names are global across every active pack: types, edges, events, intents and interfaces. Two packs declaring the same name cannot load together, so never redeclare `Sourced` or `Lifecycled`. Pack names are lowercase letters, digits and underscores (`incident_mgmt`, not `incident-mgmt`). The node type `OntologyState` is reserved.

## 1. Write the pack

Create `<name>.pack.yaml` in a directory of your own. Its sections, in the order of the crm example:

1. **`pack`**: `name`, `version` (semver, starting at 1.0.0), `requires` (at least `core>=1.1`), `owner`, `description`.
2. **`types.nodes`**:
   - `key`: the identity the source system already uses. For example, a deal is `[deal_id]`; a pull request is `[repo, number]`.
   - `interfaces`, `properties` (`string`, `text`, `int`, `float`, `bool`, `datetime`, `list<…>`, or `{enum: [...]}`), and `text_fields` (what word search reads).
   - `lifecycle`, when the type has states. List the states that mean "no longer current" in `superseded_states`: the crm pack sets `[replaced]`. Retrieval leaves such nodes out unless an intent's admission rule keeps them.
3. **`types.edges`**: `from` and `to` type lists. Add `requires: [confidence, method, link_status]` for links that may be inferred (the PDLC link policy).
4. **`events`**: every event type the pack accepts, dot-namespaced under one prefix of its own (`crm.*`).
   - The pack owns that namespace: undeclared `crm.*` events are rejected at ingest (422), and no other pack may declare events in it.
   - Payloads are not schema-checked. A value that does not fit a property's type is dropped when it is written.
5. **`projection`**: one rule per event type, which can:
   - `upsert` nodes by key;
   - make a `transition` to a state, guarded by `only_from`;
   - draw `edges`, `to` a node by key, `to_each` over a list, or `to_latest` (the newest match no later than the event).
   
   The value language: `$.payload.field`, `$event.occurred_at`, `regex(...)`, `regex_all(...)`, `match(...)`, `map(...)`, `sha256(...)`, `each(...)`. Patterns are bounded to 0.25 s per match; a slow pattern dead-letters its event. An edge's `from` can be found by `match` when its target is named by key, as PDLC's merge rule does to link earlier deployments.
   
   **Upsert the node in every rule that changes it.** Provenance is written for upserted nodes, so a rule with a bare transition records the new state but not which event set it. The crm `won`, `lost` and `replaced` rules upsert the deal for this reason.
6. **`retrieval`** (optional; needed if agents will ask questions):
   - `seed_types`: the types a question can name.
   - `key_patterns`: how questions name a type by key, when its keys do not look like `PAY-341`, a path, a version or `#N`. The crm pack declares `Deal: 'D-\d+'`, so "deal D-7" finds `Deal:D-7`.
   - `intents`: `keywords`, `weights` over edges, and optionally `max_depth`, `direction` (`inbound`) or `prefer_types`. An intent with `plugin: missing_links` answers "which X have no Y" as a set difference. It is the only plugin; another name is refused.
   - `admission`: only the rules `superseded_or_reversed`, `untrusted_uncorroborated` and `proposed_links` exist, and an unknown rule or setting is refused. If several packs declare a rule, their `include_for_intents` lists are combined.
   
   Leave out `untrusted_uncorroborated` unless your events come from a trusted source (step 3). Otherwise answers keep only the nodes the caller named by id, and everything else is hidden as untrusted.

Fields that load but are not implemented yet are listed at startup as `ontology_setting_not_implemented` warnings: `embed_fields`, `extraction.derived_proposals`, `lifecycle.decay`, `lifecycle.terminal_states_reduce_importance`, link policy settings other than `applies_to` and `link_status`, and `mappings`. Do not rely on them.

## 2. Check it loads

```
CG_ONTOLOGY_PACK_DIRS=/path/to/packs CG_ONTOLOGY_PACKS=crm python -m context_graph.ontology status
```

Every problem is reported at once: an unknown type, a rule for an undeclared event, a key that does not match the type's key, a lifecycle without `Lifecycled`, a bad pattern. `CG_ONTOLOGY_PACKS` lists every domain pack to run (`pdlc,crm`; `pdlc` is the default). Order does not matter: packs are ordered by their requirements, then by name.

## 3. Get events in

- **Generic ingest**: `POST /v1/events` or `POST /v1/events/batch` (up to 1,000 events) with your declared event types and the payload your rules read. The crm test ingests this way.
- **Trust**: add the agent id your importer uses to `CG_ONTOLOGY_TRUSTED_SOURCES` (comma-separated). Events from other agents produce `untrusted` nodes. Agent ids starting with `webhook:` are reserved for the signed webhook routes and refused on generic ingest.
- **Webhooks**: only GitHub and Jira have routes (`/v1/webhooks/{github,jira}`). A new tool needs an adapter in `sources/` and the route.

## 4. Write the evaluation set

An intent's weights are not trusted until its evaluation set passes on the deployment's graph (decision 10). Until then:

- the pack's intents are not used by `POST /v1/query/artifacts`;
- the weights on its edges are not used either;
- naming one of its intents returns 409;
- every response lists the pack in `meta.eval_pending`.

This holds from the very first deploy. `CG_ONTOLOGY_SERVE_UNEVALUATED=true` turns the check off for development only.

Write `<name>.eval.yaml` next to the pack, as in `crm.eval.yaml`. It holds questions about your real data and the node ids that answer them, with an optional `answer` reading (a node type, or retrieval reasons such as `proactive` or `no_link`). Quote every query: YAML reads ` #` as the start of a comment, and the loader refuses an unquoted query containing it. Set `min_f1` just under what the set scores, so the gate catches regressions.

## 5. Deploy

1. Deploy the API and workers with the new `CG_ONTOLOGY_PACKS`, `CG_ONTOLOGY_PACK_DIRS` and `CG_ONTOLOGY_TRUSTED_SOURCES`.
2. The projection worker reconciles at start. On a graph that already records other packs, adding a pack is a mapping change: the worker replays the pack's event types from the ledger. Run one projection replica while it does.
3. Ingest your history (step 3), and let the worker project it.
4. Run the gate and record its result:

   ```
   python -m context_graph.ontology evaluate --record
   ```

   When every set passes, `eval_pending` is cleared and, within `CG_ONTOLOGY_EVAL_STATE_TTL_S` (30 s), the API uses the pack's intents. If a set fails, the result is recorded and the pack stays pending.

## 6. Change it later

Bump `version` for every content change. `python -m context_graph.ontology status` shows how the graph will be brought to the new packs:

| Kind | Examples | Applied |
|---|---|---|
| additive | new types, properties, events, intents, keywords | hot |
| mapping | a projection rule added or changed | the worker replays the affected event types |
| breaking | a type, edge, key, state or rule removed | blue/green rebuild into a fresh graph, gated on the evaluation sets |

A breaking change needs a new major version; anything else, a new minor version. A rebuild:

```
python -m context_graph.ontology rebuild --target CG_KEY=VALUE ...
```

A change to a pack's `retrieval` section puts it back to pending until `evaluate --record` passes again.
