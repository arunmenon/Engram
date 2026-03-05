# Engram Frontend Shell — Feature Walkthrough

A comprehensive guide to every feature in the Engram demo frontend: a 4-zone React SPA that visualizes agent context lineage, scoring decay, entity relationships, and user behavioral patterns.

---

## Table of Contents

1. [Application Layout](#1-application-layout)
2. [Chat Zone](#2-chat-zone)
3. [Knowledge Graph Zone](#3-knowledge-graph-zone)
4. [Insight Panel Zone](#4-insight-panel-zone)
5. [Session Timeline Zone](#5-session-timeline-zone)
6. [Keyboard Navigation](#6-keyboard-navigation)
7. [Accessibility](#7-accessibility)
8. [Demo / Live Mode Toggle](#8-demo--live-mode-toggle)
9. [Analytics & Observability](#9-analytics--observability)
10. [Shareable Playback URLs](#10-shareable-playback-urls)
11. [Architecture Overview](#11-architecture-overview)

---

## 1. Application Layout

The Engram shell is organized into **four zones** plus a global header:

```
+-------------------------------------------------------------+
|                        HEADER                                |
|  Logo | Session tabs | Demo/Live toggle | User | Auto-Play  |
+----------+---------------------------+----------------------+
|          |                           |                      |
|   CHAT   |     KNOWLEDGE GRAPH       |   INSIGHT PANEL      |
|  PANEL   |     (Sigma.js WebGL)      |   (Tabbed sidebar)   |
|  400px   |       flex-grow           |      350px           |
|          |                           |                      |
+----------+---------------------------+----------------------+
|                    SESSION TIMELINE                          |
|  Controls | S1 ●●●●●●● | 1 week | S2 ●●●●●● | 1 week | S3|
+-------------------------------------------------------------+
```

Each zone has a designated `role="region"` with `aria-label` for screen readers.

---

## 2. Chat Zone

### 2.1 Session Tabs
- Three pre-loaded sessions: **The Billing Problem** (S1), **The Feature Request** (S2), **The Escalation** (S3)
- Color-coded dots (blue, green, orange) identify each session
- Clicking a tab switches the chat, graph filter, and context panel simultaneously

### 2.2 Chat Messages
- **User messages** appear as blue bubbles (right-aligned styling)
- **Agent messages** appear as dark cards with:
  - **Tools used** — badges like `billing_lookup`, `refund_initiate`
  - **Provenance sources** — "3 sources" button linking to event IDs
  - **Context nodes used** — expandable section showing which graph nodes the agent retrieved
- Timestamps shown below each message

### 2.3 Context Nodes Used (Expandable)
Click "X context nodes used" on any agent message to reveal:
- Cards for each retrieved node (Event, Entity, etc.) with type badges
- Clicking a context node card highlights it in the graph and selects it
- Cards show node type, label, and link to the graph visualization

### 2.4 Chat Input
- **Demo mode**: Disabled with placeholder "Switch to Live mode to enable chat"
- **Live mode**: Active text input with Enter-to-submit, wired to the orchestrator API

---

## 3. Knowledge Graph Zone

### 3.1 Graph Visualization (Sigma.js)
A WebGL-accelerated graph rendered by Sigma.js v3 with force-atlas2 physics layout.

**Node shapes by type** (4 distinct shapes for 8 node types):
| Shape | Node Types |
|-------|-----------|
| Circle | Event, UserProfile |
| Triangle | Entity, Workflow |
| Diamond | Preference, Skill |
| Square | Summary, BehavioralPattern |

**Node colors by type**:
| Type | Color |
|------|-------|
| Event | Blue (#3b82f6) |
| Entity | Teal (#14b8a6) |
| Summary | Gray (#4b5563) |
| UserProfile | Purple (#8b5cf6) |
| Preference | Green (#22c55e) |
| Skill | Violet (#a855f7) |
| Workflow | Amber (#f59e0b) |
| BehavioralPattern | Amber (#f59e0b) |

**Edge types**: 16 distinct edge types with directional arrows (FOLLOWS, CAUSED_BY, REFERENCES, DERIVED_FROM, etc.) and color-coded lines.

**Interactions**:
- **Click node** — selects it, switches to Scores tab, fires analytics event
- **Hover node** — shows tooltip with type badge, label, event type, decay score bar
- **Click stage** — deselects current node
- **Scroll** — zoom in/out
- **Drag** — pan the viewport

### 3.2 Graph Controls (Top Bar)

**Layout Toggle**:
- **Force** (default) — ForceAtlas2 physics simulation with gravity, scaling, Barnes-Hut optimization
- **Circular** — Nodes arranged in a circle for structural overview

**Node Type Filters** (8 toggle buttons):
- Event, Entity, Pref, Skill, Summary, Profile, Pattern, Workflow
- Click to hide/show nodes of that type (and their connected edges)
- Screen reader announces "Entity nodes hidden" / "Entity nodes shown"

**Session Filter** (4 buttons):
- ALL, S1, S2, S3
- Filters dims out-of-session nodes and edges
- Camera animates to center on filtered session nodes

### 3.3 Graph Legend (Collapsible)
Bottom-right "Legend" button expands a reference panel:
- **Nodes section**: All 8 node types with shape + color swatches
- **Edges section**: All edge types grouped by category (Temporal, Causal, Entity, User, Behavioral) with color-coded line samples and labels

### 3.4 Graph Export
The graph can be exported as a PNG image via the GraphControls export button. Composites all Sigma.js canvas layers into a single downloadable image named `engram-graph-{timestamp}.png`.

### 3.5 Animated Traversals
When viewing "context nodes used", an "Animate" button triggers a step-by-step traversal animation through the graph:
- Nodes light up sequentially following the retrieval path
- Colors indicate retrieval reason: **blue** (direct), **purple** (proactive), **amber** (traversal), **cyan** (similar)
- Non-animated nodes dim to dark background
- Configurable animation speed (default 600ms per step)

---

## 4. Insight Panel Zone

A tabbed sidebar with 5 tabs (Debug tab is hidden by default).

### 4.1 Context Tab
Displays the retrieved context for the current session:
- **Summary stats**: Session node count, global node count, query latency (ms)
- **Inferred intents**: Horizontal bar chart of intent scores sorted descending (e.g., `what: 0.8`, `why: 0.3`, `how_does: 0.2`)
- **Node cards**: Scrollable list of all retrieved nodes with:
  - Type badge (color-coded)
  - Decay score
  - Label and event type
  - Confidence bar
- Clicking a node card selects it in the graph

### 4.2 User Tab
Complete user profile for Sarah Chen:

**Profile Card**:
- Name, role badge (Engineering Team Lead), tech level (Advanced), communication style
- Session count, total interactions, first/last seen dates

**Preferences** (4 items):
- Polarity icons: thumbs up (positive), thumbs down (negative), dash (neutral)
- Category badges (Communication, Workflow, Product, Competitor)
- Confidence bars with color coding
- Source event IDs linking back to provenance

**Skills** (2 items):
- Category badges (Management, Methodology)
- Proficiency progress bars with category-specific colors

**Interests** (4 items):
- Tag cloud with size/opacity weighted by interest strength
- Kanban Board, Swimlanes, Taskflow, Nimbus

**Behavioral Patterns** (3 cards):
Each pattern card includes:
- **Name + status badge** (active/emerging/declining with color coding)
- **Description** — what the pattern means
- **Confidence bar** — current confidence level
- **Confidence trend sparkline** — area chart showing confidence over time, colored by status
- **Observation timeline** — vertical timeline with dots for each observation:
  - Date, session ID badge, confidence delta (e.g., "+25%")
  - Description of what was observed
- **Recommendations** — actionable suggestions with:
  - Priority badge (high/medium/low)
  - Action text and rationale

### 4.3 Scores Tab
Displays scoring details for the selected graph node:

- **Radar chart**: 4-factor visualization (Recency, Importance, Relevance, User Affinity) on 0-1 scale
- **Decay curve**: 7-day exponential decay line chart parameterized by importance
- **Scoring weight sliders**: Adjustable weights (0-2) for each factor:
  - Recency, Importance, Relevance, User Affinity
  - Composite score updates in real-time as weights change
- **Factor breakdown table**: Raw score, weight, and weighted score for each factor

### 4.4 API Tab
Mock API call log showing the request/response lifecycle:

- **Call list**: Each entry shows:
  - Method badge (POST=green, GET=blue, PUT=orange, DELETE=red)
  - Endpoint path (monospace)
  - Latency (ms)
  - Status code (200=green, 201=green, 400=orange, 500=red)
- **Expandable details**: Click any call to reveal:
  - Request body (syntax-highlighted JSON)
  - Response body (syntax-highlighted JSON)
- **Live mode**: Shows real intercepted API calls via the apiLogStore interceptor
- **Demo mode**: Shows mock API call data

### 4.5 Debug Tab (Hidden by Default)
Toggle with **Ctrl+Shift+D**. Shows memory system observability:

**Summary bar**: Total node count, stream event count

**Event Stream Table**:
- Position (Redis stream ID), event type (color-coded badge), session ID, size in bytes
- 20 most recent events in reverse chronological order

**Consumer Group Status** (4 cards in 2x2 grid):
- Graph Projection, Session Extraction, Enrichment, Consolidation
- Each shows: pending count, lag, consumer count, status badge
- Status colors: green (healthy), amber (lagging), gray (idle)

**Node Counts by Type**: Grouped bar chart for all 8 node types

**Query Latency Histogram**: Distribution across 10 buckets (0-10ms through 2000+ms)

---

## 5. Session Timeline Zone

Bottom bar providing playback controls and visual timeline.

### 5.1 Playback Controls
- **Skip to start** (|<) — jump to first event
- **Play/Pause** (>) — start/stop auto-play through events
- **Skip to end** (>|) — jump to last event
- **Speed selector** — cycle through 1x, 2x, 5x playback speeds

### 5.2 Visual Timeline
- **Session segments**: Color-coded blocks for S1, S2, S3
- **Event dots**: Individual dots within each segment representing events
- **Gap labels**: "1 week" indicators between sessions
- **Progress indicator**: Current step / total steps (e.g., "12/18")
- **Click-to-seek**: Click any session segment to jump to it

### 5.3 Auto-Play
Click "Auto-Play" in the header to begin animated playback:
- Messages appear one by one in the chat panel
- Graph highlights update as events progress
- Timeline progress indicator advances
- Auto-advances through session boundaries
- Button changes to "Pause" during playback

---

## 6. Keyboard Navigation

Full keyboard control via the `useKeyboardNavigation` hook:

| Key | Action |
|-----|--------|
| Arrow Right | Step forward one event |
| Arrow Left | Step backward one event |
| Space | Toggle play/pause |
| 1, 2, 3 | Switch to session 1, 2, or 3 |
| Home | Skip to first event |
| End | Skip to last event |
| Ctrl+Shift+D | Toggle debug mode |

**Input guard**: All keyboard shortcuts are disabled when a text input or textarea is focused, preventing conflicts with chat typing.

---

## 7. Accessibility

### 7.1 ARIA Attributes
- `role="region"` + `aria-label` on all 4 zones (Chat, Graph, Insights, Timeline)
- `aria-selected` on active tab buttons
- `aria-pressed` on toggle buttons (layout, filters)
- Graph canvas has `tabindex="0"` and descriptive `aria-label`

### 7.2 Screen Reader Announcer
An `aria-live="polite"` region announces:
- Session switches ("Switched to Session 2")
- Node selection ("Selected: Sarah Chen")
- Filter changes ("Entity nodes hidden")
- Playback events

### 7.3 Focus Management
- Visible focus rings on all interactive elements via `focus-visible`
- Tab order follows visual layout (header → chat → graph → insights → timeline)

---

## 8. Demo / Live Mode Toggle

### 8.1 Demo Mode (Default)
- Pre-loaded mock data for 3 PayPal support scenarios
- 57 graph nodes, 40+ edges, 22 chat messages
- All features work against static mock data
- Chat input disabled

### 8.2 Live Mode
Toggle via the "Demo / Live" pill in the header. Persisted in localStorage.

**Scenario Picker**:
- 5 PayPal-domain scenarios: Account Setup, Billing Dispute, Fraud Alert, Merchant Dispute, Payment Failure
- Each shows title, description, and persona name
- Click to start a session via the orchestrator API

**Live Chat**:
- Real-time chat with LLM-powered agent (via litellm)
- Messages sent to `POST /api/chat` endpoint
- Graph updates from context queries in real-time

**Health Indicator**:
- Green dot = backend healthy
- Red dot = backend unreachable
- Polls `/v1/health` every 10 seconds

**API Call Logging**:
- Real HTTP calls intercepted via the apiLogStore interceptor
- Method, URL, status, duration, request/response bodies captured

---

## 9. Analytics & Observability

### 9.1 Analytics Event Bus
All user interactions fire structured analytics events to the console:

| Event Type | Tracked Properties |
|------------|-------------------|
| `node.click` | nodeId, nodeType |
| `node.hover` | nodeId, nodeType, durationMs |
| `playback.play` | — |
| `playback.pause` | — |
| `playback.step` | direction (forward/backward) |
| `playback.speed` | speed (1/2/5) |
| `session.switch` | sessionId |
| `insight_tab.switch` | tab |
| `filter.toggle` | filterType, value, enabled |
| `graph.layout_change` | layout (force/circular) |
| `graph.export_png` | — |
| `graph.copy_link` | — |

Events are logged via `[analytics]` prefix in the browser console. The tracker supports pluggable sinks for future API integration.

### 9.2 Debug Mode
See [Section 4.5 — Debug Tab](#45-debug-tab-hidden-by-default) for the full observability dashboard.

---

## 10. Shareable Playback URLs

The `usePlaybackUrl` hook encodes application state into the URL hash:

```
http://localhost:5173/#session=session-2&step=8&speed=2&layout=circular
```

**Encoded parameters**:
| Parameter | Description | Example |
|-----------|-------------|---------|
| `session` | Current session ID | `session-1` |
| `step` | Current playback step | `5` |
| `speed` | Playback speed multiplier | `2` |
| `layout` | Graph layout type | `force` or `circular` |

**Behavior**:
- State restored on page load from URL hash
- Hash updates debounced at 300ms to avoid excessive updates
- "Copy Link" button copies current URL for sharing

---

## 11. Architecture Overview

### Tech Stack
| Layer | Technology |
|-------|-----------|
| Framework | React 18.3 + TypeScript 5.5 |
| Bundler | Vite 5.4 |
| State | Zustand 4.5 (9 stores) |
| Graph | Sigma.js 3.0 + Graphology 0.25 |
| Charts | Recharts 2.12 |
| Animation | Framer Motion 11.3 |
| Icons | Lucide React 0.424 |
| Styling | Tailwind CSS 3.4 (dark theme) |

### Store Architecture (9 Zustand stores)
| Store | Purpose |
|-------|---------|
| `sessionStore` | Mock session playback, messages, visible steps |
| `graphStore` | Nodes, edges, selection, filters, layout, Sigma ref |
| `insightStore` | Active tab, debug mode toggle |
| `chatStore` | Live mode scenarios, messages, streaming |
| `userStore` | User profile, preferences, skills, interests, patterns |
| `apiLogStore` | Live API call interception and logging |
| `animationStore` | Traversal animation state (nodes, edges, speed) |
| `debugStore` | Stream events, consumer groups, node counts, latency |
| `announceStore` | Screen reader announcements |

### Custom Hooks (4)
| Hook | Purpose |
|------|---------|
| `useKeyboardNavigation` | Arrow keys, space, numbers, home/end |
| `useGraphExport` | Composite Sigma canvases to PNG |
| `useTraversalAnimation` | Step through animated retrieval paths |
| `usePlaybackUrl` | URL hash ↔ playback state sync |

### API Integration (Vite Proxy)
| Route | Target | Purpose |
|-------|--------|---------|
| `/v1/*` | `localhost:8000` | Context Graph API |
| `/api/*` | `localhost:8100` | Orchestrator service |

### Mock Data (7 files)
- **mockGraph.ts** — 57 nodes + 40+ edges across 3 sessions
- **mockSessions.ts** — 3 sessions with 22 messages
- **mockScores.ts** — Intent scores + decay curve generator
- **mockUserProfile.ts** — Sarah Chen profile + enhanced behavioral patterns
- **mockApiCalls.ts** — 8 sample API call entries
- **mockDebug.ts** — Stream events, consumer groups, node stats, latency histogram
- **constants.ts** — Node type badge color mappings

---

## Quick Start

```bash
cd demo/frontend
npm install
npm run dev        # → http://localhost:5173
```

**Demo mode** works immediately with mock data. For **Live mode**, start the full stack:

```bash
cd docker
docker compose up -d   # Redis, Neo4j, API (8000), Orchestrator (8100)
```

Then toggle "Live" in the header and pick a scenario.

---

## E2E Test Summary

| Feature | Status | Notes |
|---------|--------|-------|
| 4-zone layout | PASS | All zones render, flex layout correct |
| Session switching (S1/S2/S3) | PASS | Chat, graph filter, context tab all update |
| Chat messages + timestamps | PASS | User/agent styling, tools badges |
| Context nodes used (expand) | PASS | Shows node cards with type badges |
| Provenance sources button | PASS | Displays source event IDs |
| Graph visualization (force) | PASS | Sigma.js renders with shapes + colors |
| Graph visualization (circular) | PASS | Nodes arranged in circle |
| Node selection (click) | PASS | Highlight, scores tab, analytics event |
| Node hover tooltip | PASS | Type badge, label, decay score |
| Node type filtering | PASS | Hide/show with announcer |
| Session filter (graph) | PASS | Dims out-of-session, camera pan |
| Graph legend | PASS | All 8 node types + edge types |
| Scores tab (radar) | PASS | 4-factor radar chart renders |
| Scores tab (decay curve) | PASS | 7-day exponential decay |
| Scores tab (weight sliders) | PASS | Composite score updates |
| User tab (profile) | PASS | Name, role, tech level, stats |
| User tab (preferences) | PASS | Polarity icons, confidence bars |
| User tab (skills) | PASS | Category bars with proficiency |
| User tab (interests) | PASS | Weighted tag cloud |
| User tab (behavioral patterns) | PASS | Timeline, trend, recommendations |
| API tab (call log) | PASS | Method/status coloring, expand |
| Debug tab (Ctrl+Shift+D) | PASS | Stream tail, consumers, charts |
| Auto-play | PASS | Messages appear sequentially |
| Play/Pause controls | PASS | Button toggles, timer works |
| Speed selector (1x/2x/5x) | PASS | Speed cycles through options |
| Keyboard navigation | PASS | Arrows, space, numbers, home/end |
| Demo/Live mode toggle | PASS | Switches UI, persists in localStorage |
| Scenario picker (Live mode) | PASS | 5 scenarios with personas |
| Health indicator (Live mode) | PASS | Green dot with "Backend healthy" |
| Analytics events (console) | PASS | node.click, filter.toggle, layout_change |
| Screen reader announcer | PASS | Announces selections and filters |
| ARIA regions + labels | PASS | 4 labeled regions |
| URL hash state (shareable) | PASS | Session, step, speed, layout encoded |
| TypeScript compilation | PASS | `tsc --noEmit` clean |
| Production build | PASS | `vite build` — 970KB JS, 24KB CSS |
| Console errors | PASS | Zero errors |
