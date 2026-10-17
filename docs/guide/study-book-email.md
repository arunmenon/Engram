# Email: Engram visual study book and pilot results

**Subject:** Engram: a visual study book of how it works, and what the pilot proved

---

Hi team,

I have put together a visual study book for Engram, so that anyone joining the work can understand how it works and what the pilot actually proved, without reading the code or the evidence logs first. This note explains what it is, how to open it, and how to get the most out of it in the time you have.

## In short

- **What:** one self-contained HTML page, `docs/guide/engram-study-book.html`, with 83 short lessons in 7 modules. Every lesson is built around a step-by-step animation.
- **Built from real material:** every example comes from the pilot journeys (Alice, Bob, the audit export, the billing incident), and every technical claim was checked against the code, including several checked by running it.
- **Honest about limits:** each lesson that relies on the pilot has a "Proven in the pilot" box quoting what was observed and what remains unproven.
- **Time needed:** a 20-minute tour gives you the big picture; the full book is about 3 to 4 hours at your own pace.

## How to open it

The book has no external dependencies, so it opens straight from your disk.

```bash
git fetch origin
git checkout feature/engram-memory-episodes
git pull
open docs/guide/engram-study-book.html        # macOS
# xdg-open docs/guide/engram-study-book.html  # Linux
```

GitHub shows HTML files as source code, so open the file locally rather than in the GitHub web view. You can jump to any lesson by adding its number to the address, for example `engram-study-book.html#5.15`.

## How to read a lesson

Each lesson has the same layout:

1. **A hook:** one or two sentences that pose the question the lesson answers.
2. **The animation:** press **Play** to watch all steps, click the numbered step tabs, or use the **left and right arrow keys** (they step through the animation, then move to the previous or next lesson). Each step has a one or two sentence caption.
3. **A short explanation:** usually under 120 words.
4. **Under the hood (collapsed):** file paths, function names, settings and issue numbers for engineers who want to check the code.
5. **Proven in the pilot (where relevant):** the coverage verdict, what was observed, and the limit.
6. **You can now answer:** one line saying what you should be able to explain afterwards.

The sidebar lists every module and lesson. A small pipeline map at the top of each lesson (ingest, ledger, workers, graph, retrieval) shows where in the system you are.

## What is in the book

| Module | Lessons | What you will learn |
|---|---|---|
| 1. The Story Before the System | 7 | Why logs and similarity search cannot answer "what changed and why", and Engram's two jobs: an immutable ledger and a graph built from it |
| 2. Packs, Built From Zero | 8 | How a pack (a YAML file) defines node types, arrows, rules and question types, built up one piece at a time |
| 3. Remembering Alice | 15 | The memory story: timelines, profiles and preferences with quoted receipts, owner isolation, beliefs, goals, episodes and summaries |
| 4. Shipping the Export | 14 | The engineering story: request to spec to design, approvals, decisions, PRs and tickets, reviews, tests, deploys, rollback, incident and lesson |
| 5. Asking Questions | 18 | Both retrieval engines: question types, the three searches and rank fusion, the owner gate, walking by intent, drift guards, admission, completeness |
| 6. Under the Hood | 13 | Startup, ingestion checks, duplicates, 16 shards, the five worker loops, failures and waits, the Spanner layout, fencing, tenants, rebuilds, running on your own Spanner |
| 7. The Pilot: What We Proved | 8 | How the pilot ran, the 12 checkpoints, all 67 coverage rows, retained failures, what is still open, and how to repeat it |

## Suggested paths

Pick the one that fits your role and time.

- **20-minute tour (everyone):** lessons 1.1 to 1.7, then 7.3 (the 67 coverage rows) and 7.6 (what is still open).
- **Product and stakeholders:** Module 1, then Modules 3 and 4 for the two stories, then Module 7.
- **Engineers working on retrieval:** Module 1, lessons 2.1 to 2.4, then all of Module 5. Lesson 5.15 walks through issue #85, which this book found and which is now fixed.
- **Platform, operations and deployment:** Module 1, then Module 6, especially 6.4 (ingestion), 6.8 (failures and waits), 6.10 (fencing) and 6.13 (running on your own Spanner).
- **Anyone repeating the pilot:** Module 7, then the team walkthrough (`docs/pilot/team-walkthrough.md`).

## How to read the pilot evidence

The pilot ran two tenants on real Cloud Spanner, through the real HTTP, worker and read paths, with real model calls. Nothing was inserted into the graph by hand, and failed runs were kept as evidence.

Its coverage map has **67 rows: 25 Tenant A stories, 24 Tenant B stories and 18 shared probes. That is 67 rows, not 67 passes.**

| Verdict | Count | Meaning |
|---|---|---|
| Full | 4 | The probe's contract was met for its frozen scope |
| Partial | 58 | The relevant engine parts passed, but the whole catalog story was not proved together |
| Diagnostic | 3 | The pilot found something the system does not support yet |
| External | 2 | Needs people or a deployment outside the engineering team |

"Partial" is the honest default, not a failure. Before drawing a conclusion from any row, read its boundary: the "Limit" line in each "Proven in the pilot" box.

## What is proven, and what is still open

**Closed with evidence during or after the pilot:** owner leaks through shared entities (#64), strict JSON model proposals (#66), summaries built from ledger content (#68), cooperative worker stop (#79), and the superseded-design trace this book found (#85, verified live: 95 of 95 checks).

**Still open:**

- **#83:** finding an entity from a description rather than its name.
- **#86:** running on a company's own Spanner outside the pilot project. The tooling and operator guide are built and pass 154 local tests, but a live run needs an authorized non-pilot GCP project, Spanner instance and database, and credentials.
- **#48:** vector search speed and load.
- **#49:** hierarchy-aware permissions inside a tenant.
- **An independent team repeat of the pilot,** and a deployment outside the engineering team. This is where you come in, if you are able to help.

## Where to go next

| If you want to | Start with |
|---|---|
| Present the pilot | `docs/guide/pilot-chapter.html` and the demo sequence in `docs/pilot/team-walkthrough.md` |
| Check a specific claim | `docs/pilot/coverage-map.md`, then the milestone in `docs/pilot/completion-verification.md` |
| Repeat the pilot | `docs/pilot/team-walkthrough.md` (prerequisites, commands, what you should see) |
| Run Engram on your own Spanner | `docs/deployment/customer-spanner.md` |
| Add a new domain | `docs/runbooks/pack-authoring.md` (worked example in `tests/fixtures/packs/crm/`) |
| See the #85 verification | `docs/pilot/issue85-verification.md` |

## Feedback

If anything in the book disagrees with the code, the code wins. Please tell me which lesson, quoting its number (for example 5.11), and what you saw. A GitHub issue or a reply to this email both work. Suggestions for lessons that are hard to follow are just as welcome.

Thanks, and enjoy the read.

Arun
