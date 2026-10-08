"""Generate the six system-map figures as inline SVG, checking label fit."""
from html import escape

HEAD_W = 8.1    # px per char, 14px semibold
TEXT_W = 6.9    # px per char, 13px regular
SMALL_W = 6.5   # px per char, 12.5px
problems = []

class Fig:
    def __init__(self, name, w, h, label):
        self.name, self.w, self.h, self.label = name, w, h, label
        self.parts = []
        p = name
        self.parts.append(
            f'<defs>'
            f'<marker id="{p}-ink" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-ink"/></marker>'
            f'<marker id="{p}-flow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-flow"/></marker>'
            f'<marker id="{p}-fence" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-fence"/></marker>'
            f'<marker id="{p}-muted" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-muted"/></marker>'
            f'<marker id="{p}-warn" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" class="mk-warn"/></marker>'
            f'</defs>')

    def _fit(self, text, width, per, where):
        if len(text) * per > width:
            problems.append(f"{self.name}: '{text}' ({len(text)*per:.0f}px) > {width}px in {where}")

    def box(self, x, y, w, h, cls, head=None, lines=(), align="middle", pad=12):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" class="{cls}"/>')
        avail = w - 2 * pad
        tx = x + w / 2 if align == "middle" else x + pad
        n = (1 if head else 0) + len(lines)
        block = (18 if head else 0) + 17 * len(lines)
        ty = y + (h - block) / 2 + 13
        if head:
            self._fit(head, avail, HEAD_W, head)
            hcls = "t-head t-inv" if "fill" in cls else "t-head"
            self.parts.append(f'<text x="{tx}" y="{ty:.1f}" text-anchor="{align if align=="middle" else "start"}" class="{hcls}">{escape(head)}</text>')
            ty += 20
        for line in lines:
            self._fit(line, avail, TEXT_W, head or line)
            lcls = "t-sub t-inv2" if "fill" in cls else "t-sub"
            self.parts.append(f'<text x="{tx}" y="{ty:.1f}" text-anchor="{align if align=="middle" else "start"}" class="{lcls}">{escape(line)}</text>')
            ty += 17
        if (ty - 17 - y) > h - 4:
            problems.append(f"{self.name}: box '{head}' too short")

    def line(self, pts, cls="ln-flow", marker="flow", start=False):
        d = "M" + " L".join(f"{a},{b}" for a, b in pts)
        m = f' marker-end="url(#{self.name}-{marker})"' if marker else ""
        s = f' marker-start="url(#{self.name}-{marker})"' if start else ""
        self.parts.append(f'<path d="{d}" class="{cls}"{m}{s}/>')

    def text(self, x, y, s, cls="t-small", anchor="middle", maxw=None):
        if maxw:
            self._fit(s, maxw, SMALL_W, s)
        self.parts.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{escape(s)}</text>')

    def frame(self, x, y, w, h, label=None):
        self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" class="bx-dash"/>')
        if label:
            self.parts.append(f'<text x="{x+14}" y="{y+22}" class="t-frame">{escape(label)}</text>')

    def svg(self):
        return (f'<svg viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.label)}">'
                + "".join(self.parts) + "</svg>")


figs = {}

# ---------------------------------------------------------------- 1 overview
f = Fig("ov", 1110, 500, "Sources enter the ingress API and are appended to the tenant's Spanner ledger; workers project them into the graph in the same database; the retrieval API answers the agent from the graph. The pack bundle configures ingress, workers and retrieval. The tenant binding authenticates writers and must match the owner row that every transaction checks.")
f.box(210, 24, 880, 62, "bx-flow", "Active pack bundle", ["core + pdlc (+ memory, user), composed into one bundle with one digest"])
f.frame(420, 150, 490, 335, "one Spanner database per tenant")
f.box(20, 222, 140, 96, "bx-soft", "Sources", ["webhooks", "agents", "importers"])
f.box(210, 222, 160, 96, "bx", "Ingress API", ["authenticate", "admit vs. bundle", "check payload"])
f.box(440, 222, 130, 96, "bx", "Ledger", ["append-only", "with acceptance", "source of truth"])
f.box(606, 222, 130, 96, "bx-flow", "5 workers", ["read in order", "project", "enrich, extract"])
f.box(772, 222, 118, 96, "bx", "Graph", ["nodes, edges", "provenance", "rebuildable"])
f.box(950, 222, 140, 96, "bx", "Retrieval API", ["pack intents", "weighted walk", "answer, evidence"])
f.box(950, 400, 140, 56, "bx-soft", "Agent")
f.box(440, 392, 430, 70, "bx-fence", "Owner row (TenantControl)", ["tenant · binding · epoch · digest · state"])
f.box(20, 392, 330, 70, "bx-fence", "Tenant binding", ["which database, epoch and bundle digest"])
# data path
f.line([(160, 270), (210, 270)]); f.text(185, 262, "event")
f.line([(370, 270), (440, 270)]); f.text(395, 262, "append")
f.line([(570, 270), (606, 270)])
f.line([(736, 270), (772, 270)])
f.line([(890, 270), (950, 270)]); f.text(930, 262, "read")
f.line([(1040, 318), (1040, 400)]); f.text(1048, 364, "answer", anchor="start")
f.line([(1000, 400), (1000, 318)], cls="ln-dash", marker="muted"); f.text(992, 364, "question", anchor="end")
# bundle configures
for x in (290, 671, 1020):
    f.line([(x, 86), (x, 222)], cls="ln-dash", marker="muted")
f.text(282, 160, "which events", anchor="end")
f.text(679, 132, "which rules", anchor="start")
f.text(1028, 160, "which intents", anchor="start")
# tenancy
f.line([(290, 392), (290, 318)], cls="ln-fence", marker="fence"); f.text(282, 362, "who may write", anchor="end")
f.line([(350, 427), (440, 427)], cls="ln-fence", marker="fence"); f.text(395, 419, "match")
for x in (505, 671, 831):
    f.line([(x, 392), (x, 318)], cls="ln-fence", marker="fence")
f.text(588, 360, "checked in")
f.text(588, 376, "every transaction")
figs["overview"] = f

# ---------------------------------------------------------------- 2 ingestion
f = Fig("in", 1110, 720, "An event passes four checks before it is stored: authenticate, admission context, pack contract and a fenced append. Each refusal stores nothing. The ledger then feeds five workers, of which projection builds the graph.")
steps = [
    (16, "bx-soft", "Source event", ["signed webhook, or POST /v1/events (single, batch, import)"]),
    (96, "bx", "1  Who sent it", ["webhook signature or bearer token; the server sets the source id"]),
    (176, "bx-fence", "2  Which tenant and bundle", ["tenant, database, binding, epoch, bundle digest"]),
    (256, "bx-flow", "3  Valid for these packs?", ["type owned by an active pack; payload fields and types; timezone"]),
    (336, "bx-fence", "4  Commit, if we still own the database", ["owner row matches; same id seen before?; stamp acceptance"]),
    (436, "bx", "Events ledger", ["201 created, with position and acceptance record"]),
]
for y, cls, head, lines in steps:
    f.box(40, y, 480, 60, cls, head, lines, align="start", pad=16)
for (y1, *_), (y2, *_) in zip(steps, steps[1:]):
    f.line([(280, y1 + 60), (280, y2)])
f.box(600, 106, 300, 40, "bx-warn", None, ["401 · nothing stored"])
f.box(600, 186, 300, 40, "bx-warn", None, ["refused · no tenant for this credential"])
f.box(600, 266, 300, 40, "bx-warn", None, ["422 · nothing stored"])
f.box(600, 326, 300, 36, "bx-warn", None, ["409 · same id, different content"])
f.box(600, 370, 300, 36, "bx-soft", None, ["201 · exact duplicate, same answer"])
for y in (126, 206, 286):
    f.line([(520, y), (600, y)], cls="ln-warn", marker="warn")
f.line([(520, 360), (560, 360), (560, 344), (600, 344)], cls="ln-warn", marker="warn")
f.line([(560, 360), (560, 388), (600, 388)], cls="ln-dash", marker="muted")
f.frame(20, 530, 1070, 176, "workers: each is a consumer group on the ledger; it acknowledges only after its writes succeed")
f.line([(280, 496), (280, 530)]); f.text(290, 518, "read in position order", anchor="start")
wk = [
    ("bx-flow", "Projection", ["builds the graph", "Event node, FOLLOWS", "pack rules: nodes, edges", "DERIVED_FROM to event"]),
    ("bx", "Pack extraction", ["LLM on prose events", "only declared types", "links start proposed"]),
    ("bx", "Enrichment", ["keywords, importance", "embeddings", "SIMILAR_TO, REFERENCES"]),
    ("bx-soft", "Extraction", ["session memory, user", "profile, preferences", "only with memory, user"]),
    ("bx-soft", "Consolidation", ["summaries, patterns", "retention", "scheduled"]),
]
for i, (cls, head, lines) in enumerate(wk):
    f.box(40 + i * 208, 566, 196, 120, cls, head, lines)
figs["ingest"] = f

# ---------------------------------------------------------------- 3 retrieval
f = Fig("rt", 1110, 346, "A question passes the tenant guard, is classified against pack intents, checked against the evaluation gate and seeded; the walk follows intent weights over the active packs only; admission rules filter what may be returned; the Atlas response carries provenance and is released after a fresh tenant check.")
top = [("bx-soft", "Question", ["text, optional seeds"]),
       ("bx-fence", "Tenant guard", ["token → tenant", "owner row active?"]),
       ("bx-flow", "Classify", ["intent from pack", "keywords"]),
       ("bx", "Eval gate", ["pack's eval set", "recorded passing?"]),
       ("bx", "Seed", ["exact ids first,", "then weighted words"])]
for i, (cls, head, lines) in enumerate(top):
    f.box(20 + i * 218, 24, 180, 92, cls, head, lines)
for i in range(4):
    f.line([(200 + i * 218, 70), (238 + i * 218, 70)])
f.box(238, 144, 180, 34, "bx-warn", None, ["401 / 403"])
f.box(674, 144, 180, 34, "bx-warn", None, ["409 · intent pending"])
f.line([(328, 116), (328, 144)], cls="ln-warn", marker="warn")
f.line([(764, 116), (764, 144)], cls="ln-warn", marker="warn")
bottom = [("bx-flow", "Walk", ["intent edge weights", "bounded depth, calls", "active packs only"]),
          ("bx", "Admit", ["drop superseded,", "untrusted, rejected;", "proposed: flagged"]),
          ("bx", "Atlas response", ["nodes, edges, scores", "reason per node", "provenance per node"]),
          ("bx-fence", "Response guard", ["fresh owner check", "before release"]),
          ("bx-soft", "Agent", [])]
for i, (cls, head, lines) in enumerate(bottom):
    x = 892 - i * 218
    f.box(x, 220, 180, 110, cls, head, lines)
for i in range(4):
    x = 892 - i * 218
    f.line([(x, 275), (x - 38, 275)])
f.line([(982, 116), (982, 220)])
figs["retrieve"] = f

# ---------------------------------------------------------------- 4 tenancy
f = Fig("tn", 1110, 460, "Two tenants authenticate through the catalog and are bound to separate Spanner databases. Each database holds an owner row naming its tenant, binding, epoch and bundle digest; every transaction checks it. A dispatcher routes each request to its tenant's binding.")
f.box(20, 150, 220, 110, "bx-fence", "Tenant catalog", ["token → principal", "principal → one binding", "no default tenant"])
f.box(20, 300, 220, 80, "bx-fence", "Dispatcher", ["many tenants per process", "request → its binding"])
f.box(310, 40, 240, 116, "bx-fence", "Binding: tenant A", ["database tenant-a", "epoch 18", "bundle digest f57f…"])
f.box(310, 290, 240, 116, "bx-fence", "Binding: tenant B", ["database tenant-b", "epoch 3", "bundle digest 91c0…"])
f.line([(240, 186), (275, 186), (275, 98), (310, 98)], cls="ln-fence", marker="fence")
f.line([(240, 224), (275, 224), (275, 348), (310, 348)], cls="ln-fence", marker="fence")
f.text(430, 210, "Every transaction re-reads", cls="t-sub")
f.text(430, 228, "its owner row and refuses", cls="t-sub")
f.text(430, 246, "on any mismatch", cls="t-sub")
for y0, name, epoch, dig in ((20, "tenant-a", "18", "f57f…"), (270, "tenant-b", "3", "91c0…")):
    f.frame(620, y0, 470, 170, f"Spanner database {name}")
    f.box(640, y0 + 36, 130, 56, "bx", "Events", ["PR #7, payments"])
    f.box(790, y0 + 36, 130, 56, "bx", "Graph", ["Change #7"])
    f.box(940, y0 + 36, 130, 56, "bx", "Cursors", ["per group"])
    f.box(640, y0 + 104, 430, 52, "bx-fence", "Owner row", [f"tenant {name[-1].upper()} · {name} · epoch {epoch} · {dig} · active"])
f.line([(550, 98), (620, 98)]); f.text(585, 90, "opens")
f.line([(550, 348), (620, 348)]); f.text(585, 340, "opens")
f.text(855, 230, "same ids in both databases, never joined", cls="t-warn")
figs["tenancy"] = f

# ---------------------------------------------------------------- 5 handshake
f = Fig("hs", 1110, 470, "Startup ladder: open with the binding's settings, verify the physical schema, the entity vector index, the acceptance column and control table, and the owner row; then serve. Each step refuses on mismatch; none applies DDL or creates ownership.")
ladder = [
    ("bx-fence", "1  Open with the binding's settings", "all ports on Spanner; no emulator; create flags off"),
    ("bx", "2  Schema matches the code", "tables, columns, indexes, property graph"),
    ("bx", "3  Entity vector index", "same dimensions, and ready"),
    ("bx", "4  Acceptance column and control table", "present, with the expected shape"),
    ("bx-fence", "5  Owner row matches the binding", "tenant, database, binding, epoch, digest; state allows it"),
]
for i, (cls, head, sub) in enumerate(ladder):
    f.box(40, 20 + i * 76, 520, 58, cls, head, [sub], align="start", pad=16)
    if i:
        f.line([(300, 20 + i * 76 - 18), (300, 20 + i * 76)], cls="ln", marker="ink")
f.line([(300, 20 + 4 * 76 + 58), (300, 400)], cls="ln", marker="ink")
f.box(40, 400, 520, 50, "bx-good", "Serve; the same check runs in every transaction")
labels = ["differs", "differs", "missing", "mismatch"]
for i, lab in enumerate(labels, start=1):
    y = 20 + i * 76 + 29
    f.line([(560, y), (640, y)], cls="ln-warn", marker="warn")
    f.text(600, y - 7, lab)
f.box(640, 20, 450, 380, "bx-warn", None, [])
refuse = [("h", "Refuse, and say why. Never:"),
          ("b", "apply DDL at startup; schema changes are"),
          ("c", "a recorded operator step"),
          ("b", "create a database on a real instance"),
          ("c", "without an explicit flag"),
          ("b", "create, repair or adopt an owner row"),
          ("b", "reactivate a frozen owner"),
          ("b", "fall back to a default tenant, the emulator"),
          ("c", "or other credentials"),
          ("b", "serve a bundle the owner row does not name"),
          ("g", ""),
          ("h", "At shutdown"),
          ("b", "close the SDK session pool Engram opened")]
y = 50
for kind, line in refuse:
    if kind == "g":
        y += 10
        continue
    if kind == "h":
        f.parts.append(f'<text x="660" y="{y}" class="t-head">{escape(line)}</text>')
        y += 28
        continue
    x = 680 if kind == "b" else 680
    if kind == "b":
        f.parts.append(f'<circle cx="666" cy="{y - 4}" r="2.5" class="mk-warn"/>')
    f._fit(line, 400, TEXT_W, "refuse")
    f.parts.append(f'<text x="{x}" y="{y}" class="t-sub">{escape(line)}</text>')
    y += 23 if kind == "b" else 27
    i = refuse.index((kind, line))
    if kind == "b" and i + 1 < len(refuse) and refuse[i + 1][0] != "c":
        y += 4
figs["handshake"] = f

# ---------------------------------------------------------------- 6 packs
f = Fig("pk", 1110, 470, "Core is mandatory; memory and user are optional; PDLC and the CRM example are domain packs. The loader composes the selected packs into one bundle with a digest, which is read at admission, projection, extraction and retrieval.")
f.box(20, 24, 380, 56, "bx-dash", "crm (example)", ["Account, Contact, Deal: new domain, no code"], align="start", pad=16)
f.box(20, 90, 380, 56, "bx-flow", "pdlc 2.1", ["17 types · 25 edges · 25 events · 5 intents"], align="start", pad=16)
f.box(20, 156, 185, 56, "bx-soft", "memory", ["optional"], align="start", pad=16)
f.box(215, 156, 185, 56, "bx-soft", "user", ["optional"], align="start", pad=16)
f.box(20, 222, 380, 56, "bx", "core 1.1 (mandatory)", ["Event, Entity, DERIVED_FROM, shared interfaces"], align="start", pad=16)
f.text(210, 300, "each tenant selects its packs", cls="t-small")
f.box(20, 330, 380, 120, "bx-soft", "Changing a pack", ["additive → applies live", "mapping → replay affected events", "breaking → rebuild from ledger, eval-gated"], align="start", pad=16)
f.box(460, 96, 200, 110, "bx-flow", "Compose, check", ["fixed order", "one owner per namespace", "edges, weights merged"])
f.box(720, 96, 200, 110, "bx-fill", "Active bundle", ["one digest", "in the binding and", "on every event"])
f.line([(400, 151), (460, 151)])
f.line([(660, 151), (720, 151)])
uses = [("Admission", ["event types", "payload contracts", "trusted sources"]),
        ("Projection", ["upserts, edges", "transitions", "keys, lifecycles"]),
        ("Extraction", ["what an LLM may", "propose, with caps"]),
        ("Retrieval", ["intents, weights", "seeds, admission", "read scope"])]
xs = [460, 620, 780, 940]
for x, (head, lines) in zip(xs, uses):
    f.box(x, 300, 150, 110, "bx", head, lines)
f.line([(820, 206), (820, 260)], cls="ln-dash", marker=None)
f.line([(535, 260), (1015, 260)], cls="ln-dash", marker=None)
for x in xs:
    f.line([(x + 75, 260), (x + 75, 300)], cls="ln-dash", marker="muted")
f.text(828, 240, "read at four points", anchor="start")
figs["packs"] = f

if __name__ == "__main__":
    for p in problems:
        print("FIT:", p)
    print("figures:", list(figs), "problems:", len(problems))
