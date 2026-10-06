# Engram walkthrough: ontology packs and the Spanner backend

Shareable page for engineers: https://claude.ai/artifact/2xnRzwTAnwV1D21hyBLW7g

It covers, in plain language:

- The big picture: what changed in each layer, before and after.
- The common ontology layer (core, memory, user) and how domain packs build on it.
- What a pack declares, and how a pack change is applied safely (replay, blue/green rebuild, evaluation gate).
- The PDLC ontology: node and edge types, intents, rules, a worked example and evaluation results.
- The ingestion flow: ways in, checks, the EventLog and Subscription ports, and two-step projection.
- The retrieval flow: what the refactor changed in the agent-memory engine, and the new artifact retriever.
- How Engram talks to Spanner: the five storage ports and how each maps onto Spanner.
- Spanner insights and open risks.

The page source is [walkthrough.html](walkthrough.html). Edit the published page by republishing that file to the same URL.
