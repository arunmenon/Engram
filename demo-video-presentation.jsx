import { useState, useEffect, useRef, useCallback } from "react";
import { LineChart, Line, XAxis, YAxis, ResponsiveContainer, RadarChart, Radar, PolarGrid, PolarAngleAxis, BarChart, Bar, Cell } from "recharts";

// ─── Color Palette ───
const C = {
  bg: "#0f1117", surface: "#1a1d27", surfaceHover: "#22263a",
  accent: "#3b82f6", accentGlow: "rgba(59,130,246,0.25)",
  green: "#22c55e", amber: "#f59e0b", red: "#ef4444", purple: "#a855f7", cyan: "#06b6d4", pink: "#ec4899",
  teal: "#14b8a6", indigo: "#6366f1", orange: "#f97316",
  text: "#e2e8f0", muted: "#64748b", mutedLight: "#94a3b8",
  border: "rgba(100,116,139,0.25)",
};

// ─── Helpers ───
function Counter({ end, duration = 2000, prefix = "", suffix = "" }) {
  const [val, setVal] = useState(0);
  const ref = useRef(null);
  useEffect(() => {
    let start = 0;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setVal(Math.floor(p * end));
      if (p < 1) ref.current = requestAnimationFrame(step);
    };
    ref.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(ref.current);
  }, [end, duration]);
  return <span>{prefix}{val.toLocaleString()}{suffix}</span>;
}

const Pill = ({ color, children }) => (
  <span style={{ padding: "3px 10px", borderRadius: 20, background: `${color}18`, color, fontSize: 10, fontWeight: 600, border: `1px solid ${color}30` }}>{children}</span>
);

const SectionTag = ({ children }) => (
  <div style={{ fontSize: 10, color: C.muted, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.2, marginBottom: 4 }}>{children}</div>
);

const Card = ({ children, style, delay = 0, anim = "slideUp" }) => (
  <div style={{ padding: 16, borderRadius: 12, background: C.surface, border: `1px solid ${C.border}`, animation: `${anim} 0.5s ease-out ${delay}s both`, ...style }}>
    {children}
  </div>
);

// ─── Animated Graph (SVG) ───
function AnimatedGraph({ phase = 0, style, compact = false }) {
  const sc = compact ? 0.65 : 1;
  const nodes = [
    { id: "e1", x: 200 * sc, y: 100 * sc, type: "Event", label: "user.message", color: C.accent },
    { id: "e2", x: 360 * sc, y: 80 * sc, type: "Event", label: "tool.execute", color: C.accent },
    { id: "e3", x: 500 * sc, y: 140 * sc, type: "Event", label: "agent.respond", color: C.accent },
    { id: "en1", x: 130 * sc, y: 220 * sc, type: "Entity", label: "Sarah Chen", color: C.green },
    { id: "en2", x: 320 * sc, y: 250 * sc, type: "Entity", label: "Billing", color: C.green },
    { id: "en3", x: 480 * sc, y: 230 * sc, type: "Entity", label: "Refund", color: C.amber },
    { id: "s1", x: 260 * sc, y: 340 * sc, type: "Summary", label: "Session Summary", color: C.purple },
    { id: "up", x: 80 * sc, y: 340 * sc, type: "UserProfile", label: "Sarah's Profile", color: C.pink },
    { id: "pf", x: 80 * sc, y: 140 * sc, type: "Preference", label: "Email only", color: C.cyan },
    { id: "sk", x: 530 * sc, y: 330 * sc, type: "Skill", label: "Tech Lead", color: C.cyan },
  ];
  const edges = [
    { from: "e1", to: "e2", type: "FOLLOWS" }, { from: "e2", to: "e3", type: "FOLLOWS" },
    { from: "e1", to: "en1", type: "REFERENCES" }, { from: "e2", to: "en2", type: "REFERENCES" },
    { from: "e3", to: "en3", type: "REFERENCES" }, { from: "s1", to: "e1", type: "SUMMARIZES" },
    { from: "s1", to: "e3", type: "SUMMARIZES" }, { from: "en1", to: "up", type: "HAS_PROFILE" },
    { from: "en1", to: "pf", type: "HAS_PREFERENCE" }, { from: "en1", to: "sk", type: "HAS_SKILL" },
    { from: "en2", to: "en3", type: "RELATED_TO" },
  ];
  const nodeMap = Object.fromEntries(nodes.map(n => [n.id, n]));
  const visN = Math.min(nodes.length, Math.floor(phase * nodes.length) + 1);
  const visE = Math.min(edges.length, Math.floor(phase * edges.length));
  const visIds = new Set(nodes.slice(0, visN).map(n => n.id));
  const shapeFor = (type) => {
    if (type === "Entity" || type === "Workflow") return "triangle";
    if (type === "Preference" || type === "Skill") return "diamond";
    if (type === "Summary" || type === "BehavioralPattern") return "square";
    return "circle";
  };
  const vw = compact ? 400 : 620;
  const vh = compact ? 260 : 400;
  return (
    <svg viewBox={`0 0 ${vw} ${vh}`} style={{ width: "100%", height: "100%", ...style }}>
      <defs>
        <filter id="glow2"><feGaussianBlur stdDeviation="3" result="g" /><feMerge><feMergeNode in="g" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
      </defs>
      {edges.slice(0, visE).map((e, i) => {
        const a = nodeMap[e.from], b = nodeMap[e.to];
        if (!visIds.has(e.from) || !visIds.has(e.to)) return null;
        return (<g key={i} style={{ animation: "fadeIn 0.6s ease-out" }}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={C.border} strokeWidth={1.2} /><text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 5} fill={C.muted} fontSize={compact ? 5 : 7} textAnchor="middle">{e.type}</text></g>);
      })}
      {nodes.slice(0, visN).map((n, i) => {
        const shape = shapeFor(n.type);
        const r = compact ? 10 : 16;
        return (
          <g key={n.id} filter="url(#glow2)" style={{ animation: `nodeAppear 0.5s ease-out ${i * 0.08}s both` }}>
            {shape === "circle" && <circle cx={n.x} cy={n.y} r={r} fill={n.color} opacity={0.85} />}
            {shape === "triangle" && <polygon points={`${n.x},${n.y - r - 2} ${n.x - r},${n.y + r * 0.6} ${n.x + r},${n.y + r * 0.6}`} fill={n.color} opacity={0.85} />}
            {shape === "diamond" && <polygon points={`${n.x},${n.y - r - 2} ${n.x + r},${n.y} ${n.x},${n.y + r + 2} ${n.x - r},${n.y}`} fill={n.color} opacity={0.85} />}
            {shape === "square" && <rect x={n.x - r + 2} y={n.y - r + 2} width={(r - 2) * 2} height={(r - 2) * 2} rx={3} fill={n.color} opacity={0.85} />}
            <text x={n.x} y={n.y + r + 12} fill={C.text} fontSize={compact ? 7 : 9} textAnchor="middle" fontWeight={600}>{n.label}</text>
          </g>
        );
      })}
    </svg>
  );
}

// ─── FE Shell Mockup ───
function FEShellMockup({ activeMsg = 4, activeTab = "context", highlightNode = null }) {
  const msgs = [
    { role: "user", text: "Hi, I was charged twice for my Nimbus Pro subscription." },
    { role: "agent", text: "I can see your account, Sarah. Let me look into that duplicate charge.", ctx: 3 },
    { role: "user", text: "Both charges are for $49.99 on March 1st and 3rd." },
    { role: "agent", text: "Found it — processing error. Refund of $49.99 initiated to card ending 4242.", ctx: 4 },
    { role: "user", text: "Thanks! Please follow up via email. I'm usually in deep work." },
    { role: "agent", text: "Noted your preference for email. Refund processes in 3-5 days.", ctx: 5 },
  ];
  const contextNodes = [
    { type: "Entity", label: "Sarah Chen", score: 0.95, reason: "direct" },
    { type: "Event", label: "billing_lookup", score: 0.91, reason: "causal" },
    { type: "Entity", label: "Nimbus Pro", score: 0.87, reason: "referenced" },
    { type: "Preference", label: "Email only", score: 0.82, reason: "proactive" },
    { type: "Skill", label: "Engineering Lead", score: 0.78, reason: "proactive" },
  ];
  const typeColor = { Entity: C.green, Event: C.accent, Preference: C.cyan, Skill: C.cyan, Summary: C.purple };
  return (
    <div style={{ display: "flex", height: 320, borderRadius: 12, overflow: "hidden", border: `1px solid ${C.border}`, background: C.bg, fontSize: 11 }}>
      <div style={{ width: 210, borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column" }}>
        <div style={{ padding: "7px 10px", borderBottom: `1px solid ${C.border}`, display: "flex", alignItems: "center", gap: 6 }}>
          <div style={{ width: 6, height: 6, borderRadius: "50%", background: C.accent }} />
          <span style={{ color: C.text, fontWeight: 600, fontSize: 9 }}>The Billing Problem</span>
        </div>
        <div style={{ flex: 1, overflow: "hidden", padding: 6, display: "flex", flexDirection: "column", gap: 5 }}>
          {msgs.slice(0, activeMsg + 1).map((m, i) => (
            <div key={i} style={{ animation: i === activeMsg ? "slideUp 0.4s ease-out" : "none" }}>
              <div style={{ padding: "5px 7px", borderRadius: 7, fontSize: 9, lineHeight: 1.4, background: m.role === "user" ? C.surfaceHover : "rgba(59,130,246,0.1)", color: C.text, maxWidth: "90%", marginLeft: m.role === "user" ? "auto" : 0, border: m.role === "agent" ? `1px solid rgba(59,130,246,0.15)` : "none" }}>{m.text}</div>
              {m.ctx && <div style={{ fontSize: 7, color: C.accent, paddingLeft: 3, marginTop: 1 }}>● {m.ctx} context nodes</div>}
            </div>
          ))}
        </div>
      </div>
      <div style={{ flex: 1, position: "relative", background: `radial-gradient(circle at center, ${C.surfaceHover} 0%, ${C.bg} 100%)` }}>
        <AnimatedGraph phase={Math.min(1, (activeMsg + 1) / 6)} compact />
      </div>
      <div style={{ width: 180, borderLeft: `1px solid ${C.border}`, display: "flex", flexDirection: "column" }}>
        <div style={{ display: "flex", borderBottom: `1px solid ${C.border}` }}>
          {["Context", "User", "Scores"].map(t => (
            <button key={t} style={{ flex: 1, padding: "6px 0", fontSize: 8, fontWeight: 500, border: "none", cursor: "pointer", background: "transparent", color: activeTab === t.toLowerCase() ? C.accent : C.muted, borderBottom: activeTab === t.toLowerCase() ? `2px solid ${C.accent}` : "2px solid transparent" }}>{t}</button>
          ))}
        </div>
        <div style={{ flex: 1, overflow: "hidden", padding: 6 }}>
          {activeTab === "context" && contextNodes.map((n, i) => (
            <div key={i} style={{ padding: "4px 5px", borderRadius: 5, background: C.surfaceHover, display: "flex", alignItems: "center", gap: 5, marginBottom: 3, border: highlightNode === i ? `1px solid ${C.accent}` : `1px solid transparent`, animation: `fadeIn 0.3s ease-out ${i * 0.08}s both` }}>
              <div style={{ width: 3, height: 16, borderRadius: 2, background: typeColor[n.type] || C.muted }} />
              <div style={{ flex: 1 }}><div style={{ fontSize: 8, color: C.text, fontWeight: 500 }}>{n.label}</div><div style={{ fontSize: 6.5, color: C.muted }}>{n.type} · {n.reason}</div></div>
              <div style={{ fontSize: 8, fontWeight: 700, color: n.score > 0.9 ? C.green : C.amber }}>{n.score.toFixed(2)}</div>
            </div>
          ))}
          {activeTab === "user" && (
            <div style={{ textAlign: "center", padding: 6 }}>
              <div style={{ width: 28, height: 28, borderRadius: "50%", background: `linear-gradient(135deg, ${C.accent}, ${C.purple})`, margin: "0 auto 4px", display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: 11 }}>SC</div>
              <div style={{ color: C.text, fontWeight: 600, fontSize: 9 }}>Sarah Chen</div>
              <div style={{ color: C.muted, fontSize: 7, marginBottom: 6 }}>Engineering Lead</div>
              {[["Prefs", "Email, dark mode"], ["Skills", "React, System Design"], ["Patterns", "Deep work, async"]].map(([k, v]) => (
                <div key={k} style={{ padding: "3px 5px", background: C.surfaceHover, borderRadius: 3, marginBottom: 3, textAlign: "left" }}>
                  <div style={{ fontSize: 7, color: C.accent, fontWeight: 600 }}>{k}</div>
                  <div style={{ fontSize: 7, color: C.text }}>{v}</div>
                </div>
              ))}
            </div>
          )}
          {activeTab === "scores" && (
            <ResponsiveContainer width="100%" height={120}>
              <RadarChart data={[{ f: "Recency", v: 92 }, { f: "Importance", v: 78 }, { f: "Relevance", v: 88 }, { f: "Affinity", v: 65 }]}>
                <PolarGrid stroke={C.border} /><PolarAngleAxis dataKey="f" tick={{ fontSize: 7, fill: C.muted }} />
                <Radar dataKey="v" stroke={C.accent} fill={C.accent} fillOpacity={0.3} />
              </RadarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Decay Curve ───
function DecayCurve({ height = 150 }) {
  const data = Array.from({ length: 50 }, (_, i) => ({
    hour: i, score: Math.exp(-0.03 * i) * 100,
    boosted: Math.exp(-0.03 * i) * 100 * (1 + (i > 20 && i < 30 ? 0.4 : 0)),
  }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <XAxis dataKey="hour" tick={{ fontSize: 8, fill: C.muted }} />
        <YAxis tick={{ fontSize: 8, fill: C.muted }} domain={[0, 100]} />
        <Line type="monotone" dataKey="score" stroke={C.accent} dot={false} strokeWidth={2} />
        <Line type="monotone" dataKey="boosted" stroke={C.green} dot={false} strokeWidth={2} strokeDasharray="4 3" />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ═══════════════════════════════════════════════════════
// SLIDES
// ═══════════════════════════════════════════════════════

function TitleSlide() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", textAlign: "center", gap: 24, animation: "fadeIn 1s ease-out" }}>
      <div style={{ width: 80, height: 80, borderRadius: "50%", background: `linear-gradient(135deg, ${C.accent}, ${C.purple})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 0 60px ${C.accentGlow}` }}>
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><circle cx="12" cy="12" r="3" /><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" /></svg>
      </div>
      <h1 style={{ fontSize: 42, fontWeight: 800, color: C.text, letterSpacing: -1, margin: 0 }}>Context Graph</h1>
      <p style={{ fontSize: 20, color: C.accent, fontWeight: 500, margin: 0 }}>Intelligent Memory for AI Agents</p>
      <p style={{ fontSize: 14, color: C.muted, maxWidth: 520, lineHeight: 1.6, margin: 0 }}>
        A traceability-first system that gives AI agents the ability to remember,
        reason about context, and deliver personalized experiences — with full provenance.
      </p>
      <div style={{ display: "flex", gap: 16, marginTop: 8 }}>
        {["Traceable", "Immutable", "Intelligent"].map(w => (
          <span key={w} style={{ padding: "6px 16px", borderRadius: 20, border: `1px solid ${C.border}`, color: C.mutedLight, fontSize: 12, fontWeight: 500 }}>{w}</span>
        ))}
      </div>
    </div>
  );
}

function ProblemSlide() {
  const problems = [
    { icon: "🔄", title: "Agents Forget", desc: "Each session starts from scratch. Past interactions, preferences, and decisions are lost forever." },
    { icon: "🔍", title: "No Traceability", desc: "When an agent uses context, there's no provenance — you can't trace back to the source event." },
    { icon: "👤", title: "No Personalization", desc: "Agents treat every user the same. No memory of preferences, skills, or behavioral patterns." },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "20px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 8px", textAlign: "center" }}>The Problem</h2>
      <p style={{ fontSize: 14, color: C.muted, textAlign: "center", margin: "0 0 32px" }}>Today's AI agents have a critical memory gap</p>
      <div style={{ display: "flex", gap: 20, flex: 1, alignItems: "center", justifyContent: "center" }}>
        {problems.map((p, i) => (
          <Card key={i} delay={i * 0.15} style={{ flex: 1, maxWidth: 240, textAlign: "center", padding: 24, borderRadius: 16 }}>
            <div style={{ fontSize: 36, marginBottom: 12 }}>{p.icon}</div>
            <h3 style={{ fontSize: 16, color: C.text, fontWeight: 700, margin: "0 0 8px" }}>{p.title}</h3>
            <p style={{ fontSize: 12, color: C.mutedLight, lineHeight: 1.6, margin: 0 }}>{p.desc}</p>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ── NEW: Memory Types Slide ──
function MemoryTypesSlide() {
  const types = [
    {
      name: "Sensory", brain: "Sensory Cortex", system: "Event Ingestion", color: C.red,
      desc: "Transient buffer — millisecond-level capture of raw agent actions via Redis Streams XADD",
      nodeTypes: ["Raw Events"], retention: "< 1s processing", icon: "⚡"
    },
    {
      name: "Working", brain: "Prefrontal Cortex", system: "Neo4j Hot Tier", color: C.amber,
      desc: "Active query context — full-detail graph nodes with all edges and derived attributes",
      nodeTypes: ["Event", "Entity"], retention: "< 24 hours", icon: "🧠"
    },
    {
      name: "Episodic", brain: "Hippocampus", system: "Redis Event Ledger", color: C.accent,
      desc: "Append-only source of truth — specific bounded temporal events with full provenance",
      nodeTypes: ["Event (immutable)"], retention: "7-90 days", icon: "📖"
    },
    {
      name: "Semantic", brain: "Temporal Lobe", system: "Neo4j Graph", color: C.green,
      desc: "Consolidated relationships — multi-hop traversal, summaries, entity networks",
      nodeTypes: ["Entity", "Summary"], retention: "Permanent", icon: "🔗"
    },
    {
      name: "Procedural", brain: "Basal Ganglia", system: "Workflow & Pattern Nodes", color: C.purple,
      desc: "Behavioral abstraction — recurring action sequences, skills, delegation patterns",
      nodeTypes: ["Workflow", "BehavioralPattern", "Skill"], retention: "Cross-session", icon: "⚙️"
    },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "12px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Cognitive Memory Architecture</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 6px" }}>Grounded in Complementary Learning Systems (CLS) theory — mapping human memory to system components</p>
      <div style={{ display: "flex", gap: 4, marginBottom: 10, justifyContent: "center" }}>
        <Pill color={C.cyan}>Liang et al. 2025</Pill>
        <Pill color={C.cyan}>HiMeS 2026</Pill>
        <Pill color={C.cyan}>MAGMA 2026</Pill>
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 7, flex: 1, justifyContent: "center" }}>
        {types.map((t, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: 14, padding: "10px 16px", borderRadius: 10,
            background: C.surface, border: `1px solid ${C.border}`,
            animation: `slideRight 0.4s ease-out ${i * 0.08}s both`
          }}>
            <div style={{ fontSize: 22, width: 36, textAlign: "center", flexShrink: 0 }}>{t.icon}</div>
            <div style={{ width: 90, flexShrink: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: t.color }}>{t.name}</div>
              <div style={{ fontSize: 8, color: C.muted }}>{t.brain}</div>
            </div>
            <div style={{ width: 2, height: 30, background: t.color, opacity: 0.4, borderRadius: 1, flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: C.text, marginBottom: 2 }}>{t.system}</div>
              <div style={{ fontSize: 9.5, color: C.mutedLight, lineHeight: 1.4 }}>{t.desc}</div>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 3, alignItems: "flex-end", flexShrink: 0 }}>
              {t.nodeTypes.map(nt => <Pill key={nt} color={t.color}>{nt}</Pill>)}
              <span style={{ fontSize: 8, color: C.muted }}>{t.retention}</span>
            </div>
          </div>
        ))}
      </div>
      <div style={{ display: "flex", justifyContent: "center", gap: 24, marginTop: 6, padding: "8px 0", borderTop: `1px solid ${C.border}` }}>
        {[["Redis = Hippocampus", "Fast episodic encoding, rapid plasticity"], ["Neo4j = Neocortex", "Slow consolidation, stable long-term storage"], ["Workers = Systems Consolidation", "Offline replay transfers episodic → semantic"]].map(([k, v], i) => (
          <div key={i} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: C.accent }}>{k}</div>
            <div style={{ fontSize: 8, color: C.muted }}>{v}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── NEW: Consolidation Pipeline Slide ──
function ConsolidationSlide() {
  const stages = [
    {
      num: "1", name: "Event Projection", consumer: "Consumer 1: GraphProjection", timing: "Real-time, per-event",
      color: C.accent, llm: false,
      ops: ["MERGE :Event node in Neo4j", "Create FOLLOWS edges (temporal ordering)", "Create CAUSED_BY edges (explicit causality)"],
      input: "Raw events from Redis Streams", output: "EventNode + temporal/causal edges"
    },
    {
      num: "2", name: "Enrichment", consumer: "Consumer 3: Enrichment", timing: "Async, batch-oriented",
      color: C.green, llm: false,
      ops: ["Extract keywords from payload", "Compute 384-dim embeddings", "Create SIMILAR_TO edges (cosine > 0.85)", "Create REFERENCES edges (entity mentions)"],
      input: "Projected event nodes", output: "Semantic + entity edges, derived attributes"
    },
    {
      num: "3", name: "Session Extraction", consumer: "Consumer 2: Extraction", timing: "On session_end",
      color: C.purple, llm: true,
      ops: ["LLM extracts entities, preferences, skills", "Three-tier entity resolution", "Create UserProfile / Preference / Skill nodes", "Link via DERIVED_FROM for provenance"],
      input: "Complete session events", output: "Knowledge nodes with full provenance"
    },
    {
      num: "4", name: "Re-Consolidation", consumer: "Consumer 4: Consolidation", timing: "Scheduled (every 6h)",
      color: C.amber, llm: true,
      ops: ["Group events into episodes (30-min gap)", "Create hierarchical Summary nodes", "Recompute importance from graph centrality", "Active forgetting: prune by retention tier"],
      input: "Accumulated session data", output: "Summaries + pruned graph"
    },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "12px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Memory Consolidation Pipeline</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 12px" }}>4 async consumers — mapping to biological hippocampal replay</p>
      <div style={{ display: "flex", gap: 10, flex: 1 }}>
        {stages.map((s, i) => (
          <div key={i} style={{
            flex: 1, display: "flex", flexDirection: "column", borderRadius: 10,
            background: C.surface, border: `1px solid ${C.border}`, overflow: "hidden",
            animation: `slideUp 0.4s ease-out ${i * 0.1}s both`
          }}>
            {/* Header */}
            <div style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}`, background: `${s.color}10` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 3 }}>
                <div style={{ width: 22, height: 22, borderRadius: 6, background: s.color, display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 800, fontSize: 11 }}>{s.num}</div>
                <div style={{ fontSize: 12, fontWeight: 700, color: s.color }}>{s.name}</div>
              </div>
              <div style={{ fontSize: 8, color: C.muted }}>{s.consumer}</div>
              <div style={{ display: "flex", gap: 4, marginTop: 4 }}>
                <Pill color={s.color}>{s.timing}</Pill>
                {s.llm && <Pill color={C.pink}>LLM Required</Pill>}
              </div>
            </div>
            {/* Operations */}
            <div style={{ flex: 1, padding: "8px 10px", display: "flex", flexDirection: "column", gap: 4 }}>
              <SectionTag>Operations</SectionTag>
              {s.ops.map((op, j) => (
                <div key={j} style={{ fontSize: 9, color: C.text, display: "flex", alignItems: "flex-start", gap: 4, lineHeight: 1.4 }}>
                  <span style={{ color: s.color, flexShrink: 0 }}>›</span> {op}
                </div>
              ))}
            </div>
            {/* I/O */}
            <div style={{ padding: "6px 10px", borderTop: `1px solid ${C.border}`, fontSize: 8 }}>
              <div style={{ color: C.muted }}>IN: <span style={{ color: C.mutedLight }}>{s.input}</span></div>
              <div style={{ color: C.muted }}>OUT: <span style={{ color: C.mutedLight }}>{s.output}</span></div>
            </div>
          </div>
        ))}
      </div>
      {/* Trigger & reconsolidation note */}
      <div style={{ display: "flex", gap: 16, marginTop: 8, padding: "8px 16px", background: C.surface, borderRadius: 8, border: `1px solid ${C.border}` }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: C.amber }}>Reflection Trigger</div>
          <div style={{ fontSize: 9, color: C.mutedLight }}>Re-consolidation fires when accumulated importance exceeds threshold (default: 150). ~15 high-importance events trigger reflection, matching Park et al. (2023) Generative Agents.</div>
        </div>
        <div style={{ width: 1, background: C.border }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: C.green }}>Reconsolidation on Retrieval</div>
          <div style={{ fontSize: 9, color: C.mutedLight }}>When a node is queried, its access_count increments and stability grows by S_boost (24h). Retrieval strengthens memories — biological reconsolidation. Redis ledger stays immutable.</div>
        </div>
      </div>
    </div>
  );
}

// ── NEW: Architecture Patterns Slide ──
function ArchitecturePatternsSlide() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "12px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Architecture Patterns</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 14px" }}>Event Sourcing + CQRS + Hexagonal Architecture + Multi-Graph Schema</p>
      <div style={{ display: "flex", gap: 14, flex: 1 }}>
        {/* Left: Hexagonal + Dual Store */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
          {/* Hexagonal */}
          <Card delay={0} style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.purple, marginBottom: 8 }}>Hexagonal Architecture (Ports & Adapters)</div>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1 }}>
                <SectionTag>Ports (Protocol interfaces)</SectionTag>
                {["EventStore", "GraphStore", "EmbeddingService", "ExtractionService"].map((p, i) => (
                  <div key={i} style={{ fontSize: 9, color: C.text, padding: "3px 0", display: "flex", alignItems: "center", gap: 4 }}>
                    <span style={{ color: C.purple, fontSize: 10 }}>◇</span> {p}
                  </div>
                ))}
              </div>
              <div style={{ width: 1, background: C.border }} />
              <div style={{ flex: 1 }}>
                <SectionTag>Adapters (Implementations)</SectionTag>
                {[
                  { name: "Redis Store", tech: "Streams + JSON + FT.SEARCH", color: C.red },
                  { name: "Neo4j Store", tech: "MERGE-based Cypher", color: C.green },
                  { name: "LLM Client", tech: "Instructor + litellm", color: C.amber },
                ].map((a, i) => (
                  <div key={i} style={{ fontSize: 9, padding: "3px 0" }}>
                    <span style={{ color: a.color, fontWeight: 600 }}>{a.name}</span>
                    <span style={{ color: C.muted }}> — {a.tech}</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ marginTop: 8, padding: "6px 8px", background: `${C.purple}10`, borderRadius: 6, fontSize: 9, color: C.mutedLight }}>
              <span style={{ color: C.purple, fontWeight: 700 }}>Domain Core:</span> 10/11 modules have zero framework imports. Pure Python with typing.Protocol — not ABCs.
            </div>
          </Card>

          {/* Dual Store */}
          <Card delay={0.15} style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.amber, marginBottom: 8 }}>Dual Store — CLS Theory in Practice</div>
            <div style={{ display: "flex", gap: 10 }}>
              <div style={{ flex: 1, padding: 8, borderRadius: 8, background: `${C.red}10`, border: `1px solid ${C.red}20` }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: C.red, marginBottom: 4 }}>Redis Stack (Hippocampus)</div>
                <div style={{ fontSize: 9, color: C.mutedLight, lineHeight: 1.5 }}>
                  Append-only event ledger. Lua dedup scripts for idempotent ingestion. RediSearch indexes. Stream entries + JSON documents. Source of truth.
                </div>
                <div style={{ fontSize: 8, color: C.muted, marginTop: 4 }}>Role: Fast episodic encoding</div>
              </div>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: C.muted, fontSize: 10 }}>
                <div>Projection</div>
                <div style={{ fontSize: 16 }}>→</div>
                <div style={{ fontSize: 8 }}>4 consumers</div>
              </div>
              <div style={{ flex: 1, padding: 8, borderRadius: 8, background: `${C.green}10`, border: `1px solid ${C.green}20` }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: C.green, marginBottom: 4 }}>Neo4j Community (Neocortex)</div>
                <div style={{ fontSize: 9, color: C.mutedLight, lineHeight: 1.5 }}>
                  Derived, rebuildable graph. 8 node types, 16 edge types. MERGE-based idempotent writes. Intent-weighted traversal.
                </div>
                <div style={{ fontSize: 8, color: C.muted, marginTop: 4 }}>Role: Stable long-term knowledge</div>
              </div>
            </div>
          </Card>
        </div>

        {/* Right: CQRS + Multi-Graph */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
          {/* CQRS */}
          <Card delay={0.1} style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.accent, marginBottom: 8 }}>Event Sourcing + CQRS</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {[
                { path: "Write (Command)", desc: "POST /v1/events → validate → Redis XADD", detail: "Idempotent via Lua dedup. Global position auto-assigned.", color: C.accent },
                { path: "Read (Query)", desc: "POST /v1/query → intent classify → weighted traversal → Atlas", detail: "Decay-scored, bounded by max_nodes/depth/timeout.", color: C.green },
                { path: "Projection (Async)", desc: "Redis Streams → 4 Consumer Groups → Neo4j MERGE", detail: "Continuous replay. Consumer offset tracking. Replayable.", color: C.purple },
              ].map((p, i) => (
                <div key={i} style={{ padding: "6px 8px", borderRadius: 6, background: C.surfaceHover, borderLeft: `3px solid ${p.color}` }}>
                  <div style={{ fontSize: 10, fontWeight: 700, color: p.color }}>{p.path}</div>
                  <div style={{ fontSize: 9, color: C.text }}>{p.desc}</div>
                  <div style={{ fontSize: 8, color: C.muted }}>{p.detail}</div>
                </div>
              ))}
            </div>
          </Card>

          {/* Multi-Graph */}
          <Card delay={0.2} style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.teal, marginBottom: 8 }}>5 Orthogonal Graph Views (ADR-0009)</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {[
                { view: "Temporal", edge: "FOLLOWS", desc: "Event → Event: session ordering", color: C.accent },
                { view: "Causal", edge: "CAUSED_BY", desc: "Event → Event: parent-child dependency", color: C.red },
                { view: "Semantic", edge: "SIMILAR_TO", desc: "Event → Event: embedding similarity > 0.85", color: C.green },
                { view: "Entity", edge: "REFERENCES", desc: "Event → Entity: shared object mentions", color: C.amber },
                { view: "Hierarchical", edge: "SUMMARIZES", desc: "Summary → Event: abstraction levels", color: C.purple },
              ].map((v, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 9 }}>
                  <div style={{ width: 60, fontWeight: 600, color: v.color }}>{v.view}</div>
                  <div style={{ padding: "2px 6px", borderRadius: 3, background: `${v.color}15`, color: v.color, fontSize: 8, fontWeight: 600, fontFamily: "monospace" }}>{v.edge}</div>
                  <div style={{ color: C.mutedLight, flex: 1 }}>{v.desc}</div>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 6, fontSize: 8, color: C.muted, padding: "4px 6px", background: `${C.teal}08`, borderRadius: 4 }}>
              Intent-weighted traversal: "why?" amplifies CAUSED_BY 5x. "when?" amplifies FOLLOWS 5x. Same graph, different paths.
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ── NEW: Entity Reconciliation Slide ──
function EntityReconciliationSlide() {
  const tiers = [
    {
      num: "1", name: "Exact Match", method: "Deterministic", color: C.green, confidence: "1.0", action: "MERGE",
      desc: "Normalize name → resolve via alias dictionary → compare canonical forms",
      example: '"quickbooks" → ["qb", "qbo", "quickbooks online"] all resolve to canonical',
      aliases: ["JavaScript → js", "PostgreSQL → postgres, psql, pg", "GitHub → gh"],
      neo4j: "Reuse existing Entity node. Add REFERENCES edges.",
    },
    {
      num: "2a", name: "Fuzzy String", method: "Similarity-based", color: C.amber, confidence: "≥ 0.9", action: "SAME_AS / RELATED_TO",
      desc: "SequenceMatcher character-level ratio across original, canonical, and aliased forms",
      example: '"React.js" vs "ReactJS" → similarity 0.92 → SAME_AS',
      aliases: ["Compares multiple name forms", "Threshold: 0.9 for match", "Types must agree for SAME_AS"],
      neo4j: "Create new entity. Link via SAME_AS or RELATED_TO edge.",
    },
    {
      num: "2b", name: "Semantic", method: "Embedding-based", color: C.purple, confidence: "≥ 0.75", action: "SAME_AS / RELATED_TO",
      desc: "Cosine similarity of entity name embeddings — catches conceptual equivalence",
      example: '"payment processing" and "billing system" → cosine 0.82 → RELATED_TO',
      aliases: ["SAME_AS: cosine ≥ 0.90", "RELATED_TO: cosine ≥ 0.75", "Never produces MERGE (only links)"],
      neo4j: "Create new entity. Link via semantic relationship edge.",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "12px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Three-Tier Entity Reconciliation</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 6px" }}>Grounded in SKOS/SSSOM standards (ADR-0011) — cascading resolution with confidence ceilings</p>
      <div style={{ display: "flex", gap: 4, justifyContent: "center", marginBottom: 12 }}>
        <Pill color={C.cyan}>domain/entity_resolution.py</Pill>
        <Pill color={C.cyan}>worker/extraction.py</Pill>
      </div>

      {/* Cascade flow */}
      <div style={{ display: "flex", gap: 10, flex: 1 }}>
        {tiers.map((t, i) => (
          <div key={i} style={{
            flex: 1, display: "flex", flexDirection: "column", borderRadius: 10,
            background: C.surface, border: `1px solid ${C.border}`, overflow: "hidden",
            animation: `slideUp 0.4s ease-out ${i * 0.12}s both`
          }}>
            <div style={{ padding: "10px 12px", borderBottom: `1px solid ${C.border}`, background: `${t.color}08` }}>
              <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                <div style={{ width: 24, height: 24, borderRadius: 6, background: t.color, display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 800, fontSize: 11 }}>{t.num}</div>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 700, color: t.color }}>{t.name}</div>
                  <div style={{ fontSize: 8, color: C.muted }}>{t.method}</div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 4 }}>
                <Pill color={t.color}>Confidence: {t.confidence}</Pill>
                <Pill color={C.text}>→ {t.action}</Pill>
              </div>
            </div>
            <div style={{ flex: 1, padding: "8px 12px", display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ fontSize: 10, color: C.text, lineHeight: 1.5 }}>{t.desc}</div>
              <div style={{ padding: "6px 8px", borderRadius: 6, background: C.surfaceHover, fontSize: 9, color: C.mutedLight, fontStyle: "italic" }}>
                {t.example}
              </div>
              <div>
                <SectionTag>Key Rules</SectionTag>
                {t.aliases.map((a, j) => (
                  <div key={j} style={{ fontSize: 9, color: C.mutedLight, display: "flex", alignItems: "center", gap: 4, padding: "2px 0" }}>
                    <span style={{ color: t.color }}>›</span> {a}
                  </div>
                ))}
              </div>
            </div>
            <div style={{ padding: "6px 12px", borderTop: `1px solid ${C.border}`, fontSize: 8, color: C.muted }}>
              Neo4j: {t.neo4j}
            </div>
          </div>
        ))}
      </div>

      {/* Resolution flow + fallback */}
      <div style={{ display: "flex", gap: 12, marginTop: 10, alignItems: "center" }}>
        <div style={{ flex: 1, padding: "8px 12px", background: C.surface, borderRadius: 8, border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: C.text, marginBottom: 4 }}>Resolution Cascade</div>
          <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 9 }}>
            <span style={{ padding: "3px 8px", borderRadius: 4, background: `${C.green}15`, color: C.green, fontWeight: 600 }}>Tier 1: Exact</span>
            <span style={{ color: C.muted }}>miss →</span>
            <span style={{ padding: "3px 8px", borderRadius: 4, background: `${C.amber}15`, color: C.amber, fontWeight: 600 }}>Tier 2a: Fuzzy</span>
            <span style={{ color: C.muted }}>miss →</span>
            <span style={{ padding: "3px 8px", borderRadius: 4, background: `${C.purple}15`, color: C.purple, fontWeight: 600 }}>Tier 2b: Semantic</span>
            <span style={{ color: C.muted }}>miss →</span>
            <span style={{ padding: "3px 8px", borderRadius: 4, background: `${C.accent}15`, color: C.accent, fontWeight: 600 }}>CREATE new entity</span>
          </div>
        </div>
        <div style={{ padding: "8px 12px", background: C.surface, borderRadius: 8, border: `1px solid ${C.border}` }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: C.pink, marginBottom: 2 }}>Provenance Chain</div>
          <div style={{ fontSize: 9, color: C.mutedLight }}>Every entity links back to source events via <span style={{ color: C.pink, fontWeight: 600 }}>DERIVED_FROM</span> edges</div>
        </div>
      </div>
    </div>
  );
}

// ── NEW: Research Landscape Slide ──
function ResearchLandscapeSlide() {
  const clusters = [
    {
      name: "Graph-Based Memory", color: C.accent, icon: "🔗",
      papers: [
        { title: "Graph-based Agent Memory Survey", authors: "Yang et al. (18 authors)", date: "Feb 2026", finding: "Taxonomy of 5 graph types + 4-stage lifecycle", arxiv: "2602.05665" },
        { title: "MAGMA: Multi-Graph Agentic Memory", authors: "Jiang et al.", date: "Jan 2026", finding: "4 orthogonal views, 45.5% higher reasoning accuracy", arxiv: "2601.03236" },
        { title: "A-MEM: Agentic Memory (NeurIPS)", authors: "Xu et al.", date: "Feb 2025", finding: "Zettelkasten-inspired, bidirectional evolution", arxiv: "2502.12110" },
      ]
    },
    {
      name: "Agent Memory Architectures", color: C.green, icon: "🧠",
      papers: [
        { title: "Memory in the Age of AI Agents", authors: "Hu et al. (47 authors)", date: "Dec 2025", finding: "Unified framework: Forms + Functions + Dynamics", arxiv: "2512.13564" },
        { title: "Rethinking Memory Mechanisms", authors: "Huang et al. (60 authors)", date: "Feb 2026", finding: "3-factor scoring formula: recency + importance + relevance", arxiv: "2602.06052" },
        { title: "Episodic Memory is the Missing Piece", authors: "Pink, Wu, Vo et al.", date: "Feb 2025", finding: "5 defining properties of episodic memory", arxiv: "2502.06975" },
      ]
    },
    {
      name: "Neuroscience-Inspired", color: C.purple, icon: "🧬",
      papers: [
        { title: "AI Meets Brain: Memory Systems", authors: "Liang et al. (15 authors)", date: "Dec 2025", finding: "CLS theory bridge: hippocampal-neocortical consolidation", arxiv: "2512.23343" },
        { title: "HiMeS: Hippocampus-Inspired", authors: "Li et al.", date: "Jan 2026", finding: "Dual-memory + RL compression, 55.5% alignment", arxiv: "2601.06152" },
        { title: "HiCL: Hippocampal Circuit Learning", authors: "Kapoor et al.", date: "Aug 2025", finding: "EC → DG → CA3 → CA1 circuit mapping to software", arxiv: "2508.16651" },
      ]
    },
    {
      name: "Production Systems", color: C.amber, icon: "⚙️",
      papers: [
        { title: "Zep / Graphiti", authors: "Zep AI", date: "Jan 2025", finding: "Temporal KG for agents, P95 latency 300ms", arxiv: "2501.13956" },
        { title: "Mem0: Production-Ready Memory", authors: "ECAI 2025", date: "2025", finding: "Scalable long-term memory with graph modeling", arxiv: "2504.19413" },
        { title: "Memoria: Hybrid Architecture", authors: "Dec 2025", date: "Dec 2025", finding: "Summarization + weighted KG, 87.1% accuracy", arxiv: "2512.12686" },
      ]
    },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "10px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Research Foundations</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 10px" }}>12 papers across 4 research clusters informed every architectural decision (Dec 2025 – Feb 2026)</p>
      <div style={{ display: "flex", gap: 8, flex: 1 }}>
        {clusters.map((cl, ci) => (
          <div key={ci} style={{
            flex: 1, borderRadius: 10, background: C.surface, border: `1px solid ${C.border}`, overflow: "hidden",
            display: "flex", flexDirection: "column", animation: `slideUp 0.4s ease-out ${ci * 0.1}s both`
          }}>
            <div style={{ padding: "8px 10px", borderBottom: `1px solid ${C.border}`, background: `${cl.color}08`, display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ fontSize: 18 }}>{cl.icon}</span>
              <div>
                <div style={{ fontSize: 11, fontWeight: 700, color: cl.color }}>{cl.name}</div>
                <div style={{ fontSize: 8, color: C.muted }}>{cl.papers.length} papers</div>
              </div>
            </div>
            <div style={{ flex: 1, padding: "6px 8px", display: "flex", flexDirection: "column", gap: 6 }}>
              {cl.papers.map((p, pi) => (
                <div key={pi} style={{ padding: "6px 8px", borderRadius: 6, background: C.surfaceHover, borderLeft: `3px solid ${cl.color}`, animation: `fadeIn 0.3s ease-out ${ci * 0.1 + pi * 0.08}s both` }}>
                  <div style={{ fontSize: 9.5, fontWeight: 600, color: C.text, lineHeight: 1.3, marginBottom: 2 }}>{p.title}</div>
                  <div style={{ fontSize: 7.5, color: C.muted, marginBottom: 3 }}>{p.authors} · {p.date}</div>
                  <div style={{ fontSize: 8.5, color: cl.color, fontWeight: 500, lineHeight: 1.3 }}>{p.finding}</div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div style={{ marginTop: 6, padding: "6px 16px", background: C.surface, borderRadius: 8, border: `1px solid ${C.border}`, display: "flex", alignItems: "center", justifyContent: "center", gap: 20, fontSize: 9 }}>
        <span style={{ color: C.text, fontWeight: 600 }}>Key Insight:</span>
        <span style={{ color: C.mutedLight }}>No existing system combines immutable event sourcing + graph lineage + provenance-annotated retrieval</span>
        <span style={{ color: C.accent, fontWeight: 600 }}>— Context Graph fills this gap</span>
      </div>
    </div>
  );
}

// ── NEW: Neuroscience Foundation Slide ──
function NeuroscienceSlide() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "10px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Neuroscience Foundation</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 10px" }}>Complementary Learning Systems (CLS) theory maps directly to our dual-store architecture</p>
      <div style={{ display: "flex", gap: 14, flex: 1 }}>
        {/* Left: Brain mapping */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
          <Card delay={0} style={{ flex: 1, padding: 14 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.purple, marginBottom: 8 }}>Brain → System Mapping</div>
            {[
              { brain: "Hippocampus", arrow: "→", system: "Redis Stack", desc: "Fast episodic encoding. Sparse pointers (stream entry IDs), not full content. Sub-millisecond append.", color: C.red, brainDesc: "Rapid learning, pattern separation" },
              { brain: "Neocortex", arrow: "→", system: "Neo4j Graph", desc: "Slow consolidation into stable knowledge. Entity networks, summaries, behavioral patterns.", color: C.green, brainDesc: "Slow integration, generalization" },
              { brain: "Systems Consolidation", arrow: "→", system: "4 Consumer Workers", desc: "Offline replay transfers structure from episodic to semantic. Runs async on Redis Streams.", color: C.amber, brainDesc: "Sleep replay, memory transfer" },
              { brain: "Prefrontal Cortex", arrow: "→", system: "Working Memory (API)", desc: "Active context window. Bounded queries (max 100 nodes, depth 3). Miller's 7±2 constraint.", color: C.accent, brainDesc: "Executive control, attention" },
              { brain: "Basal Ganglia", arrow: "→", system: "Workflow / Pattern Nodes", desc: "Procedural memory: learned sequences, habits, skill automation. Cross-session persistence.", color: C.cyan, brainDesc: "Habit learning, motor skills" },
            ].map((m, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0", borderBottom: i < 4 ? `1px solid ${C.border}` : "none", animation: `slideRight 0.4s ease-out ${i * 0.08}s both` }}>
                <div style={{ width: 120, flexShrink: 0 }}>
                  <div style={{ fontSize: 11, fontWeight: 700, color: m.color }}>{m.brain}</div>
                  <div style={{ fontSize: 7.5, color: C.muted }}>{m.brainDesc}</div>
                </div>
                <div style={{ fontSize: 14, color: C.muted, flexShrink: 0 }}>→</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: C.text }}>{m.system}</div>
                  <div style={{ fontSize: 8.5, color: C.mutedLight, lineHeight: 1.4 }}>{m.desc}</div>
                </div>
              </div>
            ))}
          </Card>
        </div>

        {/* Right: Key mechanisms + research */}
        <div style={{ width: 300, display: "flex", flexDirection: "column", gap: 8 }}>
          <Card delay={0.15} style={{ padding: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: C.amber, marginBottom: 6 }}>Ebbinghaus Forgetting Curve (1885)</div>
            <div style={{ fontFamily: "monospace", fontSize: 16, color: C.text, textAlign: "center", padding: "8px 0", background: C.surfaceHover, borderRadius: 6, marginBottom: 6 }}>
              R = e<sup style={{ fontSize: 12 }}>−t/S</sup>
            </div>
            <div style={{ fontSize: 9, color: C.mutedLight, lineHeight: 1.5 }}>
              R = retention, t = time elapsed, S = stability (grows with each retrieval). Every access reinforces memory — biological reconsolidation. Our S_base = 168h (1 week), S_boost = 24h per access.
            </div>
          </Card>

          <Card delay={0.25} style={{ padding: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: C.pink, marginBottom: 6 }}>Hippocampal Replay (HiCL, Kapoor 2025)</div>
            <div style={{ display: "flex", alignItems: "center", gap: 4, justifyContent: "center", marginBottom: 6 }}>
              {["EC", "DG", "CA3", "CA1"].map((region, i) => (
                <React.Fragment key={region}>
                  <div style={{ padding: "4px 8px", borderRadius: 4, background: `${C.pink}15`, color: C.pink, fontSize: 9, fontWeight: 700 }}>{region}</div>
                  {i < 3 && <span style={{ color: C.muted, fontSize: 10 }}>→</span>}
                </React.Fragment>
              ))}
            </div>
            <div style={{ fontSize: 8, color: C.mutedLight, lineHeight: 1.5 }}>
              Grid-cell encoding → Pattern separation (UUIDs + provenance) → Pattern completion (lineage queries) → Integration (graph traversal). Our projection pipeline mirrors this circuit.
            </div>
          </Card>

          <Card delay={0.3} style={{ padding: 12 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: C.green, marginBottom: 6 }}>Key Research Validations</div>
            {[
              { paper: "Liang et al. 2025", finding: "CLS theory directly applicable to agent memory" },
              { paper: "Li et al. 2026 (HiMeS)", finding: "Dual-memory outperforms single-store by 55.5%" },
              { paper: "Pink et al. 2025", finding: "Episodic + semantic = necessary and sufficient" },
              { paper: "Park et al. 2023", finding: "~15 high-importance events trigger reflection" },
            ].map((r, i) => (
              <div key={i} style={{ padding: "4px 0", borderBottom: i < 3 ? `1px solid ${C.border}` : "none", fontSize: 8.5 }}>
                <span style={{ color: C.green, fontWeight: 600 }}>{r.paper}: </span>
                <span style={{ color: C.mutedLight }}>{r.finding}</span>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}

// ── NEW: Industry Gap Analysis Slide ──
function IndustryGapSlide() {
  const frameworks = [
    { name: "LangSmith", trace: "Run tree", agent: "None", session: "Project", ledger: false, prov: false, graph: false, color: C.accent },
    { name: "CrewAI", trace: "OTel spans", agent: "Role-based", session: "Execution", ledger: false, prov: false, graph: false, color: C.green },
    { name: "AutoGen 0.4", trace: "Event-driven", agent: "Name-based", session: "Runtime", ledger: false, prov: false, graph: false, color: C.amber },
    { name: "OpenAI Agents", trace: "Typed spans", agent: "Name", session: "group_id", ledger: false, prov: false, graph: false, color: C.purple },
    { name: "Semantic Kernel", trace: "Fn spans", agent: "None", session: "None", ledger: false, prov: false, graph: false, color: C.pink },
    { name: "Context Graph", trace: "Event sourced", agent: "UUID + trace", session: "Full lifecycle", ledger: true, prov: true, graph: true, color: C.cyan },
  ];

  const standards = [
    { name: "OpenTelemetry GenAI", status: "Development", relevance: "Span conventions for LLM/agent tracing", mapping: "Our event_type aligns with OTel span kinds" },
    { name: "W3C PROV-DM", status: "Recommendation", relevance: "Provenance vocabulary for lineage", mapping: "DERIVED_FROM, GENERATED_BY adopted in edge types" },
    { name: "Event Sourcing (Axon/Marten)", status: "Mature pattern", relevance: "Immutable ledger + projection + replay", mapping: "Core architecture: Redis append-only + Neo4j projection" },
    { name: "SKOS / SSSOM", status: "Standard", relevance: "Entity resolution vocabulary", mapping: "Three-tier resolution with SAME_AS / RELATED_TO" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "10px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Industry Gap Analysis</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 10px" }}>No existing platform combines immutable events + graph lineage + provenance retrieval</p>
      <div style={{ display: "flex", gap: 14, flex: 1 }}>
        {/* Framework comparison */}
        <div style={{ flex: 1 }}>
          <Card delay={0} style={{ height: "100%", padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.accent, marginBottom: 8 }}>Agent Framework Landscape</div>
            <div style={{ display: "flex", gap: 4, marginBottom: 8 }}>
              {["Immutable Ledger", "Provenance Annotations", "Graph Lineage"].map(cap => (
                <Pill key={cap} color={C.cyan}>{cap}</Pill>
              ))}
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 9 }}>
              <thead>
                <tr style={{ borderBottom: `1px solid ${C.border}` }}>
                  {["Framework", "Trace Model", "Agent ID", "Ledger", "Prov.", "Graph"].map(h => (
                    <th key={h} style={{ padding: "4px 6px", textAlign: "left", color: C.muted, fontWeight: 600, fontSize: 8 }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {frameworks.map((f, i) => (
                  <tr key={i} style={{ borderBottom: `1px solid ${C.border}`, background: f.name === "Context Graph" ? `${C.cyan}08` : "transparent" }}>
                    <td style={{ padding: "5px 6px", fontWeight: 600, color: f.color }}>{f.name}</td>
                    <td style={{ padding: "5px 6px", color: C.mutedLight }}>{f.trace}</td>
                    <td style={{ padding: "5px 6px", color: C.mutedLight }}>{f.agent}</td>
                    <td style={{ padding: "5px 6px", textAlign: "center" }}>{f.ledger ? <span style={{ color: C.green }}>●</span> : <span style={{ color: C.red }}>✗</span>}</td>
                    <td style={{ padding: "5px 6px", textAlign: "center" }}>{f.prov ? <span style={{ color: C.green }}>●</span> : <span style={{ color: C.red }}>✗</span>}</td>
                    <td style={{ padding: "5px 6px", textAlign: "center" }}>{f.graph ? <span style={{ color: C.green }}>●</span> : <span style={{ color: C.red }}>✗</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div style={{ marginTop: 8, padding: "6px 8px", background: `${C.cyan}08`, borderRadius: 6, fontSize: 9, color: C.mutedLight }}>
              <span style={{ color: C.cyan, fontWeight: 700 }}>Context Graph</span> is the only system with all three capabilities. Existing platforms provide observability but not memory — they trace what happened but can't use it for future context.
            </div>
          </Card>
        </div>

        {/* Standards + Production systems */}
        <div style={{ width: 320, display: "flex", flexDirection: "column", gap: 8 }}>
          <Card delay={0.1} style={{ padding: 12 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.green, marginBottom: 8 }}>Standards Alignment</div>
            {standards.map((s, i) => (
              <div key={i} style={{ padding: "5px 0", borderBottom: i < standards.length - 1 ? `1px solid ${C.border}` : "none", animation: `fadeIn 0.3s ease-out ${i * 0.08}s both` }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 2 }}>
                  <span style={{ fontSize: 10, fontWeight: 600, color: C.text }}>{s.name}</span>
                  <Pill color={C.green}>{s.status}</Pill>
                </div>
                <div style={{ fontSize: 8, color: C.muted, marginBottom: 1 }}>{s.relevance}</div>
                <div style={{ fontSize: 8, color: C.green }}>↳ {s.mapping}</div>
              </div>
            ))}
          </Card>

          <Card delay={0.2} style={{ padding: 12, flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.amber, marginBottom: 8 }}>Production System Benchmarks</div>
            {[
              { name: "Zep/Graphiti", metric: "P95 latency", value: "300ms", desc: "Temporal KG with entity dedup" },
              { name: "MAGMA", metric: "Reasoning accuracy", value: "+45.5%", desc: "Multi-graph with intent traversal" },
              { name: "Memoria", metric: "Retrieval accuracy", value: "87.1%", desc: "Summarization + weighted KG" },
              { name: "HiMeS", metric: "Contextual alignment", value: "55.5%", desc: "Dual-memory + RL compression" },
              { name: "A-MEM", metric: "Token efficiency", value: "85-93%", desc: "Zettelkasten enriched notes" },
            ].map((b, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, padding: "4px 0", borderBottom: i < 4 ? `1px solid ${C.border}` : "none" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 9.5, fontWeight: 600, color: C.text }}>{b.name}</div>
                  <div style={{ fontSize: 7.5, color: C.muted }}>{b.desc}</div>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: 12, fontWeight: 800, color: C.amber }}>{b.value}</div>
                  <div style={{ fontSize: 7, color: C.muted }}>{b.metric}</div>
                </div>
              </div>
            ))}
          </Card>
        </div>
      </div>
    </div>
  );
}

function SolutionSlide() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "20px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 8px", textAlign: "center" }}>The Solution</h2>
      <p style={{ fontSize: 14, color: C.muted, textAlign: "center", margin: "0 0 24px" }}>An event-sourced knowledge graph with built-in memory intelligence</p>
      <div style={{ display: "flex", gap: 12, flex: 1, alignItems: "center" }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 12 }}>
          {[
            { title: "Capture", desc: "Every agent action becomes an immutable event", color: C.accent, icon: "📥" },
            { title: "Project", desc: "Events are projected into a rich knowledge graph", color: C.green, icon: "🔗" },
            { title: "Enrich", desc: "Entities extracted, embeddings computed, relationships formed", color: C.purple, icon: "✨" },
            { title: "Retrieve", desc: "Intent-weighted queries return scored, provenance-annotated context", color: C.amber, icon: "🎯" },
          ].map((s, i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, padding: "12px 16px", borderRadius: 12, background: C.surface, border: `1px solid ${C.border}`, animation: `slideRight 0.5s ease-out ${i * 0.12}s both` }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: s.color, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, flexShrink: 0 }}>{s.icon}</div>
              <div><div style={{ fontSize: 14, fontWeight: 700, color: C.text }}>{s.title}</div><div style={{ fontSize: 11, color: C.mutedLight }}>{s.desc}</div></div>
            </div>
          ))}
        </div>
        <div style={{ width: 200, display: "flex", flexDirection: "column", gap: 12, justifyContent: "center" }}>
          {[{ n: 8, label: "Node Types", sub: "Event, Entity, Summary, Profile..." }, { n: 16, label: "Edge Types", sub: "FOLLOWS, CAUSED_BY, REFERENCES..." }, { n: 8, label: "Intent Types", sub: "why, when, what, related..." }, { n: 4, label: "Consumer Workers", sub: "Projection, Extraction, Enrichment, Consolidation" }].map((s, i) => (
            <Card key={i} delay={i * 0.1 + 0.5} anim="fadeIn" style={{ padding: "10px 14px" }}>
              <div style={{ fontSize: 22, fontWeight: 800, color: C.accent }}><Counter end={s.n} duration={1200} /></div>
              <div style={{ fontSize: 11, fontWeight: 600, color: C.text }}>{s.label}</div>
              <div style={{ fontSize: 9, color: C.muted }}>{s.sub}</div>
            </Card>
          ))}
        </div>
      </div>
    </div>
  );
}

function DemoSlide({ step }) {
  const tabs = ["context", "user", "scores"];
  const tabIdx = Math.floor((step || 0) / 2) % 3;
  const msgIdx = Math.min(5, (step || 0));
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "12px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>FE Shell — Live Demo</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 14px" }}>Three-panel interface: Chat · Graph · Insights</p>
      <div style={{ flex: 1 }}><FEShellMockup activeMsg={msgIdx} activeTab={tabs[tabIdx]} highlightNode={step % 5} /></div>
      <div style={{ display: "flex", justifyContent: "center", gap: 20, marginTop: 8, fontSize: 10, color: C.muted }}>
        <span>⬅ Chat flows left</span><span>● Graph builds center</span><span>Insights update right ➡</span>
      </div>
    </div>
  );
}

function PersonaSlide() {
  const personas = [
    { name: "Sarah Chen", role: "Engineering Lead", color: C.accent, avatar: "SC", scenario: "Billing dispute → refund → preference capture", context: ["Prefers email", "Deep work blocks", "Tech lead — skip basics"], result: "Agent proactively adjusts communication style across sessions" },
    { name: "Mike Torres", role: "Product Manager", color: C.green, avatar: "MT", scenario: "Feature request → prioritization → roadmap update", context: ["Kanban workflow", "Async-first", "Needs data for decisions"], result: "Agent surfaces relevant metrics and past decisions automatically" },
    { name: "Lisa Park", role: "Customer Success", color: C.amber, avatar: "LP", scenario: "Data loss incident → escalation → recovery", context: ["High urgency patterns", "Escalation history", "Values quick resolution"], result: "Agent recognizes urgency pattern and fast-tracks response" },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "20px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 8px", textAlign: "center" }}>Persona Simulations</h2>
      <p style={{ fontSize: 14, color: C.muted, textAlign: "center", margin: "0 0 24px" }}>Context Graph learns and adapts to each user's unique patterns</p>
      <div style={{ display: "flex", gap: 16, flex: 1, alignItems: "stretch" }}>
        {personas.map((p, i) => (
          <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", padding: 18, borderRadius: 14, background: C.surface, border: `1px solid ${C.border}`, animation: `slideUp 0.5s ease-out ${i * 0.15}s both` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
              <div style={{ width: 36, height: 36, borderRadius: "50%", background: `linear-gradient(135deg, ${p.color}, ${C.purple})`, display: "flex", alignItems: "center", justifyContent: "center", color: "white", fontWeight: 700, fontSize: 13 }}>{p.avatar}</div>
              <div><div style={{ fontSize: 13, fontWeight: 700, color: C.text }}>{p.name}</div><div style={{ fontSize: 10, color: p.color }}>{p.role}</div></div>
            </div>
            <SectionTag>Scenario</SectionTag>
            <div style={{ fontSize: 11, color: C.text, marginBottom: 12, lineHeight: 1.5 }}>{p.scenario}</div>
            <SectionTag>Context Captured</SectionTag>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, marginBottom: 12 }}>
              {p.context.map((c, j) => (<div key={j} style={{ fontSize: 10, color: C.mutedLight, display: "flex", alignItems: "center", gap: 6 }}><div style={{ width: 4, height: 4, borderRadius: "50%", background: p.color, flexShrink: 0 }} />{c}</div>))}
            </div>
            <div style={{ marginTop: "auto", padding: "8px 10px", borderRadius: 8, background: `${p.color}10`, border: `1px solid ${p.color}30` }}>
              <div style={{ fontSize: 10, fontWeight: 600, color: p.color, marginBottom: 2 }}>RESULT</div>
              <div style={{ fontSize: 10, color: C.text, lineHeight: 1.5 }}>{p.result}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function MemoryIntelligenceSlide() {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "14px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 4px", textAlign: "center" }}>Decay Scoring & Active Forgetting</h2>
      <p style={{ fontSize: 13, color: C.muted, textAlign: "center", margin: "0 0 12px" }}>Ebbinghaus-inspired decay · R = e<sup>(-t/S)</sup> · 4-factor composite scoring</p>
      <div style={{ display: "flex", gap: 14, flex: 1 }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
          <Card delay={0} style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.text, marginBottom: 6 }}>Memory Decay Curve</div>
            <DecayCurve height={130} />
            <div style={{ display: "flex", gap: 12, justifyContent: "center", marginTop: 2, fontSize: 8 }}>
              <span style={{ color: C.accent }}>━ Natural decay (S_base = 168h)</span>
              <span style={{ color: C.green }}>╌ Re-accessed (S += 24h per access)</span>
            </div>
          </Card>
          <Card delay={0.1} style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 700, color: C.text, marginBottom: 6 }}>Dual-Tier Retention System</div>
            <div style={{ display: "flex", gap: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 9, fontWeight: 700, color: C.green, marginBottom: 4 }}>Neo4j Graph Tiers</div>
                {[
                  { tier: "HOT", time: "< 24h", rule: "Full detail, all edges", color: C.red },
                  { tier: "WARM", time: "1-7d", rule: "Prune SIMILAR_TO < 0.7", color: C.amber },
                  { tier: "COLD", time: "7-30d", rule: "importance < 5 AND access < 3 → delete", color: C.accent },
                  { tier: "ARCHIVE", time: "> 30d", rule: "Remove from Neo4j entirely", color: C.muted },
                ].map((t, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 0", fontSize: 8 }}>
                    <span style={{ width: 50, fontWeight: 700, color: t.color }}>{t.tier}</span>
                    <span style={{ width: 35, color: C.muted }}>{t.time}</span>
                    <span style={{ color: C.mutedLight }}>{t.rule}</span>
                  </div>
                ))}
              </div>
              <div style={{ width: 1, background: C.border }} />
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 9, fontWeight: 700, color: C.red, marginBottom: 4 }}>Redis Ledger Tiers</div>
                {[
                  { tier: "HOT", time: "0-7d", rule: "Stream entries + JSON docs", color: C.red },
                  { tier: "COLD", time: "7+ d", rule: "JSON only (streams trimmed)", color: C.accent },
                  { tier: "GONE", time: "> 90d", rule: "Deleted (summaries survive in Neo4j)", color: C.muted },
                ].map((t, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 6, padding: "3px 0", fontSize: 8 }}>
                    <span style={{ width: 50, fontWeight: 700, color: t.color }}>{t.tier}</span>
                    <span style={{ width: 35, color: C.muted }}>{t.time}</span>
                    <span style={{ color: C.mutedLight }}>{t.rule}</span>
                  </div>
                ))}
              </div>
            </div>
          </Card>
        </div>
        <div style={{ width: 250, display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.text }}>4-Factor Composite Score</div>
          <div style={{ fontSize: 8, color: C.muted, fontFamily: "monospace", padding: "4px 6px", background: C.surfaceHover, borderRadius: 4, lineHeight: 1.6 }}>
            score = w_r * recency(t)<br />
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; + w_i * importance(n)<br />
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; + w_v * relevance(q, n)<br />
            &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; + w_u * affinity(u, n)
          </div>
          {[
            { factor: "Recency", desc: "e^(-t/S), S grows with access", icon: "⏱", score: 92, weight: "1.0" },
            { factor: "Importance", desc: "hint/10 + access_boost + degree_boost", icon: "⭐", score: 78, weight: "1.0" },
            { factor: "Relevance", desc: "cosine(query_embed, node_embed)", icon: "🎯", score: 88, weight: "1.0" },
            { factor: "User Affinity", desc: "session proximity + recurrence + entity overlap", icon: "👤", score: 65, weight: "0.5" },
          ].map((f, i) => (
            <div key={i} style={{ padding: "8px 10px", borderRadius: 8, background: C.surface, border: `1px solid ${C.border}`, animation: `slideRight 0.4s ease-out ${i * 0.08}s both` }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 3 }}>
                <span style={{ fontSize: 11, fontWeight: 600, color: C.text }}>{f.icon} {f.factor}</span>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  <span style={{ fontSize: 8, color: C.muted }}>w={f.weight}</span>
                  <span style={{ fontSize: 12, fontWeight: 800, color: C.accent }}>{f.score}</span>
                </div>
              </div>
              <div style={{ fontSize: 9, color: C.muted, marginBottom: 4 }}>{f.desc}</div>
              <div style={{ height: 3, borderRadius: 2, background: C.surfaceHover }}>
                <div style={{ height: "100%", borderRadius: 2, background: C.accent, width: `${f.score}%`, transition: "width 1s ease-out" }} />
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function DifferentiatorsSlide() {
  const diffs = [
    { title: "Full Provenance", desc: "Every context node carries event_id, global_position, source, occurred_at, session_id, agent_id, trace_id.", icon: "🔗", color: C.accent },
    { title: "Immutable Ledger", desc: "Redis Streams append-only. Neo4j is derived, rebuildable. Lua dedup for idempotent ingestion.", icon: "🔒", color: C.green },
    { title: "Framework Agnostic", desc: "Domain has zero framework imports. Works with LangChain, CrewAI, or custom agents.", icon: "🧩", color: C.purple },
    { title: "Proactive Context", desc: "Infers intent and surfaces relevant context before being asked. System-owned retrieval.", icon: "🧠", color: C.amber },
    { title: "GDPR Ready", desc: "Data export + deletion endpoints. Audit trail. Automatic forgetting via retention tiers.", icon: "🛡", color: C.cyan },
    { title: "Intent-Weighted", desc: "8 intent types with edge weight maps. 'Why?' and 'When?' traverse completely different paths.", icon: "🎯", color: C.pink },
  ];
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%", padding: "20px 0" }}>
      <h2 style={{ fontSize: 28, fontWeight: 700, color: C.text, margin: "0 0 8px", textAlign: "center" }}>Key Differentiators</h2>
      <p style={{ fontSize: 14, color: C.muted, textAlign: "center", margin: "0 0 24px" }}>What makes Context Graph unique</p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14, flex: 1, alignContent: "center" }}>
        {diffs.map((d, i) => (
          <Card key={i} delay={i * 0.08} anim="fadeIn" style={{ padding: 16 }}>
            <div style={{ fontSize: 24, marginBottom: 8 }}>{d.icon}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: d.color, marginBottom: 4 }}>{d.title}</div>
            <div style={{ fontSize: 10, color: C.mutedLight, lineHeight: 1.6 }}>{d.desc}</div>
          </Card>
        ))}
      </div>
    </div>
  );
}

function ClosingSlide() {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: "100%", textAlign: "center", gap: 24, animation: "fadeIn 1s ease-out" }}>
      <div style={{ width: 64, height: 64, borderRadius: "50%", background: `linear-gradient(135deg, ${C.accent}, ${C.purple})`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 0 80px ${C.accentGlow}` }}>
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14" /><polyline points="22 4 12 14.01 9 11.01" /></svg>
      </div>
      <h2 style={{ fontSize: 36, fontWeight: 800, color: C.text, margin: 0 }}>Ready to Remember</h2>
      <p style={{ fontSize: 16, color: C.mutedLight, maxWidth: 520, lineHeight: 1.6, margin: 0 }}>
        Context Graph gives AI agents the memory they deserve — traceable, intelligent, and personalized. Grounded in cognitive science, built for production.
      </p>
      <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
        <div style={{ padding: "10px 24px", borderRadius: 10, background: C.accent, color: "white", fontSize: 14, fontWeight: 600 }}>Get Started</div>
        <div style={{ padding: "10px 24px", borderRadius: 10, border: `1px solid ${C.border}`, color: C.text, fontSize: 14, fontWeight: 500 }}>View Documentation</div>
      </div>
      <div style={{ marginTop: 20, display: "flex", gap: 16, fontSize: 10, color: C.muted }}>
        {["Complementary Learning Systems", "Ebbinghaus Decay", "MAGMA Multi-Graph", "SKOS Entity Resolution"].map(r => (
          <Pill key={r} color={C.muted}>{r}</Pill>
        ))}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════
// MAIN PRESENTATION
// ═══════════════════════════════════════════════════════

export default function ContextGraphPresentation() {
  const [slide, setSlide] = useState(0);
  const [demoStep, setDemoStep] = useState(0);
  const [autoPlay, setAutoPlay] = useState(false);
  const autoRef = useRef(null);

  const DEMO_SLIDE_INDEX = 10; // index of the DemoSlide in slides array

  const slides = [
    { title: "Context Graph", component: <TitleSlide />, duration: 8000 },
    { title: "The Problem", component: <ProblemSlide />, duration: 10000 },
    { title: "Research Foundations", component: <ResearchLandscapeSlide />, duration: 16000 },
    { title: "Neuroscience", component: <NeuroscienceSlide />, duration: 16000 },
    { title: "Industry Gap", component: <IndustryGapSlide />, duration: 14000 },
    { title: "The Solution", component: <SolutionSlide />, duration: 12000 },
    { title: "Memory Types", component: <MemoryTypesSlide />, duration: 15000 },
    { title: "Consolidation", component: <ConsolidationSlide />, duration: 15000 },
    { title: "Architecture", component: <ArchitecturePatternsSlide />, duration: 15000 },
    { title: "Entity Resolution", component: <EntityReconciliationSlide />, duration: 14000 },
    { title: "FE Shell Demo", component: <DemoSlide step={demoStep} />, duration: 15000 },
    { title: "Personas", component: <PersonaSlide />, duration: 12000 },
    { title: "Decay & Forgetting", component: <MemoryIntelligenceSlide />, duration: 14000 },
    { title: "Differentiators", component: <DifferentiatorsSlide />, duration: 10000 },
    { title: "Closing", component: <ClosingSlide />, duration: 8000 },
  ];

  const isDemoSlide = slide === DEMO_SLIDE_INDEX;

  const next = useCallback(() => {
    if (isDemoSlide && demoStep < 5) {
      setDemoStep(d => d + 1);
    } else {
      setSlide(s => Math.min(s + 1, slides.length - 1));
      setDemoStep(0);
    }
  }, [slide, demoStep, slides.length, isDemoSlide]);

  const prev = useCallback(() => {
    if (isDemoSlide && demoStep > 0) {
      setDemoStep(d => d - 1);
    } else {
      setSlide(s => Math.max(s - 1, 0));
      setDemoStep(0);
    }
  }, [slide, demoStep, isDemoSlide]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === "ArrowRight" || e.key === " ") { e.preventDefault(); next(); }
      if (e.key === "ArrowLeft") { e.preventDefault(); prev(); }
      if (e.key === "a") setAutoPlay(p => !p);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [next, prev]);

  useEffect(() => {
    if (autoPlay) {
      const dur = isDemoSlide ? 2500 : slides[slide]?.duration || 8000;
      autoRef.current = setTimeout(next, dur);
    }
    return () => clearTimeout(autoRef.current);
  }, [autoPlay, slide, demoStep, next, slides, isDemoSlide]);

  const progress = ((slide + (isDemoSlide ? demoStep / 6 : 0)) / (slides.length - 1)) * 100;

  return (
    <div style={{ width: "100%", height: "100vh", background: C.bg, color: C.text, fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <style>{`
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes slideUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes slideRight { from { opacity: 0; transform: translateX(-20px); } to { opacity: 1; transform: translateX(0); } }
        @keyframes nodeAppear { from { opacity: 0; transform: scale(0.5); } to { opacity: 1; transform: scale(1); } }
        * { box-sizing: border-box; }
      `}</style>

      <div style={{ height: 3, background: C.surfaceHover, flexShrink: 0 }}>
        <div style={{ height: "100%", background: `linear-gradient(90deg, ${C.accent}, ${C.purple})`, width: `${progress}%`, transition: "width 0.4s ease-out" }} />
      </div>

      <div key={`${slide}-${demoStep}`} style={{ flex: 1, padding: "12px 32px", overflow: "hidden" }}>
        {slides[slide]?.component}
      </div>

      <div style={{ padding: "8px 32px", display: "flex", alignItems: "center", gap: 12, borderTop: `1px solid ${C.border}`, flexShrink: 0 }}>
        <button onClick={prev} disabled={slide === 0 && demoStep === 0} style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${C.border}`, background: "transparent", color: C.text, cursor: "pointer", fontSize: 11, opacity: slide === 0 && demoStep === 0 ? 0.3 : 1 }}>← Prev</button>
        <button onClick={next} disabled={slide === slides.length - 1} style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${C.border}`, background: "transparent", color: C.text, cursor: "pointer", fontSize: 11, opacity: slide === slides.length - 1 ? 0.3 : 1 }}>Next →</button>
        <button onClick={() => setAutoPlay(p => !p)} style={{ padding: "5px 12px", borderRadius: 6, border: `1px solid ${autoPlay ? C.accent : C.border}`, background: autoPlay ? `${C.accent}20` : "transparent", color: autoPlay ? C.accent : C.text, cursor: "pointer", fontSize: 11 }}>{autoPlay ? "⏸ Pause" : "▶ Auto"}</button>
        <div style={{ flex: 1, display: "flex", gap: 4, justifyContent: "center" }}>
          {slides.map((s, i) => (
            <button key={i} onClick={() => { setSlide(i); setDemoStep(0); }} style={{
              width: i === slide ? 20 : 7, height: 7, borderRadius: 4, border: "none", cursor: "pointer", transition: "all 0.3s",
              background: i === slide ? C.accent : i < slide ? C.mutedLight : C.surfaceHover
            }} title={s.title} />
          ))}
        </div>
        <span style={{ fontSize: 10, color: C.muted, minWidth: 100, textAlign: "right" }}>
          {slide + 1}/{slides.length} {isDemoSlide ? `(${demoStep + 1}/6)` : ""} · {slides[slide]?.title}
        </span>
      </div>
    </div>
  );
}
