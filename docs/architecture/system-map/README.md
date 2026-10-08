# Engram System Map

A design overview of Engram at a 30,000-foot level. It covers ingestion, retrieval, multi-tenancy, the Spanner handshake and ontology packs.

- Published artifact (private until shared): https://claude.ai/artifact/9r5JZ8TY7Lf1nBPiyntpoA
- Page source: `engram-system-map.html`. It opens directly in a browser.
- Diagram generator: `figs.py`. It draws the six SVG figures and checks that every label fits its box.

## Updating the diagrams

1. Edit the figure in `figs.py`.
2. Run `python figs.py` and confirm it reports no fit problems.
3. Replace the six `<svg viewBox=...>...</svg>` blocks in the HTML, in this order: overview, ingest, retrieve, tenancy, handshake, packs. Each block is the matching figure's `svg()` output.
4. Republish the HTML to the artifact link above so the shared page stays current.
