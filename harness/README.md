# T4 experiment harness

Runners, freezers and scorers for the accepted experiment specs on the research
bus. Standard library only, so a pinned commit runs on any host with Python 3.11+.

| Package | Spec | Command shape (from the spec's execution packet) |
|---|---|---|
| `gate_eval` | E-20260928-06-r2 naming audit | `python -m gate_eval.freeze build …`, `python -m gate_eval.naming_audit --manifest … --templates templates/naming_audit/ --models models.lock.json --policy <policy.md> --out runs/E-20260928-06-r2/`, `python -m gate_eval.naming_score --run … --labels …` |
| `linkstale` | E-20260928-07-r2 neighbours as free text vs typed field | `python -m linkstale.run --manifest <run_manifest.json>`, `python -m linkstale.score --run … --dataset …` |
| `memdec` | E-20260928-12 (setup only) | `python -m memdec.export …`, `python -m memdec.targets …` |

Run every command from this directory (`cd harness`). Tests: `python -m pytest -q tests`.

## What every runner enforces before the first call

1. Git working tree clean; the commit hash goes into `run_manifest.json`.
2. `policy.md` (a local copy of the bus file, path passed explicitly) has `status: set`; per-run caps for tokens, USD and wall clock are read from it and checked before every call. The harness has no default caps.
3. The frozen dataset verifies: every per-record sha256 in the manifest matches.
4. `models.lock.json` pins the model version and the template hashes (`models.lock.example.json` shows the shape; the preflight rejects empty pins).
5. `TYPESAFE_API_KEY` is present in the environment, or `--render-only` is passed. Keys are never read from files.
6. The output directory is empty. A rerun needs a new spec revision, per policy.

Labels are read only by the scorers. Runners never open `labels.jsonl`, `gold.jsonl` or the planted answers.

`verdict.json` inside a run directory is the machine output of the spec's predeclared rule. It is not a bus verdict: the verdict role writes `verdicts/`, the executor never does.

## What is deliberately not here

- No fine-tuning code for E-20260928-12: Qwen base downloads and GPU training do not belong on a harness host without model-endpoint egress and a GPU pin. `memdec` covers export, repository-level splits and soft targets only.
- No dataset content. `data/frozen/` is empty until the dataset owners freeze H5-labelled-90, LINK-STALE-200 (including the 400 planted opinions and `opinion_rule.json`) and MEMDEC-OD. The executor does not author labels, probes or rules (policy: executor never modifies datasets or scorer).
- No Laya arm. The licence check the spec requires (frozen model-card sha256) has not been done.

## Open items for the T4 owner before a freeze

- Noul rendering: the TypeSafe Noul primitive has no option names or order, so all cells of `noul_quote_supports_item` render through the Choice primitive with two options. The N-aligned cell is therefore not byte-identical to a native Noul call. Confirm or change before freeze (`templates/naming_audit/noul_quote_supports_item.json`, `render_note`).
- Rubric wording in both templates was drafted from `docs/research/2026-09/jev-typed-decisions.md` A1; it must be confirmed as the current H5 wording. Both files carry `wording_status`.
- Payload delivery check: the spec's relative token check cannot detect rubrics dropped identically in every cell (REV-20260928-24). The runner records that limitation in `run_manifest.json`; an absolute control (echoed payload or nonce canary) needs a spec revision.
- `linkstale.score` falls back to a bytes/4 proxy for the neighbour token count when the dataset does not carry `nbr_tokens` from the pinned tokenizer; freeze `nbr_tokens` with the dataset.
