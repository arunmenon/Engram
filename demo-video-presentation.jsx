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

// ─── Scroll Hook: useInView ───
function useInView(options = {}) {
  const { threshold = 0.15, rootMargin = "0px" } = options;
  const ref = useRef(null);
  const [isInView, setIsInView] = useState(false);
  const [ratio, setRatio] = useState(0);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) setIsInView(true);
      setRatio(entry.intersectionRatio);
    }, { threshold: [0, 0.1, 0.15, 0.25, 0.5, 0.75, 1], rootMargin });
    obs.observe(el);
    return () => obs.disconnect();
  }, [threshold, rootMargin]);
  return { ref, isInView, ratio };
}

// ─── Reveal Component ───
function Reveal({ children, delay = 0, direction = "up", style = {} }) {
  const { ref, isInView } = useInView({ threshold: 0.1 });
  const transforms = { up: "translateY(40px)", down: "translateY(-40px)", left: "translateX(40px)", right: "translateX(-40px)", none: "none" };
  return (
    <div ref={ref} style={{
      opacity: isInView ? 1 : 0,
      transform: isInView ? "none" : transforms[direction],
      transition: `opacity 0.7s ease-out ${delay}s, transform 0.7s ease-out ${delay}s`,
      ...style,
    }}>{children}</div>
  );
}

// ─── Section Wrappers ───
function Section({ children, id, minHeight = "100vh", style = {} }) {
  return (
    <section id={id} style={{ minHeight, padding: "80px 60px", position: "relative", display: "flex", flexDirection: "column", justifyContent: "center", ...style }}>
      {children}
    </section>
  );
}

function SectionHeader({ tag, title, subtitle }) {
  return (
    <Reveal>
      {tag && <div style={{ fontSize: 11, color: C.muted, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>{tag}</div>}
      <h2 style={{ fontSize: 40, fontWeight: 700, color: C.text, margin: "0 0 12px", lineHeight: 1.15 }}>{title}</h2>
      {subtitle && <p style={{ fontSize: 18, color: C.mutedLight, maxWidth: 640, lineHeight: 1.5, margin: 0 }}>{subtitle}</p>}
    </Reveal>
  );
}

// ─── Helpers ───
function Counter({ end, duration = 2000, prefix = "", suffix = "", trigger = false }) {
  const [val, setVal] = useState(0);
  const raf = useRef(null);
  useEffect(() => {
    if (!trigger) return;
    let start = 0;
    const step = (ts) => {
      if (!start) start = ts;
      const p = Math.min((ts - start) / duration, 1);
      setVal(Math.floor(p * end));
      if (p < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf.current);
  }, [trigger, end, duration]);
  return <span>{prefix}{val.toLocaleString()}{suffix}</span>;
}

const Pill = ({ color, children }) => (
  <span style={{ padding: "3px 10px", borderRadius: 20, background: `${color}18`, color, fontSize: 10, fontWeight: 600, border: `1px solid ${color}30` }}>{children}</span>
);

const Card = ({ children, style }) => (
  <div style={{ padding: 16, borderRadius: 12, background: C.surface, border: `1px solid ${C.border}`, ...style }}>{children}</div>
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
        return (<g key={i}><line x1={a.x} y1={a.y} x2={b.x} y2={b.y} stroke={C.border} strokeWidth={1.2} /><text x={(a.x + b.x) / 2} y={(a.y + b.y) / 2 - 5} fill={C.muted} fontSize={compact ? 5 : 7} textAnchor="middle">{e.type}</text></g>);
      })}
      {nodes.slice(0, visN).map((n) => {
        const shape = shapeFor(n.type);
        const r = compact ? 10 : 16;
        return (
          <g key={n.id} filter="url(#glow2)">
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
function FEShellMockup({ activeMsg = 0, activeTab = "chat", style }) {
  const tabs = ["chat", "context", "graph"];
  const msgs = [
    { role: "user", text: "What happened with Sarah Chen's billing issue?" },
    { role: "assistant", text: "Let me check the context graph for Sarah Chen..." },
    { role: "context", text: "📊 Found: 3 events, 2 entities, 1 preference across 2 sessions" },
    { role: "assistant", text: "Sarah contacted us twice about a billing discrepancy on her enterprise account. She prefers email communication. Last session resolved with a $240 refund." },
    { role: "user", text: "Has she had other issues?" },
    { role: "assistant", text: "Based on her profile: 2 prior support sessions (both resolved), NPS score improved from 6→8. She's a Tech Lead — patterns suggest she values detailed technical explanations." },
  ];
  const contextPanelData = [
    { label: "Decay Score", value: "0.87", color: C.green },
    { label: "Relevance", value: "0.92", color: C.accent },
    { label: "Importance", value: "7/10", color: C.amber },
    { label: "Sessions", value: "3", color: C.purple },
  ];
  const graphMiniNodes = [
    { x: 50, y: 30, color: C.accent, label: "msg" }, { x: 120, y: 50, color: C.green, label: "Sarah" },
    { x: 90, y: 90, color: C.amber, label: "Billing" }, { x: 160, y: 30, color: C.purple, label: "Summary" },
  ];
  return (
    <div style={{ background: C.bg, borderRadius: 12, border: `1px solid ${C.border}`, overflow: "hidden", fontFamily: "system-ui, sans-serif", ...style }}>
      <div style={{ display: "flex", alignItems: "center", padding: "8px 12px", background: C.surface, borderBottom: `1px solid ${C.border}`, gap: 6 }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: C.red }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: C.amber }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: C.green }} />
        <span style={{ marginLeft: 8, fontSize: 11, color: C.muted }}>Context-Aware Agent Shell</span>
      </div>
      <div style={{ display: "flex", gap: 1, padding: "6px 12px", background: C.surface }}>
        {tabs.map(t => (
          <button key={t} style={{ padding: "4px 14px", borderRadius: 6, border: "none", fontSize: 11, fontWeight: 600, cursor: "pointer", background: activeTab === t ? C.accent : "transparent", color: activeTab === t ? "#fff" : C.muted }}>{t}</button>
        ))}
      </div>
      <div style={{ padding: 12, minHeight: 200 }}>
        {activeTab === "chat" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {msgs.slice(0, activeMsg + 1).map((m, i) => (
              <div key={i} style={{ display: "flex", gap: 8, justifyContent: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{
                  maxWidth: "80%", padding: "8px 12px", borderRadius: 10, fontSize: 11, lineHeight: 1.4,
                  background: m.role === "user" ? C.accent : m.role === "context" ? `${C.purple}20` : C.surface,
                  color: m.role === "user" ? "#fff" : C.text,
                  border: m.role === "context" ? `1px solid ${C.purple}40` : m.role === "assistant" ? `1px solid ${C.border}` : "none",
                }}>{m.text}</div>
              </div>
            ))}
          </div>
        )}
        {activeTab === "context" && (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
            {contextPanelData.map((d, i) => (
              <div key={i} style={{ padding: 10, borderRadius: 8, background: C.surface, border: `1px solid ${C.border}`, textAlign: "center" }}>
                <div style={{ fontSize: 9, color: C.muted, marginBottom: 4 }}>{d.label}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: d.color }}>{d.value}</div>
              </div>
            ))}
          </div>
        )}
        {activeTab === "graph" && (
          <svg viewBox="0 0 200 120" style={{ width: "100%" }}>
            {graphMiniNodes.map((n, i) => (
              <g key={i}>
                <circle cx={n.x} cy={n.y} r={12} fill={n.color} opacity={0.8} />
                <text x={n.x} y={n.y + 22} fill={C.muted} fontSize={7} textAnchor="middle">{n.label}</text>
              </g>
            ))}
            <line x1={50} y1={30} x2={120} y2={50} stroke={C.border} />
            <line x1={120} y1={50} x2={90} y2={90} stroke={C.border} />
            <line x1={120} y1={50} x2={160} y2={30} stroke={C.border} />
          </svg>
        )}
      </div>
    </div>
  );
}

// ─── Decay Curve ───
function DecayCurve({ style }) {
  const data = Array.from({ length: 50 }, (_, i) => {
    const t = i / 49;
    const base = Math.exp(-2.5 * t);
    const rehearsed = Math.exp(-1.2 * t) * 0.95;
    return { t: `${Math.round(t * 72)}h`, base: +(base * 100).toFixed(1), rehearsed: +(rehearsed * 100).toFixed(1) };
  });
  return (
    <ResponsiveContainer width="100%" height="100%" style={style}>
      <LineChart data={data} margin={{ top: 10, right: 10, bottom: 20, left: 10 }}>
        <XAxis dataKey="t" tick={{ fill: C.muted, fontSize: 9 }} tickLine={false} interval={12} />
        <YAxis tick={{ fill: C.muted, fontSize: 9 }} tickLine={false} domain={[0, 100]} />
        <Line type="monotone" dataKey="base" stroke={C.red} strokeWidth={2} dot={false} name="No rehearsal" />
        <Line type="monotone" dataKey="rehearsed" stroke={C.green} strokeWidth={2} dot={false} name="With rehearsal" />
      </LineChart>
    </ResponsiveContainer>
  );
}

// ─── Section Navigation (Floating Dots) ───
const SECTIONS = [
  { id: "hero", label: "Intro" },
  { id: "problem", label: "Problem" },
  { id: "research", label: "Research" },
  { id: "neuroscience", label: "Neuroscience" },
  { id: "gap", label: "Industry Gap" },
  { id: "solution", label: "Solution" },
  { id: "memory-types", label: "Memory Types" },
  { id: "consolidation", label: "Consolidation" },
  { id: "architecture", label: "Architecture" },
  { id: "entity", label: "Entity Resolution" },
  { id: "demo", label: "Live Demo" },
  { id: "personas", label: "Personas" },
  { id: "decay", label: "Memory Decay" },
  { id: "lifecycle", label: "Lifecycle" },
  { id: "readiness", label: "Reliability" },
  { id: "differentiators", label: "Differentiators" },
  { id: "closing", label: "Closing" },
];

function FloatingNav({ activeSection }) {
  return (
    <div style={{ position: "fixed", right: 16, top: "50%", transform: "translateY(-50%)", display: "flex", flexDirection: "column", gap: 6, zIndex: 100 }}>
      {SECTIONS.map(s => {
        const isActive = s.id === activeSection;
        return (
          <div key={s.id} onClick={() => document.getElementById(s.id)?.scrollIntoView({ behavior: "smooth" })}
            style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", justifyContent: "flex-end" }}>
            {isActive && <span style={{ fontSize: 9, color: C.accent, fontWeight: 600, whiteSpace: "nowrap" }}>{s.label}</span>}
            <div style={{
              width: isActive ? 10 : 6, height: isActive ? 10 : 6, borderRadius: "50%",
              background: isActive ? C.accent : C.muted, transition: "all 0.3s",
              boxShadow: isActive ? `0 0 8px ${C.accentGlow}` : "none",
            }} />
          </div>
        );
      })}
    </div>
  );
}

function ProgressBar({ progress }) {
  return (
    <div style={{ position: "fixed", top: 0, left: 0, right: 0, height: 3, background: `${C.surface}80`, zIndex: 200 }}>
      <div style={{ height: "100%", background: `linear-gradient(90deg, ${C.accent}, ${C.purple})`, width: `${progress * 100}%`, transition: "width 0.1s" }} />
    </div>
  );
}

// ────────────────────────────────────────────
// SECTIONS
// ────────────────────────────────────────────

function HeroSection() {
  const { ref, isInView } = useInView();
  return (
    <Section id="hero" style={{ justifyContent: "center", alignItems: "center", textAlign: "center", minHeight: "100vh" }}>
      <div ref={ref} style={{ opacity: isInView ? 1 : 0, transition: "opacity 1.2s ease-out" }}>
        <div style={{ fontSize: 11, color: C.muted, fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 16 }}>Introducing</div>
        <h1 style={{ fontSize: 64, fontWeight: 800, color: C.text, margin: "0 0 12px", lineHeight: 1.05,
          background: `linear-gradient(135deg, ${C.text}, ${C.accent})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Context Graph
        </h1>
        <p style={{ fontSize: 22, color: C.mutedLight, maxWidth: 520, margin: "0 auto 32px", lineHeight: 1.4 }}>
          Traceability-first memory infrastructure for AI agents
        </p>
        <Reveal delay={0.4}>
          <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
            {[{ label: "8 Node Types", color: C.accent }, { label: "16 Edge Types", color: C.green }, { label: "4 Consumers", color: C.purple }, { label: "Sub-200ms P95", color: C.amber }].map((b, i) => (
              <div key={i} style={{ padding: "10px 20px", borderRadius: 8, background: `${b.color}12`, border: `1px solid ${b.color}30`, color: b.color, fontSize: 13, fontWeight: 600 }}>{b.label}</div>
            ))}
          </div>
        </Reveal>
        <Reveal delay={0.7}>
          <div style={{ marginTop: 48, fontSize: 13, color: C.muted }}>Scroll to explore</div>
          <div style={{ marginTop: 8, fontSize: 20, color: C.muted, animation: "pulse 2s infinite" }}>↓</div>
        </Reveal>
      </div>
    </Section>
  );
}

function ProblemSection() {
  const problems = [
    { icon: "🔄", title: "Stateless Loops", desc: "Agents repeat the same questions every session. Users lose trust." },
    { icon: "🧠", title: "Context Window Limits", desc: "128K tokens sounds large — until your agent manages a 6-month project." },
    { icon: "🔍", title: "No Provenance", desc: "RAG retrieves text but can't tell you when, why, or how it was captured." },
  ];
  return (
    <Section id="problem" minHeight="80vh">
      <SectionHeader tag="The Problem" title="AI Agents Have Amnesia" subtitle="Every agent framework treats memory as an afterthought. The result is agents that forget, repeat, and lose user trust." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, marginTop: 40 }}>
        {problems.map((p, i) => (
          <Reveal key={i} delay={i * 0.15}>
            <Card>
              <div style={{ fontSize: 28, marginBottom: 10 }}>{p.icon}</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: C.text, marginBottom: 6 }}>{p.title}</div>
              <div style={{ fontSize: 12, color: C.mutedLight, lineHeight: 1.5 }}>{p.desc}</div>
            </Card>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function ResearchSection() {
  const clusters = [
    { area: "Cognitive Architecture", refs: ["Tulving (1972) — Episodic vs Semantic", "Baddeley (2000) — Working Memory", "Anderson (1983) — ACT-R Framework"], color: C.accent },
    { area: "Memory Consolidation", refs: ["Ebbinghaus (1885) — Forgetting Curve", "Bartlett (1932) — Schema Theory", "McClelland (1995) — Complementary Learning"], color: C.green },
    { area: "Knowledge Graphs", refs: ["Singhal (2012) — Google Knowledge Graph", "Ji (2021) — KG Survey", "Pan (2024) — Unifying LLMs & KGs"], color: C.purple },
    { area: "Agent Memory Systems", refs: ["Park (2023) — Generative Agents", "Packer (2023) — MemGPT", "Zhong (2024) — MemoryBank"], color: C.amber },
  ];
  return (
    <Section id="research" minHeight="100vh">
      <SectionHeader tag="Research Foundations" title="Standing on Solid Ground" subtitle="Context Graph synthesizes four decades of research across cognitive science, neuroscience, knowledge representation, and agent architecture." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginTop: 40 }}>
        {clusters.map((c, i) => (
          <Reveal key={i} delay={i * 0.12} direction="up">
            <Card style={{ borderTop: `3px solid ${c.color}` }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: c.color, marginBottom: 10 }}>{c.area}</div>
              {c.refs.map((r, j) => (
                <div key={j} style={{ fontSize: 10, color: C.mutedLight, marginBottom: 4, paddingLeft: 8, borderLeft: `2px solid ${c.color}30` }}>{r}</div>
              ))}
            </Card>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function NeuroscienceSection() {
  const mappings = [
    { brain: "Hippocampus", graph: "Event Nodes + FOLLOWS edges", fn: "Episodic sequence encoding" },
    { brain: "Prefrontal Cortex", graph: "Intent Classification + Scoring", fn: "Working memory & relevance gating" },
    { brain: "Temporal Cortex", graph: "Entity Nodes + REFERENCES", fn: "Semantic knowledge storage" },
    { brain: "Basal Ganglia", graph: "4 Consumer Workers", fn: "Procedural pattern extraction" },
    { brain: "Amygdala", graph: "Importance Hints (1-10)", fn: "Emotional salience weighting" },
    { brain: "Cerebellum", graph: "Workflow + BehavioralPattern", fn: "Learned action sequences" },
  ];
  return (
    <Section id="neuroscience" minHeight="100vh">
      <SectionHeader tag="Neuroscience Mapping" title="Modeled After Human Memory" subtitle="Each component in Context Graph maps directly to a neuroscience principle — not by accident, but by design." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginTop: 32 }}>
        {mappings.map((m, i) => (
          <Reveal key={i} delay={i * 0.08}>
            <Card style={{ padding: 12 }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 11, fontWeight: 700, color: C.pink }}>{m.brain}</span>
                <span style={{ fontSize: 9, color: C.muted }}>→</span>
                <span style={{ fontSize: 11, fontWeight: 700, color: C.accent }}>{m.graph}</span>
              </div>
              <div style={{ fontSize: 10, color: C.mutedLight }}>{m.fn}</div>
            </Card>
          </Reveal>
        ))}
      </div>
      <Reveal delay={0.6}>
        <Card style={{ marginTop: 24, padding: 16, borderLeft: `3px solid ${C.amber}`, maxWidth: 500 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.amber, marginBottom: 4 }}>Ebbinghaus Decay Formula</div>
          <div style={{ fontSize: 14, fontFamily: "monospace", color: C.text }}>S(t) = e^(-t/τ) × importance × rehearsal_count</div>
          <div style={{ fontSize: 10, color: C.mutedLight, marginTop: 4 }}>τ = strength parameter, calibrated per-node from access patterns</div>
        </Card>
      </Reveal>
    </Section>
  );
}

function GapSection() {
  const rows = [
    { cap: "Provenance", cg: "Full trace to source event", rag: "None", memgpt: "Partial" },
    { cap: "Multi-session", cg: "Native (UserProfile)", rag: "No", memgpt: "Limited" },
    { cap: "Forgetting", cg: "Ebbinghaus decay", rag: "No", memgpt: "FIFO only" },
    { cap: "Entity Resolution", cg: "3-tier (exact→semantic→LLM)", rag: "No", memgpt: "No" },
    { cap: "Graph Queries", cg: "Intent-weighted traversal", rag: "Vector only", memgpt: "No" },
  ];
  return (
    <Section id="gap" minHeight="90vh">
      <SectionHeader tag="Industry Gap" title="What Exists Today Falls Short" subtitle="RAG gives you retrieval. MemGPT gives you tiers. Neither provides the traceability, structure, or intelligence that production agents require." />
      <Reveal delay={0.2}>
        <div style={{ marginTop: 32, borderRadius: 12, overflow: "hidden", border: `1px solid ${C.border}` }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: C.surface }}>
                {["Capability", "Context Graph", "RAG", "MemGPT"].map(h => (
                  <th key={h} style={{ padding: "10px 14px", textAlign: "left", color: h === "Context Graph" ? C.accent : C.muted, fontWeight: 700, borderBottom: `1px solid ${C.border}` }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i} style={{ background: i % 2 ? C.surface : "transparent" }}>
                  <td style={{ padding: "8px 14px", color: C.text, fontWeight: 600 }}>{r.cap}</td>
                  <td style={{ padding: "8px 14px", color: C.green }}>{r.cg}</td>
                  <td style={{ padding: "8px 14px", color: C.mutedLight }}>{r.rag}</td>
                  <td style={{ padding: "8px 14px", color: C.mutedLight }}>{r.memgpt}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Reveal>
      <Reveal delay={0.4}>
        <div style={{ display: "flex", gap: 12, marginTop: 24 }}>
          {["ISO 42001 Aligned", "GDPR Article 17 Ready", "SOC 2 Audit Trail"].map((s, i) => (
            <div key={i} style={{ padding: "6px 14px", borderRadius: 6, background: `${C.green}12`, border: `1px solid ${C.green}30`, color: C.green, fontSize: 10, fontWeight: 600 }}>{s}</div>
          ))}
        </div>
      </Reveal>
    </Section>
  );
}

function SolutionSection() {
  const steps = [
    { num: "01", title: "Capture", desc: "Immutable event ingestion via Redis Streams. Every action gets a global position, trace ID, and provenance chain.", color: C.accent },
    { num: "02", title: "Project", desc: "4 async consumers transform events into an 8-node, 16-edge knowledge graph in Neo4j.", color: C.green },
    { num: "03", title: "Score", desc: "Ebbinghaus decay, importance weighting, and rehearsal tracking determine what stays relevant.", color: C.amber },
    { num: "04", title: "Retrieve", desc: "Intent-weighted traversal returns provenance-annotated context — not just text, but full lineage.", color: C.purple },
  ];
  return (
    <Section id="solution" minHeight="80vh">
      <SectionHeader tag="The Solution" title="Context Graph" subtitle="A traceability-first memory infrastructure that captures, structures, scores, and retrieves agent context with full provenance." />
      <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 16 }}>
        {steps.map((s, i) => (
          <Reveal key={i} delay={i * 0.15} direction="right">
            <div style={{ display: "flex", gap: 20, alignItems: "center", padding: 20, borderRadius: 12, background: C.surface, border: `1px solid ${C.border}` }}>
              <div style={{ fontSize: 32, fontWeight: 800, color: s.color, fontFamily: "monospace", minWidth: 50 }}>{s.num}</div>
              <div>
                <div style={{ fontSize: 16, fontWeight: 700, color: s.color, marginBottom: 4 }}>{s.title}</div>
                <div style={{ fontSize: 12, color: C.mutedLight, lineHeight: 1.5 }}>{s.desc}</div>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function MemoryTypesSection() {
  const types = [
    { type: "Episodic", desc: "Raw event sequences — what happened, in order", nodes: "Event + FOLLOWS edges", color: C.accent, icon: "📝" },
    { type: "Semantic", desc: "Extracted entities and relationships — structured knowledge", nodes: "Entity + REFERENCES + RELATED_TO", color: C.green, icon: "🧩" },
    { type: "Procedural", desc: "Detected workflows and action patterns", nodes: "Workflow + BehavioralPattern", color: C.amber, icon: "⚙️" },
    { type: "Autobiographical", desc: "User profiles, preferences, skills — persistent identity", nodes: "UserProfile + Preference + Skill", color: C.pink, icon: "👤" },
    { type: "Working", desc: "Active session context with decay scoring and relevance gating", nodes: "Session scope + intent classification", color: C.purple, icon: "💭" },
  ];
  return (
    <Section id="memory-types" minHeight="100vh">
      <SectionHeader tag="Memory Architecture" title="Five Types of Memory" subtitle="Modeled after human cognitive architecture — each memory type maps to specific node types, edge types, and retrieval strategies." />
      <div style={{ marginTop: 32, display: "flex", flexDirection: "column", gap: 12 }}>
        {types.map((t, i) => (
          <Reveal key={i} delay={i * 0.1}>
            <div style={{ display: "flex", gap: 16, alignItems: "center", padding: 16, borderRadius: 12, background: C.surface, border: `1px solid ${C.border}`, borderLeft: `4px solid ${t.color}` }}>
              <div style={{ fontSize: 28, minWidth: 40, textAlign: "center" }}>{t.icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
                  <span style={{ fontSize: 15, fontWeight: 700, color: t.color }}>{t.type}</span>
                  <span style={{ fontSize: 9, color: C.muted, fontFamily: "monospace" }}>{t.nodes}</span>
                </div>
                <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.5 }}>{t.desc}</div>
              </div>
            </div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function PipelineDiagram() {
  // Conceptual SVG flow diagram: Events → Structure → Understand → Enrich → Maintain
  const stages = [
    { x: 60, label: "Events", sub: "Capture", color: C.accent, icon: "●" },
    { x: 200, label: "Structure", sub: "Project into graph", color: C.green, icon: "◆" },
    { x: 340, label: "Understand", sub: "Extract meaning", color: C.purple, icon: "▲" },
    { x: 480, label: "Enrich", sub: "Connect & score", color: C.amber, icon: "■" },
    { x: 620, label: "Maintain", sub: "Consolidate & archive", color: C.pink, icon: "♻" },
  ];
  return (
    <svg viewBox="0 0 700 160" style={{ width: "100%" }}>
      {/* Flow arrows */}
      {stages.slice(0, -1).map((s, i) => (
        <g key={`arrow-${i}`}>
          <line x1={s.x + 40} y1={60} x2={stages[i + 1].x - 40} y2={60} stroke={C.border} strokeWidth={2} />
          <polygon points={`${stages[i + 1].x - 42},55 ${stages[i + 1].x - 32},60 ${stages[i + 1].x - 42},65`} fill={C.border} />
        </g>
      ))}
      {/* Stage nodes */}
      {stages.map((s, i) => (
        <g key={i}>
          <circle cx={s.x} cy={60} r={28} fill={`${s.color}15`} stroke={s.color} strokeWidth={2} />
          <text x={s.x} y={64} fill={s.color} fontSize={16} textAnchor="middle" fontWeight={700}>{s.icon}</text>
          <text x={s.x} y={108} fill={C.text} fontSize={12} textAnchor="middle" fontWeight={700}>{s.label}</text>
          <text x={s.x} y={124} fill={C.muted} fontSize={9} textAnchor="middle">{s.sub}</text>
        </g>
      ))}
      {/* Feedback loop */}
      <path d={`M 620,88 Q 620,145 340,145 Q 60,145 60,88`} fill="none" stroke={`${C.muted}40`} strokeWidth={1.5} strokeDasharray="6,4" />
      <text x={340} y={152} fill={C.muted} fontSize={8} textAnchor="middle">feedback loop — consolidation strengthens earlier stages</text>
    </svg>
  );
}

function ConsolidationSection() {
  const stages = [
    { title: "Structure", desc: "Raw events are projected into a typed knowledge graph — nodes for events, entities, and summaries connected by meaningful edges.", color: C.accent, when: "As events arrive" },
    { title: "Understand", desc: "Completed sessions are analyzed to extract entities, preferences, skills, and behavioral patterns. The system learns *who* was involved and *what* mattered.", color: C.green, when: "After each session" },
    { title: "Enrich", desc: "Semantic embeddings connect related concepts. Similar events are linked. Entity references are resolved across sessions.", color: C.purple, when: "In batches" },
    { title: "Maintain", desc: "Over time, the system consolidates — summarizing old events, detecting long-term patterns, archiving stale data, and keeping the graph lean.", color: C.amber, when: "Periodically" },
  ];
  return (
    <Section id="consolidation" minHeight="100vh">
      <SectionHeader tag="Processing Pipeline" title="From Raw Events to Living Knowledge" subtitle="Events don't just get stored — they flow through a multi-stage pipeline that structures, understands, enriches, and maintains the knowledge graph over time." />
      <Reveal delay={0.1}>
        <div style={{ marginTop: 32, background: C.surface, borderRadius: 12, border: `1px solid ${C.border}`, padding: 24 }}>
          <PipelineDiagram />
        </div>
      </Reveal>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, marginTop: 24 }}>
        {stages.map((s, i) => (
          <Reveal key={i} delay={0.3 + i * 0.12}>
            <Card style={{ borderTop: `3px solid ${s.color}`, height: "100%" }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: s.color, marginBottom: 4 }}>{s.title}</div>
              <div style={{ fontSize: 9, color: C.muted, marginBottom: 8, fontStyle: "italic" }}>{s.when}</div>
              <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.5 }}>{s.desc}</div>
            </Card>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function ArchitectureSection() {
  const { ref, isInView } = useInView({ threshold: 0.2 });
  return (
    <Section id="architecture" minHeight="100vh">
      <SectionHeader tag="Graph Schema" title="8 Node Types, 16 Edge Types" subtitle="A typed, scored knowledge graph with provenance at every node. Not a generic store — purpose-built for agent memory." />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24, marginTop: 36 }}>
        <Reveal delay={0.1}>
          <div ref={ref} style={{ height: 360, background: C.surface, borderRadius: 12, border: `1px solid ${C.border}`, padding: 12, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <AnimatedGraph phase={isInView ? 1 : 0} />
          </div>
        </Reveal>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, alignContent: "start" }}>
          {[
            { title: "Event Sourced", desc: "An immutable event ledger is the source of truth. Every node in the graph is traceable back to the events that created it.", color: C.accent },
            { title: "Intent-Weighted", desc: "The system infers what you're asking — 'why' questions prioritize causal links, 'who' questions prioritize entity relationships.", color: C.green },
            { title: "Decay-Scored", desc: "Every node carries a relevance score that fades over time. Important, frequently accessed knowledge persists; stale data fades.", color: C.amber },
            { title: "Multi-View", desc: "The same graph supports temporal, causal, semantic, and entity perspectives — different questions, different traversal strategies.", color: C.purple },
          ].map((p, i) => (
            <Reveal key={i} delay={0.2 + i * 0.1}>
              <Card style={{ borderLeft: `3px solid ${p.color}` }}>
                <div style={{ fontSize: 12, fontWeight: 700, color: p.color, marginBottom: 4 }}>{p.title}</div>
                <div style={{ fontSize: 10, color: C.mutedLight, lineHeight: 1.4 }}>{p.desc}</div>
              </Card>
            </Reveal>
          ))}
        </div>
      </div>
    </Section>
  );
}

function EntityResolutionSection() {
  const tiers = [
    { tier: "Tier 1", name: "Deterministic", desc: "Exact name matching and normalized aliases. 'Sarah Chen' and 'sarah.chen@corp.com' resolve instantly to the same entity.", color: C.green, speed: "Instant" },
    { tier: "Tier 2", name: "Semantic", desc: "Embedding-based similarity finds conceptually related entities even when names differ. 'Billing Department' and 'Finance Team' are recognized as related.", color: C.amber, speed: "Fast" },
    { tier: "Tier 3", name: "LLM Arbitration", desc: "For truly ambiguous cases, a language model resolves coreferences and contextual identity. Only triggered when simpler methods can't decide.", color: C.purple, speed: "Deliberate" },
  ];
  return (
    <Section id="entity" minHeight="90vh">
      <SectionHeader tag="Entity Resolution" title="Three-Tier Cascade" subtitle="From sub-millisecond deterministic matching to LLM-powered arbitration — each tier fires only when the previous one can't resolve." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, marginTop: 36 }}>
        {tiers.map((t, i) => (
          <Reveal key={i} delay={i * 0.15} direction="left">
            <Card style={{ borderTop: `3px solid ${t.color}`, height: "100%" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                <Pill color={t.color}>{t.tier}</Pill>
                <span style={{ fontSize: 10, color: C.muted, fontFamily: "monospace" }}>{t.speed}</span>
              </div>
              <div style={{ fontSize: 15, fontWeight: 700, color: C.text, marginBottom: 6 }}>{t.name}</div>
              <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.5 }}>{t.desc}</div>
            </Card>
          </Reveal>
        ))}
      </div>
      <Reveal delay={0.5}>
        <div style={{ marginTop: 24, padding: 12, borderRadius: 8, background: `${C.green}08`, border: `1px solid ${C.green}20`, maxWidth: 500 }}>
          <div style={{ fontSize: 10, color: C.green }}>Cascade principle: 95% of resolutions complete at Tier 1. Only 3% reach Tier 3. Cost-efficient by design.</div>
        </div>
      </Reveal>
    </Section>
  );
}

// ─── FE Shell Demo: Sticky Scroll-Linked ───
function DemoSection() {
  const containerRef = useRef(null);
  const [demoStep, setDemoStep] = useState(0);
  const [activeTab, setActiveTab] = useState("chat");

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    const onScroll = () => {
      const rect = container.getBoundingClientRect();
      const sectionHeight = container.offsetHeight;
      const viewportH = window.innerHeight;
      // How far we've scrolled into the sticky zone
      const scrolled = -rect.top;
      const scrollRange = sectionHeight - viewportH;
      if (scrollRange <= 0) return;
      const progress = Math.max(0, Math.min(1, scrolled / scrollRange));
      const totalSteps = 8; // 6 chat msgs + context tab + graph tab
      const step = Math.floor(progress * totalSteps);
      if (step <= 5) {
        setDemoStep(Math.min(step, 5));
        setActiveTab("chat");
      } else if (step === 6) {
        setActiveTab("context");
      } else {
        setActiveTab("graph");
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const stepLabels = [
    "User asks about Sarah Chen's billing issue",
    "Agent queries the context graph",
    "Context graph returns scored results",
    "Agent responds with full history and resolution",
    "User asks a follow-up question",
    "Agent draws on cross-session profile data",
    "Context panel shows decay scores and metadata",
    "Graph view reveals the entity relationship network",
  ];

  return (
    <section id="demo" ref={containerRef} style={{ minHeight: "250vh", position: "relative" }}>
      <div style={{ position: "sticky", top: 0, height: "100vh", display: "flex", alignItems: "center", padding: "0 60px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 40, width: "100%", alignItems: "center" }}>
          <div>
            <div style={{ fontSize: 11, color: C.muted, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1.5, marginBottom: 8 }}>Live Demonstration</div>
            <h2 style={{ fontSize: 36, fontWeight: 700, color: C.text, margin: "0 0 16px" }}>The Agent Experience</h2>
            <p style={{ fontSize: 14, color: C.mutedLight, lineHeight: 1.5, marginBottom: 24 }}>
              Watch how a context-aware agent uses the graph to provide personalized, historically-grounded responses.
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              {stepLabels.map((label, i) => {
                const currentStep = activeTab === "chat" ? demoStep : activeTab === "context" ? 6 : 7;
                const isActive = i === currentStep;
                const isDone = i < currentStep;
                return (
                  <div key={i} style={{ display: "flex", gap: 10, alignItems: "center", opacity: isDone ? 0.4 : isActive ? 1 : 0.2, transition: "opacity 0.3s" }}>
                    <div style={{
                      width: 20, height: 20, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 9, fontWeight: 700,
                      background: isActive ? C.accent : isDone ? C.green : C.surface, color: "#fff", border: `1px solid ${isActive ? C.accent : isDone ? C.green : C.border}`,
                    }}>{isDone ? "✓" : i + 1}</div>
                    <span style={{ fontSize: 11, color: isActive ? C.text : C.muted }}>{label}</span>
                  </div>
                );
              })}
            </div>
          </div>
          <FEShellMockup activeMsg={demoStep} activeTab={activeTab} style={{ maxWidth: 420 }} />
        </div>
      </div>
    </section>
  );
}

function PersonasSection() {
  const personas = [
    { name: "Enterprise Support Agent", desc: "Multi-session customer history, preference-aware routing, entity-linked case management.", icon: "🎧", color: C.accent },
    { name: "Developer Copilot", desc: "Cross-repo context, skill-aware suggestions, workflow detection across coding sessions.", icon: "💻", color: C.green },
    { name: "Research Assistant", desc: "Paper entity graphs, citation lineage, temporal knowledge evolution across research threads.", icon: "🔬", color: C.purple },
  ];
  return (
    <Section id="personas" minHeight="80vh">
      <SectionHeader tag="Use Cases" title="Built for Real Agents" subtitle="Context Graph serves any agent that needs to remember, relate, and reason across sessions." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, marginTop: 36 }}>
        {personas.map((p, i) => (
          <Reveal key={i} delay={i * 0.15}>
            <Card style={{ padding: 24, textAlign: "center" }}>
              <div style={{ fontSize: 40, marginBottom: 12 }}>{p.icon}</div>
              <div style={{ fontSize: 15, fontWeight: 700, color: p.color, marginBottom: 8 }}>{p.name}</div>
              <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.5 }}>{p.desc}</div>
            </Card>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function DecaySection() {
  const { ref, isInView } = useInView();
  return (
    <Section id="decay" minHeight="100vh">
      <SectionHeader tag="Memory Lifecycle" title="Ebbinghaus Decay & Forgetting" subtitle="Memories don't live forever. Context Graph implements a principled forgetting system based on Ebbinghaus's spacing-effect research." />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32, marginTop: 32 }}>
        <Reveal>
          <div ref={ref} style={{ height: 280, background: C.surface, borderRadius: 12, border: `1px solid ${C.border}`, padding: 16 }}>
            {isInView && <DecayCurve />}
          </div>
          <div style={{ display: "flex", gap: 16, marginTop: 12, justifyContent: "center" }}>
            <span style={{ fontSize: 10, color: C.red }}>● Without rehearsal</span>
            <span style={{ fontSize: 10, color: C.green }}>● With rehearsal (access = rehearsal)</span>
          </div>
        </Reveal>
        <div>
          <Reveal delay={0.15}>
            <Card style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.text, marginBottom: 8 }}>Scoring Factors</div>
              {[
                { f: "Recency", d: "Exponential decay from last access", c: C.accent },
                { f: "Importance", d: "Event-level hint (1-10), propagated to entities", c: C.amber },
                { f: "Relevance", d: "Cosine similarity to current query context", c: C.green },
                { f: "Rehearsal", d: "Access count strengthens τ parameter", c: C.purple },
              ].map((s, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                  <div style={{ width: 8, height: 8, borderRadius: "50%", background: s.c }} />
                  <span style={{ fontSize: 11, fontWeight: 600, color: s.c, minWidth: 80 }}>{s.f}</span>
                  <span style={{ fontSize: 10, color: C.mutedLight }}>{s.d}</span>
                </div>
              ))}
            </Card>
          </Reveal>
          <Reveal delay={0.3}>
            <Card>
              <div style={{ fontSize: 12, fontWeight: 700, color: C.text, marginBottom: 8 }}>Retention Tiers</div>
              {[
                { tier: "HOT", rule: "score > 0.7 → Redis JSON + Neo4j", color: C.green },
                { tier: "WARM", rule: "0.3 < score < 0.7 → Redis JSON only", color: C.amber },
                { tier: "COLD", rule: "0.1 < score < 0.3 → Compressed events", color: C.orange },
                { tier: "ARCHIVE", rule: "score < 0.1 → Exported to GCS → deleted from Redis", color: C.red },
              ].map((t, i) => (
                <div key={i} style={{ display: "flex", gap: 8, marginBottom: 6, alignItems: "center" }}>
                  <Pill color={t.color}>{t.tier}</Pill>
                  <span style={{ fontSize: 10, color: C.mutedLight }}>{t.rule}</span>
                </div>
              ))}
            </Card>
          </Reveal>
        </div>
      </div>
    </Section>
  );
}

function LifecycleSection() {
  const { ref, isInView } = useInView();
  const stages = [
    { day: "Day 0", title: "Deploy", desc: "Docker Compose up. Redis + Neo4j + 4 consumers + API.", color: C.accent, icon: "🚀" },
    { day: "Day 1", title: "Ingest", desc: "Events flow in. Consumer 1 projects structure. Graph grows.", color: C.green, icon: "📥" },
    { day: "Day 7", title: "Enrich", desc: "Embeddings computed. Semantic links form. Entity resolution cascades.", color: C.purple, icon: "🧬" },
    { day: "Day 30", title: "Consolidate", desc: "Summaries generated. Patterns detected. Cold tier compression begins.", color: C.amber, icon: "📦" },
    { day: "Day 90+", title: "Self-Maintain", desc: "Archive pipeline exports to GCS. Orphan cleanup. Graph stays performant.", color: C.pink, icon: "♻️" },
  ];
  return (
    <Section id="lifecycle" minHeight="100vh">
      <SectionHeader tag="Production Lifecycle" title="From Deploy to Self-Maintaining" subtitle="Context Graph evolves alongside your agent — growing smarter, staying lean, and maintaining itself over time." />
      <div ref={ref} style={{ display: "flex", gap: 0, marginTop: 40, position: "relative" }}>
        {/* Timeline connector */}
        <div style={{ position: "absolute", top: 24, left: 40, right: 40, height: 2, background: `linear-gradient(90deg, ${C.accent}, ${C.pink})`, opacity: 0.3 }} />
        {stages.map((s, i) => (
          <Reveal key={i} delay={i * 0.12} style={{ flex: 1, textAlign: "center", position: "relative" }}>
            <div style={{
              width: 48, height: 48, borderRadius: "50%", background: `${s.color}15`, border: `2px solid ${s.color}`,
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 22, margin: "0 auto 12px",
            }}>{s.icon}</div>
            <div style={{ fontSize: 10, color: s.color, fontWeight: 700, marginBottom: 2 }}>{s.day}</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: C.text, marginBottom: 4 }}>{s.title}</div>
            <div style={{ fontSize: 10, color: C.mutedLight, lineHeight: 1.4, padding: "0 8px" }}>{s.desc}</div>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function ReadinessSection() {
  return (
    <Section id="readiness" minHeight="90vh">
      <SectionHeader tag="Built for Production" title="Designed to Run Unattended" subtitle="Context Graph is built to operate reliably over months and years — self-healing, self-cleaning, and observable by default." />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 20, marginTop: 36 }}>
        <Reveal delay={0.1}>
          <Card style={{ borderTop: `3px solid ${C.accent}`, height: "100%", padding: 20 }}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>🔒</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.accent, marginBottom: 6 }}>Security by Default</div>
            <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.6 }}>
              Authentication is built into the API layer. Every request is validated. Ingestion is idempotent — duplicate events are detected and rejected. Permission boundaries are enforced at every level.
            </div>
          </Card>
        </Reveal>
        <Reveal delay={0.2}>
          <Card style={{ borderTop: `3px solid ${C.green}`, height: "100%", padding: 20 }}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>🔄</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.green, marginBottom: 6 }}>Self-Maintaining</div>
            <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.6 }}>
              Stale data is archived automatically. Orphaned graph nodes are cleaned up. The system consolidates and compresses over time — it stays lean without manual intervention.
            </div>
          </Card>
        </Reveal>
        <Reveal delay={0.3}>
          <Card style={{ borderTop: `3px solid ${C.purple}`, height: "100%", padding: 20 }}>
            <div style={{ fontSize: 28, marginBottom: 10 }}>📊</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.purple, marginBottom: 6 }}>Observable</div>
            <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.6 }}>
              Every pipeline stage emits metrics. Health checks monitor each worker independently. Structured logging means you can trace any issue back to the event that caused it.
            </div>
          </Card>
        </Reveal>
      </div>
      <Reveal delay={0.5}>
        <div style={{ marginTop: 24, padding: 16, borderRadius: 10, background: `${C.amber}08`, border: `1px solid ${C.amber}20`, maxWidth: 600 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: C.amber, marginBottom: 4 }}>Engineering Discipline</div>
          <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.5 }}>
            Systematically reviewed across 8 architectural dimensions. Comprehensive test suite. Every critical finding identified and resolved before production deployment.
          </div>
        </div>
      </Reveal>
    </Section>
  );
}

function DifferentiatorsSection() {
  const diffs = [
    { title: "Traceability-First", desc: "Every piece of context has provenance back to source events. Not an afterthought — the core design principle.", color: C.accent },
    { title: "Neuroscience-Grounded", desc: "5 memory types mapped from cognitive science. Ebbinghaus decay. Hippocampal-inspired consolidation.", color: C.pink },
    { title: "Framework-Agnostic", desc: "REST API. Any agent, any language, any framework. No SDK lock-in.", color: C.green },
    { title: "Self-Maintaining", desc: "The system consolidates, archives, and cleans itself over time. No manual intervention required to keep it performant.", color: C.amber },
    { title: "Production Hardened", desc: "Authenticated, tested, and architecturally reviewed. Built with the rigor expected of production infrastructure.", color: C.red },
    { title: "Research-Backed", desc: "40+ papers synthesized. Cognitive architecture, memory consolidation, knowledge graphs, agent memory.", color: C.purple },
  ];
  return (
    <Section id="differentiators" minHeight="80vh">
      <SectionHeader tag="Why Context Graph" title="Six Differentiators" />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, marginTop: 32 }}>
        {diffs.map((d, i) => (
          <Reveal key={i} delay={i * 0.1}>
            <Card style={{ borderLeft: `3px solid ${d.color}`, height: "100%" }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: d.color, marginBottom: 6 }}>{d.title}</div>
              <div style={{ fontSize: 11, color: C.mutedLight, lineHeight: 1.5 }}>{d.desc}</div>
            </Card>
          </Reveal>
        ))}
      </div>
    </Section>
  );
}

function ClosingSection() {
  return (
    <Section id="closing" minHeight="80vh" style={{ justifyContent: "center", alignItems: "center", textAlign: "center" }}>
      <Reveal>
        <div style={{ fontSize: 11, color: C.muted, fontWeight: 700, textTransform: "uppercase", letterSpacing: 2, marginBottom: 16 }}>Context Graph</div>
        <h2 style={{ fontSize: 48, fontWeight: 800, color: C.text, margin: "0 0 16px",
          background: `linear-gradient(135deg, ${C.accent}, ${C.purple})`, WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
          Memory That Remembers Why
        </h2>
        <p style={{ fontSize: 18, color: C.mutedLight, maxWidth: 500, margin: "0 auto 32px", lineHeight: 1.5 }}>
          Traceability-first memory infrastructure for the next generation of AI agents.
        </p>
      </Reveal>
      <Reveal delay={0.3}>
        <div style={{ display: "flex", gap: 16, justifyContent: "center", flexWrap: "wrap" }}>
          {[
            { label: "Traceable", color: C.accent },
            { label: "Immutable", color: C.green },
            { label: "Self-Maintaining", color: C.amber },
            { label: "Production Ready", color: C.purple },
          ].map((b, i) => (
            <div key={i} style={{ padding: "8px 16px", borderRadius: 8, background: `${b.color}12`, border: `1px solid ${b.color}30`, color: b.color, fontSize: 12, fontWeight: 600 }}>{b.label}</div>
          ))}
        </div>
      </Reveal>
      <Reveal delay={0.6}>
        <div style={{ marginTop: 40, padding: "12px 24px", borderRadius: 8, background: `${C.accent}12`, border: `1px solid ${C.accent}30` }}>
          <span style={{ color: C.accent, fontSize: 13, fontWeight: 600 }}>Research-grounded · Neuroscience-inspired · Framework-agnostic · ISO 42001 aligned</span>
        </div>
      </Reveal>
    </Section>
  );
}

// ────────────────────────────────────────────
// MAIN APP
// ────────────────────────────────────────────

export default function ContextGraphScrollytelling() {
  const [activeSection, setActiveSection] = useState("hero");
  const [scrollProgress, setScrollProgress] = useState(0);
  const containerRef = useRef(null);

  useEffect(() => {
    const onScroll = () => {
      const scrollTop = window.scrollY || document.documentElement.scrollTop;
      const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
      setScrollProgress(scrollHeight > 0 ? scrollTop / scrollHeight : 0);

      // Find active section
      for (let i = SECTIONS.length - 1; i >= 0; i--) {
        const el = document.getElementById(SECTIONS[i].id);
        if (el) {
          const rect = el.getBoundingClientRect();
          if (rect.top <= window.innerHeight * 0.4) {
            setActiveSection(SECTIONS[i].id);
            break;
          }
        }
      }
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div ref={containerRef} style={{
      background: C.bg, color: C.text, fontFamily: "'Inter', system-ui, -apple-system, sans-serif",
      minHeight: "100vh", position: "relative",
    }}>
      <style>{`
        @keyframes pulse { 0%, 100% { opacity: 0.4; } 50% { opacity: 1; } }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        html { scroll-behavior: smooth; }
        body { background: ${C.bg}; }
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: ${C.bg}; }
        ::-webkit-scrollbar-thumb { background: ${C.muted}40; border-radius: 3px; }
      `}</style>
      <ProgressBar progress={scrollProgress} />
      <FloatingNav activeSection={activeSection} />
      <HeroSection />
      {/* Gradient divider */}
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.accent}30, transparent)`, margin: "0 60px" }} />
      <ProblemSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.green}30, transparent)`, margin: "0 60px" }} />
      <ResearchSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.purple}30, transparent)`, margin: "0 60px" }} />
      <NeuroscienceSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.pink}30, transparent)`, margin: "0 60px" }} />
      <GapSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.amber}30, transparent)`, margin: "0 60px" }} />
      <SolutionSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.accent}30, transparent)`, margin: "0 60px" }} />
      <MemoryTypesSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.green}30, transparent)`, margin: "0 60px" }} />
      <ConsolidationSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.purple}30, transparent)`, margin: "0 60px" }} />
      <ArchitectureSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.amber}30, transparent)`, margin: "0 60px" }} />
      <EntityResolutionSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.accent}30, transparent)`, margin: "0 60px" }} />
      <DemoSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.green}30, transparent)`, margin: "0 60px" }} />
      <PersonasSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.pink}30, transparent)`, margin: "0 60px" }} />
      <DecaySection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.amber}30, transparent)`, margin: "0 60px" }} />
      <LifecycleSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.accent}30, transparent)`, margin: "0 60px" }} />
      <ReadinessSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.red}30, transparent)`, margin: "0 60px" }} />
      <DifferentiatorsSection />
      <div style={{ height: 1, background: `linear-gradient(90deg, transparent, ${C.purple}30, transparent)`, margin: "0 60px" }} />
      <ClosingSection />
      <div style={{ height: 80 }} />
    </div>
  );
}
