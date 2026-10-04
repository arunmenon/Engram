# PDLC pack: competency-question check (step 1)

**Date:** 2026-10-04
**Inputs:** [`competency-questions.yaml`](competency-questions.yaml) (30 questions), [`pdlc.pack.yaml`](pdlc.pack.yaml) (now v0.3)
**Caveat:** no internal users were available, so the questions come from the Jetstream document, published PDLC research (MOOSEDev, TraceDev, ProjectMem, EA-Graph), DORA metrics and the research-bus briefs. They are a reasoned stand-in for user interviews, not a replacement. Step 2 (mapping a real Apache project) is the check against reality.

## Result

| Check | Result |
|---|---|
| Questions answerable with pack v0.2 | 19 of 30 |
| Questions answerable with pack v0.3 | 30 of 30, on paper (types, links and fields all present) |
| Types no question needs | none (all 16 used) |
| Links no question needs | none (all 23 used) |
| Fields a question needs but the pack lacked | 5, now added |

## What the check changed (v0.2 → v0.3)

| Added | Why | Questions |
|---|---|---|
| `APPLIES_TO` Decision → Service / Requirement / DesignElement / Change | a decision had an author and a successor but nothing saying *what it is about*, so "which decisions apply here?" had no answer | CQ01, CQ02, CQ08, CQ13, CQ15 |
| `CITES` Spec / Change → Decision / Constraint / DesignElement / Lesson / Requirement, with `pinned_position` | Jetstream says a spec *references* knowledge and the reviewer must see it *as it was*; nothing recorded the reference or the ledger position | CQ04, CQ28 |
| `TOUCHES` Change → Service, plus `Service.path_prefixes` | nothing connected a file path to a service, so "before I edit this file" and "change failure rate per service" could not start | CQ14, CQ21 |
| `REVERTS` Change → Change | reverts are declared in PR titles and are the clearest signal that a fix failed | CQ23, CQ26 |
| `DECIDED_BY` also from Constraint | "who relaxed this constraint?" | CQ30 |
| embeddings on `Request` and `Change` | "has this been asked or tried before?" is a similarity search | CQ03, CQ26 |

## What the questions say about the rest of Engram

1. **Only 22 of 30 questions are graph walks.** The rest need other kinds of query:

   | Kind | Count | Example |
   |---|---|---|
   | walk the graph | 22 | why does this file exist |
   | time window or history | 7 | decisions reversed last quarter |
   | "has no link" (set difference) | 4 | requirements with no test |
   | filter on a field | 3 | changes touching `refund/retry.py` |
   | counts and durations | 3 | lead time; change failure rate |
   | as-of snapshot | 2 | what the spec cited when approved |
   | similarity | 3 | similar past requests |

   Engram's retrieval today is one shape: start from events, walk out, rank. The PDLC needs the other six as named queries in the pack (the plugins in ADR-0018). This is the biggest build implication found so far, and it belongs in step 5.

2. **History comes from the ledger, not from the node.** Lead time and "reversed last quarter" need every status change with its time. The node only holds the current status; the events behind it (`DERIVED_FROM`) hold the history. That works because the ledger is immutable, and it is one more reason not to store history in the graph.

3. **Eight questions depend on links a model guesses.** CQ01, 02, 08, 13, 14, 15, 21 and 26 rely on `APPLIES_TO`, `ATTRIBUTED_TO` or inferred `IMPLEMENTS`/`VERIFIES`. Their answers are only as good as link scoring, which is what the R10 brief's experiment measures. The pack already keeps those links as "proposed" with a score rather than dropping them.

4. **Two inputs come from outside the PDLC tools.**
   - Which paths belong to which service: a catalog source (Backstage `catalog-info.yaml`, or `CODEOWNERS`) is needed to fill `Service.path_prefixes`.
   - Where decisions are recorded: ADR files in repositories map cleanly to `pdlc.decision.recorded`; decisions buried in threads need LLM extraction.

5. **Weakest-justified types:** `Team` and `Review` are each needed by one question. Keep them (they are cheap and declared by tools), but they are the first to cut if step 2 finds no data for them.

6. **Most-used types:** Change (15 questions), Decision (10), WorkItem (10), Service (8), Incident (7). If the MVP has to shrink, these five plus Requirement and Deployment are the core.

## Next

Step 2: map one Apache project (Jira tickets, GitHub PRs, design proposals) onto pack v0.3 on a sample, to see which fields actually fill, which types nothing feeds, and which links are declared versus guessed.
