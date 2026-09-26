# Research queue — the handshake between intelligence (T0) and experiments (T5)

Directory contract; see [`../2026-09/t0-intelligence-handbook.md`](../2026-09/t0-intelligence-handbook.md) §3–5 for formats and rules.

```
queue/
  cards/        PC-YYYYMMDD-NN.md   proposal cards (T0 writes; T5 moves status)
  watch/        WR-YYYYMMDD-NN.md   watch requests (anyone writes; T0 answers)
  verdicts/     <H-or-E-id>.md      experiment verdicts (T5 writes)
  delta/        YYYY-WW.md          weekly intelligence delta (T0 writes, Mondays)
  triage-log/   YYYY-MM-DD.md       per-run triage counts and one-line entries (T0)
  index.jsonl                       one line per card, regenerated after every change
```

States: `proposed → accepted | merged | rejected → carded`; `withdrawn` at any time; nothing is deleted. Only T5 moves a card past `proposed`; only T0 creates cards and notes; every change records who, when, why.
