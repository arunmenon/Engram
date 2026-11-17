# M2a: catalog-based domain pack selection

The workbench now lists packaged, engine-loadable packs instead of hardcoding PDLC. CRM and PDLC are selectable with descriptions from their pack metadata. Existing PDLC drafts remain readable. Selection is saved and survives reload/reauthentication.

The catalog is a local module and packaged files, not a registry service. The CRM file copies M0's adapted contracts while preserving the original fixture's email-based contact identity. It does not replace the separate authored CRM draft with stable contact IDs. Source: M0 baseline crm-workbench.json, original tests/fixtures/packs/crm/crm.pack.yaml. Expectations remain author-reviewed.

Composition still rejects missing dependencies, duplicate type names and authored packs that shadow selected packs. Unknown selections fail API validation. The existing authored-story digest prevents missing snapshots from silently using PDLC. Packs without declared lifecycle states no longer require an authored-pack lifecycle attestation; identity confirmation remains required. The UI no longer offers a fabricated event template as an example.

## Verification and limitations

Evidence and reproducibility: `output/playwright/ai-native-onboarding/M2a/catalog-20261106/README.md`.

- 117 targeted backend tests passed. Final catalog suite: 11 passed, including one additional combined-domain test.
- 13 frontend tests passed; workbench build, Ruff and targeted mypy passed.
- Headed Chrome: selection, keyboard toggle, persistence through reload/sign-in, existing PDLC selection, narrow layout, neutral sample intake and no-lifecycle confirmation.
- Tests preserve authored incident/Northstar fixture behavior; this slice did not repeat a live Northstar authoring journey.
- No provider call, Spanner run, sandbox evaluation, production activation or full recovery-browser rerun.
- Implementer verification only. Independent review remains pending. Existing review-page density and F04 wording are not resolved by this slice.

## Fable re-review ask

Use the ai-native-ui-review skill, fresh reviewer-owned copies and the evidence identity above. Do not reuse implementation copies as acceptance cases. Verify selection is supplied by capabilities rather than a frontend PDLC branch; CRM contracts enforce all declared events; old PDLC and authored pack compatibility remain; unknown packs and composition conflicts fail clearly. Verify no-lifecycle confirmation is absent while identification remains required. Check keyboard, narrow layout and save/reload recovery. Keep functionality, clarity and AI-helpfulness verdicts separate. Do not infer live reasoning, cloud isolation or approval from these checks. Report issues without changing code or expected outcomes.
