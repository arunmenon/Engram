# E-20260928-18-r2 (first cut, LoCoMo only): should Jev decide which memories link to each other?

We took the 920 memories our extractor already wrote for two LoCoMo conversations and linked them three ways. With simple rules: same session in order, same named thing. With those rules plus the links Jev confirms: for each new memory Jev judged up to 10 earlier candidates as same topic, cause and effect, or same event, at the paper's 0.60 cut. And with no links at all. Then Claude answered 292 benchmark questions from a fixed 4,000-token slice of memory in each case, and Codex graded the answers. Links help: rule-based links raised accuracy from 55.0% to 58.7%, and the gain is real (interval above zero). Jev's links added nothing on top of the rules (58.4% against 58.7%). They also made the answerer worse at refusing trick questions whose premise is false (66% against 73% correct refusals), because Jev pulls in more loosely related memories. Jev was cheap and fast: about 9 US cents per 1,000 writes and about 0.4 seconds per write. For Engram this says to build the deterministic links now (they are free and they work) and not to add Jev link decisions on this evidence. Recommended next step: keep Jev linking out of the write path. The two parts of the spec this first cut could not do (labelled link pairs to measure link precision directly, and the comparison with our LLM linker) wait on OpenAI credits and a labelling round. Run them only if trace links on the PDLC fixture are still wanted.

## Numbers

Nodes: 920 memory items (conv-47 whole, conv-49 sessions 1 to 13 and 17 only, as extracted), 9,090 frozen candidate pairs (at most 10 per write), 1,251 deterministic edges (built twice, byte-identical). Questions: 292 LoCoMo questions whose evidence sessions were extracted (categories 1 to 5: 31, 56, 18, 123, 64).

Jev link pass (jev-1.13.0): 918 writes scored, 27,270 Nouls, 2.03M input tokens, 0.085 USD (0.093 USD per 1,000 writes), mean 0.39 s per write, 45 s wall clock at 8 in parallel. Links at >= 0.60: 4,284 (semantic 2,591 of 9,090 pairs, caused_by 646, same_episode 1,047). Mean Jev probability 0.35 (semantic), 0.22 (caused_by), 0.23 (same_episode).

Answer accuracy (Claude claude-sonnet-5-5 reader, Codex gpt-6-astra judge, scores 0 / 0.5 / 1; served tokens about 3,980 in every arm):

| Arm | Edges | Accuracy | Categories 1 to 4 | False-premise (category 5) |
|---|---|---|---|---|
| N | none | 0.550 | 0.515 | 0.672 |
| C | deterministic (temporal + same entity) | **0.587** | 0.546 | **0.734** |
| A_paper | C + Jev-confirmed at 0.60 | 0.584 | **0.564** | 0.656 |

Paired differences (question bootstrap, 10,000 resamples):
- A_paper minus C: -0.003, 95% [-0.031, +0.026], 28 discordant questions.
- A_paper minus N: +0.034 [+0.003, +0.067].
- C minus N: +0.038 [+0.002, +0.075].

Rule read-out: not `negative` (the A minus C answer interval includes zero; trace-link precision was not measurable); not `edges_inert` (C and A beat N by more than 1 point); the link-metric rules (non-inferiority to B within 2 points, A over C on macro-F1) cannot be evaluated without labelled pairs and arm B, so the outcome is **inconclusive**, with the answer evidence pointing against adding Jev links.

## Weaker than the spec wanted

- **No arm B.** The production LLM linker would run on gpt-5.6-terra, and the OpenAI key has no credits. Engram also has no standalone LLM linker to call; its linking today is enrichment (embeddings, entity resolution).
- **No link labels, so no link precision or recall.** The frozen LINK-ASF-LOCOMO set has labelled PDLC pairs but no LoCoMo pairs and no arm-proposed pairs. The executor does not label. So only the answer endpoint and build cost are measured here.
- **No refit.** A-refit needs a labelled dev slice; only the paper's fixed 0.60 threshold (A-paper) was run.
- **One Jev pass, not three**, and LoCoMo only (the PDLC trace-link arm is the queue's "then" step).
- **Nodes are the existing terra build**, which failed on conv-49 sessions 14 to 16 and 18 to 25 when OpenAI credits ran out, so conv-49 is partial.
- **Retrieval stand-in.** BM25 seeds (top 5), one-hop expansion along each arm's edges, then further BM25 ranks, up to 4,000 tokens. Engram's hybrid retrieval (RRF over vector, lexical, entity, time) needs the Redis and Neo4j stack and was not used. Candidates use entity and lexical channels only (no vector channel).
- **Judge and reader.** Codex's judge scores were not human-checked (the spec asks for a 20% human subsample). One answering repetition per arm, not three.
- **Rerun.** The first Jev pass read Noul answers from the wrong field and produced 0 links; the parser was fixed and the pass rerun on the same 918 writes.
- **Policy gates** replaced by the CTO's fast-track queue and policy v2.

## Files

`nodes.jsonl`, `candidates.jsonl`, `edges_C.jsonl`, `edges_A_paper.jsonl`, `jev_link_calls.jsonl` (every Jev score per pair and type), `jev_link_summary.json`, `questions.jsonl`, `answers/`, `judged/`, `metrics.csv`, `verdict.json`, `build_manifest.json`, `run_manifest.json`, `receipts.sha256`. Commands: `python -m linkeval.locomo {build,jev,answer,judge,score}` from `harness/`.
