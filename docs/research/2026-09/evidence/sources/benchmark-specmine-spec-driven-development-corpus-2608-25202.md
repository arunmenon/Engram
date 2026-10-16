---
schema_version: 1
artifact_id: N-SURVEY-20260928-13
artifact_type: note
producer: triage
run_id: survey-20260928T070101Z-8451
created_at: 2026-09-28T07:26:00Z
idempotency_key: note:survey:arxiv:2608.25202
input_refs: []
pillar_primary: R10
pillar_secondary: [R6]
memory_stage: linking
priority: 3
beliefs_affected:
  supports: []
  contradicts: []
evidence:
  directness: 4
  control: 2
  independence: 5
  reproducibility: 5
  applicability: 5
  scale: "1 (weak) to 5 (strong)"
source_url: https://arxiv.org/abs/2608.25202
found_via: survey
claim_cluster: specmine-spec-to-pr-corpus
---

# SpecMine: A Large-Scale Corpus of Spec-Driven Development Artifacts

- **URL:** https://arxiv.org/abs/2608.25202 (HTML v3 read). Data: Zenodo DOI 10.5281/zenodo.22102779, Hugging Face Parquet mirrors, GitHub.
- **Type:** paper (dataset)
- **Author / org:** not stated in the extracted text
- **Date:** 2026-08 (v3)
- **Retrieved:** 2026-09-28
- **Cited by evidence:** survey run, R10 question 5 (data to seed the PDLC memory benchmark) and question 1 (trace links)
- **Relevance to a memory stack:** high. The first public corpus found that holds requirement -> design -> task -> PR -> code chains from real repositories, with typed references, commit history and licence. It is the missing data for H7 and for our PDLC memory benchmark.

## TL;DR
- Broad census: 470,795 spec files across 73,030 repositories, attributed to 17 named tools (OpenSpec 274,955 files in 8,926 repos; Spec Kit 54,640 in 10,619; caffeine.ai 14,262 in 13,749).
- Kiro census: 98,574 files across 12,910 repositories in Kiro's requirements / design / tasks layout, which maps directly onto our Requirement, DesignElement and Ticket node types.
- PR layer: 5,992 spec-touching PRs across 581 repositories (repos with >= 10 stars, 11 tools), with changesets. 81.2% of spec-touching PRs also change code.
- 2,421,323 typed references mined from spec text, commit messages, task lists and trees: 1,278,828 to code files, 863,445 to sibling documents, 151,563 to PRs, plus refs, branches and 22k issues.
- CC BY 4.0 compilation licence, 14.7 GB; each spec carries full commit history, so requirement changes over time are observable.

## What it claims / describes
Two censuses of spec-driven development artifacts on public GitHub, each spec enriched with repository metadata, complete commit history and parsed document structure (including counts of "shall" statements, Gherkin blocks and an EARS-template flag). A sweep of every PR that touches a spec in qualifying repositories. A census-wide index of typed references gives a second, independent link from spec to code.

## Numbers
| metric | value | caveat |
|---|---|---|
| Spec files / repos (broad) | 470,795 / 73,030 | GitHub code search caps at 1,000 results per query; reachable set may be a strict subset |
| Kiro files / repos | 98,574 / 12,910 | |
| Spec-touching PRs / repos | 5,992 / 581 (of 949 repos meeting the star threshold) | a subsample, not a census |
| PRs changing spec and code together | 81.2% | co-change is a heuristic: "a PR may touch a spec for unrelated reasons" |
| Typed references | 2,421,323 (code 1,278,828; documents 863,445; PRs 151,563; issues about 22k) | extraction noise not quantified in the extracted text |
| Repos with >= 100 stars | 923 of 73,030 | maturity bias |
| Repos with a recognised SPDX licence | 28,698 | individual repos keep their own licences |
| Size | 14.7 GB uncompressed | |

EARS prevalence statistics: not stated in summary sections.

## Mechanism details you could implement
- Seed a PDLC graph from Kiro repositories: `requirements.md` -> `:Requirement`, `design.md` sections -> `:DesignElement` with REFINES, `tasks.md` items -> `:Ticket`, and spec-touching PRs -> `:PullRequest` with candidate IMPLEMENTS edges from co-change plus typed references.
- Commit history of each spec gives natural "changed requirement" events with timestamps: ground truth for "notice a changed requirement" and supersession questions.
- Two independent link sources (co-change and textual references) allow agreement-based silver labels, with human adjudication on a sample.

## Limitations, caveats, counter-evidence
- Links are heuristic, not ground truth; the authors say so. See N-SURVEY-20260928-14 for evidence that even explicit PR-issue links are misaligned 13.6% of the time.
- Many specs are AI-drafted; agent-written artifacts may be easier than human ones (inference).
- Low-star repos dominate; the PR layer is limited to >= 10 stars.

## Takeaways for tuning a memory stack
- Use SpecMine's Kiro subset as the source for H7's "~300 typed records from a real project history" instead of hand-seeding; pick 5 to 10 repos with long spec histories and many spec-touching PRs.
- It is also the best found seed for the PDLC memory benchmark questions: recall the design behind a requirement, notice a changed requirement, link a PR to what it implements.
- Licence permits research use of the compilation; check each repo's own licence before redistributing content.

## Open questions
- What fraction of spec-touching PRs actually implement the touched requirement? (Needs a labelled sample.)
- How many Kiro repos have enough history (spec revisions after first PR) for staleness questions?
