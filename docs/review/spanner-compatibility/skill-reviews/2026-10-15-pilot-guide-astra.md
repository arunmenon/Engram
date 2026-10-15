# Pilot guide accuracy and clarity review — 15 October 2026

## Verdict and scope

No accuracy blocker found in the bounded chapter or the refreshed Memory, consolidation and tenant sections. Two small explanatory fixes are recommended before delivery; neither requires runtime work or a redesign. Browser/render verification remains a separate required check: this review inspected HTML, JavaScript and generation logic, but did not operate a browser or execute runtime/database tests.

Applied `explain-with-depth` as a review workflow. Reviewed `docs/guide/pilot-chapter.html`, all 49 entries in `pilot-journey-explanations.json`, `scripts/build_pilot_guide.py`, and the generated guide's refreshed sections and navigation script. Grounded key claims in the three discovery catalogs and README, Memory and tenant verification records, and targeted current source (`settings.py`, `worker/consolidation.py`, `retrieval/episodes.py`, `api/tenants.py`). This is not a full runtime audit or verification that the proposed pilot works.

## Recommended minimal fixes

1. **Missing explanation: give the consolidation threshold its meaning.** In `engram-architecture.html`, section `worker-deep-dive-consolidation`, “reflection threshold is 150” has no unit or causal explanation. A developer could reasonably read it as 150 Events and choose incorrect fixture settings. Current `worker/consolidation.py:186` uses event count × 5 as an importance proxy; `memory-episodes-verification.md:13` explicitly explains roughly thirty Events. Add one sentence saying that 150 is a proxy threshold, with current eligibility using event count × 5, roughly thirty Events. Preserve the distinction between default settings and accelerated verification settings.

2. **Missing explanation: shared probes expose an untranslated shorthand.** `pilot-chapter.html`, the `data-pilot-catalog="c"` selector and `choose()` renderer, renders raw shared-catalog paragraphs directly. C01/C02 already expose `P/S/E/C/X`, `X ACK`, and `Monitoring 403`; the A and B glossaries use different shorthand and do not define this shared sequence. A newcomer should not have to infer whether S means session extraction or Summary, or whether X is a failure. Add a short local glossary for the shared worker letters and explain ACK as acknowledgement at this location; expand “Monitoring 403” to the monitoring-access refusal and its diagnostic consequence, or move that operational phrase into optional technical detail. Keep the raw source catalog available.

## Accuracy and evidence checks

- The 25 A journeys, 24 B journeys and 18 shared probes agree with discovery. The chapter consistently labels them as candidates and distinguishes a specification from runnable fixtures.
- Test failure/rerun illustrations are labeled expected/illustrative, and the verification table says the pilot has not run. No example was promoted into measured proof.
- Belief/Goal actions remain explicit structured inputs. Session prose is not claimed to produce Goals automatically; domain artifacts do not acquire invented Memory links.
- Episode snapshots preserve exact membership and old snapshots. The late-event example is consistent with the documented 30-minute splitting rule. Ten-snapshot/500-reference limits and truncation are kept visible.
- Tenant routing is attributed to authenticated grants and pinned runtimes, with frozen-provider and cooperative-restart limits. `api/tenants.py` confirms the factory owns child API lifespans while workers start separately; the pilot's launch instructions correctly require workers as well.
- The five-worker explanation avoids implying five serial phases. Matching PDLC prose extraction and inapplicable A pack extraction are distinguished. Acceptance/ACK are not used as proof of useful extraction.
- Artifact lexical lookup is not described as artifact-vector retrieval. Exact traversal and natural-wording discovery receive separate verdicts.

## Generation and browser considerations

The generator obtains catalog counts and bodies from the versioned discovery files, validates 25/24/18, attaches teaching text by stable ID, escapes closing script sequences in embedded JSON, replaces the marked chapter, and rebuilds the 27-page selector. No blocking generation error was found by inspection. Teaching entries are trusted repository text inserted as HTML; if prose later includes literal markup characters, escape those teaching fields before insertion.

The chapter initializes an actual first family, first journey and first worker state, and provides prose alongside its diagrams. Page links target the existing guide sections. Check the finished guide in a browser for all eight new pages, both tenant controls and all four steps, A/B/shared family changes, technical-detail expansion, narrow-screen SVG scrolling and keyboard navigation. Do not open `pilot-chapter.html` as a standalone finished artifact: it is a template containing the unresolved `@@PILOT_DATA@@` marker.

## Optional polish

- Expand HLD/LLD at first use in B02's teaching sentence, and define paraphrase as “the same question in different words” on the retrieval page. The surrounding content is already understandable without changing architecture detail.
- Give support verdict/prerequisite a compact visible line outside A/B's technical disclosure when a selected journey is a gap or product decision; current general caveats are accurate, but per-journey applicability would be faster to inspect.
- Longer term, avoid hard-coding the page count in the generator if the guide grows. It is a useful present guard, not a current defect.

## Comprehension checks (review prompts, not learner-study results)

- **Newcomer:** Does a successful write mean Alice's preference is ready? Expected: no; the ledger accepts first, then the triggered extraction must return validated owner/source information, and a read must verify it.
- **Developer:** A test passes on rerun. Can the prior failed run disappear? Expected: no; separate execution identities, outcomes and supporting Events remain inspectable.
- **Implementation engineer:** What changes when an older Event bridges two activity groups? Expected: a new exact-membership Episode snapshot can appear; old snapshots remain, and bounded retrieval is not guaranteed to show a latest disjoint partition.
- **Changed condition:** Does a no-op pack-extraction ACK in Tenant A indicate failure or useful model extraction? Expected: neither by itself; no profile matches those packs, so that worker is inapplicable to prose extraction, while relevant workers require their own output evidence.
- **Evidence misconception:** Does prior tenant isolation verification establish real-model personalization quality? Expected: no; its frozen outputs support the bounded routing/data/lifecycle claims. The new actual-provider journey must establish quality separately.

## Coordinator disposition and rendered checks

Applied both requested clarity fixes: threshold units/count proxy and a local shared-probe glossary including ACK/Monitoring refusal. Also expanded HLD/LLD and escaped teaching strings before HTML insertion. Browser checks used the available Chrome/CUA Playwright surface after the installed CLI wrapper failed to expose playwright-cli. All eight new pages rendered; all 25 A/24 B/18 shared entries were reachable through their family selectors; both tenant worker states changed correctly; narrow-screen layout was checked at the 390px requested viewport (effective browser CSS width354), with no horizontal page overflow after fixing header sizing. Original screenshot and browser checks are inspection evidence, not a learner study or pilot execution proof.
