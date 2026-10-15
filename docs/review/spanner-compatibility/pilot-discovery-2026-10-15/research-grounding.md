# External research grounding for pilot journey discovery

15 October 2026. Planning references only; no benchmark execution, dataset download, implementation or pilot run. These sources suggest coverage dimensions. Engram support must be established independently from its contracts and evidence.

## Conversational and personal memory

[LongMemEval — authors' repository](https://github.com/xiaowu0162/LongMemEval) and [ICLR 2025 paper](https://proceedings.iclr.cc/paper_files/paper/2025/file/d813d324dbf0598bbdc9c8e79740ed01-Paper-Conference.pdf) distinguish information extraction, multi-session reasoning, temporal reasoning, knowledge updates and abstention. Adapt these into separate Engram retrieval probes: single-source recall; enough evidence from several sessions; time-scoped context; current versus superseded state; and absence of supporting evidence for an unsupported premise. An exact identifier lookup cannot substitute for natural-language evidence discovery. Retrieval correctness and downstream answer reasoning are separate verdicts.

[LoCoMo — ACL 2024 paper](https://aclanthology.org/2024.acl-long.747/) evaluates long conversations using persona and temporal event context, question answering and event summarization. This motivates varied personal/work situations and checking what summaries preserve or omit, instead of repeating the same preference story. Multimodal tasks from that research do not imply Engram supports images or uploaded-document parsing.

These are adapted discovery dimensions, not an assertion of benchmark compliance or comparable scores. We are not importing all benchmark cases or committing to their history sizes. Engram returns graph/context responses; an application-level generated answer must be evaluated separately if included in the pilot.

## Development lifecycle

[GitHub pull-request review semantics](https://docs.github.com/en/pull-requests/reference/pull-request-reviews) separates comment, approval and requested changes. This motivates review reversal and revision-specific evidence cases; Engram's exact supported review/approval declarations govern what can be required.

[GitHub deployment history](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/view-deployment-history) exposes environment-specific deployment history, commit and workflow relationships. This motivates asking which exact build reached which environment and distinguishing attempts/outcomes, rather than treating a release as proof of production success. Native GitHub webhook ingress is currently unavailable in Engram's public tenant service; source-normalized API ingestion is a separate supported path.

[DORA deployment automation](https://dora.dev/capabilities/deployment-automation/) emphasizes deployable packages, environment-specific configuration, deployment tests and repeatability. [DORA test automation](https://dora.dev/capabilities/test-automation/) emphasizes feedback through the delivery lifecycle. Adapt these into Engram evidence stories for test failures, reruns, staged deployment, failed rollout and recovery. This is a knowledge/retrieval pilot, not a project to implement deployment automation, measure DORA performance or add historical database migration.

## Discovery rules

- Vary the business story, input shape, temporal history, artifact relationships and question type; do not inflate journey counts by renaming Alice or changing a PR number.
- Count a product journey separately from its assertions and shared failure probes.
- State exact inputs, expected useful output/evidence, forbidden effects, worker applicability, supported read surface, prerequisites and priority for each candidate.
- Label verified representative behavior, supported contract requiring fresh pilot proof, exploratory/model-quality behavior, and gap/product decision separately.
- Core remains mandatory. Memory Belief/Goal actions are explicit producer assertions. User prose extraction needs actual-provider evidence. Episode snapshots are scheduled and time-grouped; no automatic domain-to-memory semantic join is implied.
- Preserve original natural-language questions beside exact-ID controls. Freeze gold source IDs and expected/forbidden artifacts before execution; a missing useful answer must remain visible.
- Keep finer hierarchy authorization, migrations, ANN/load stress, hot pack switching and unsupported tenant maintenance/import/cursors/webhooks outside this discovery's execution authority.
