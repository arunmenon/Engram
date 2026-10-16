# Pilot handoff quality review

Scope: the final pilot chapter in the 27-page HTML guide, team reproduction instructions,67-entry coverage map and P01–P12 verification record. Audience: an engineer who knows HTTP and database rows but is new to Engram. Applied `explain-with-depth` and `artifact-quality-gate`; this reviews concrete defects, not whether text was authored by AI. No numeric quality/slop score is inferred.

## Findings and dispositions

| Finding | Why it matters | Correction or explicit boundary |
|---|---|---|
| The guide still said selected failed/passed test outcomes were “not run”. | A stale result hides existing evidence. | Link the selected P01–P02 catalog/connected proof; distinguish the illustrative diagram from its exact executed payload. |
| Catalog descriptions did not show the actual recorded verdict beside the story. | A reader could mistake proposed coverage for a passing journey. | Every entry now shows observed behavior and a remaining boundary, generated from the same versioned coverage map. |
| “Full” C03 originally included unproved A earlier-session wording discovery. | B paraphrase proof cannot establish a different A read contract. | Changed to partial; explicitly identify the missing A behavior. |
| “Full” C06 originally implied every Entity/ID/text collision variant ran. | Event/Goal collision proof is narrower than the catalog contract. | Changed to partial; preserve the tested identifiers and name the unproved variants. |
| Early P11 references anticipated a reproduction result. | A planned run is not evidence. | The final references now link the accepted69-check run, source/import audit and declared reused environment. Human repetition stays external. |
| Coverage verdict terms could themselves become jargon. | A first-time reader needs to understand how to interpret partial evidence. | Added definitions for full, partial, diagnostic and external next to the checkpoint explanation. |
| Historical #64/#66/#68 issue text could lag accepted corrective evidence. | A team handoff needs current issue dispositions, not inferred closure. | Reconcile each against its exact acceptance criteria and Astra's assessment; do not close broader umbrellas. |

Source claims remain bounded: explicit producer actions are distinct from model inference; an ACK is not proof of a useful output; source-backed claims are not external truth; owner selection is not within-tenant authorization; native ANN participation is not performance or universal semantic discovery. Retained failed attempts remain failed. Illustrations and interactive teaching states are not live measurements.

## Reader comprehension checks

- Does selecting a pack create a separate worker? No. Shared workers apply the enabled rules/profiles; applicability and actual outputs need evidence.
- Does an accepted Event mean its projection is ready? No. Acceptance records the source; workers may still be pending or failed.
- Does successful B paraphrase retrieval prove A can find yesterday's session without its ID? No. They use different retrieval contracts; automatic A earlier-session discovery remains unproved.
- Does a passing test complete a Memory Goal? No. The Goal needs its explicit supported lifecycle action.
- Does an agent's clean-checkout run count as an independent human pilot? No. Technical reproduction and human/team repetition have separate verdicts.

## Rendered checks

The real browser navigated all 27 pages and required one visible page with a nonempty heading. It selected every family and all 67 catalog entries, requiring a visible recorded verdict and boundary. Both tenant worker explanations were exercised through all four teaching stages. Desktop screenshots and a 390px mobile reproduction screenshot were inspected; the mobile document has no horizontal overflow. The only observed initial browser console error was the local server's missing favicon, not an application-script exception. Navigation/rendering checks establish presentation usability, not new Engram journey coverage.

Evidence is retained under `output/playwright/p12/`. The builder checks exact catalog/coverage identifier equality. Relevant Python fixture checks passed; no new runtime behavior was introduced for P12. The final Astra review and GitHub reconciliation are recorded in the verification walkthrough.
