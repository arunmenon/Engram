# Engram FE Shell -- Feature Breakdown

Structured inventory of every feature in the Engram demo frontend, organized into 7 categories. For each feature: name, description, UI location, key interactions, implementing component(s), and driving store(s).

---

## Category 1: Mode System & Navigation

### 1.1 Demo / Live Mode Toggle

**Description:** A pill-shaped toggle in the header right section switches between "Demo" (offline mock data) and "Live" (connected to Engram backend). Switching triggers a full page reload to re-initialize all stores with the correct data source.

**UI Location:** Header, right side -- two-button pill labeled "Demo" and "Live".

**Key Interactions:**

- Click "Demo" to switch to mock data mode (blue highlight).
- Click "Live" to switch to backend-connected mode (green highlight).
- Mode persists in `localStorage` under key `engram-data-mode`.
- Page reloads on toggle to re-initialize stores.

**Component(s):** `components/layout/Header.tsx`
**Store(s):** `api/mode.ts` (`getDataMode`, `setDataMode`)

---

### 1.2 Live Sub-Mode Toggle (Interactive / Simulator / Dynamic)

**Description:** When in Live mode, a second pill-shaped toggle appears with three sub-mode options: Interactive (direct chat with backend), Simulator (scripted scenario playback with real ingestion), and Dynamic (LLM-powered two-agent conversations).

**UI Location:** Header, right side -- appears only when Live mode is active, next to the Demo/Live toggle.

**Key Interactions:**

- Click "Interactive" for direct chat mode (green highlight).
- Click "Simulator" for scripted playback mode (purple highlight).
- Click "Dynamic" for LLM conversation mode (orange highlight).
- Sub-mode persists in `localStorage` under key `engram-live-submode`.
- Page reloads on toggle.

**Component(s):** `components/layout/Header.tsx`
**Store(s):** `api/mode.ts` (`getLiveSubMode`, `setLiveSubMode`)

---

### 1.3 Backend Health Indicator

**Description:** A small colored dot in the header indicates whether the Engram backend API is reachable. Green when healthy, red when unreachable. Polls the `/health` endpoint at a configurable interval.

**UI Location:** Header, right side -- visible in Live mode (Interactive and Dynamic sub-modes). Simulator mode uses its own backend status badge in SimulatorControls.

**Key Interactions:**

- Hover to see tooltip ("Backend healthy" or "Backend unreachable").
- Automatically polls in the background while Live mode is active.

**Component(s):** `components/layout/Header.tsx`
**Store(s):** Local state in Header via `useState(healthy)`; health check uses `API_BASE_URL` from config.

---

### 1.4 User Avatar Display

**Description:** A static display showing the current user persona name ("Sarah Chen") and initials avatar ("SC") in a purple circle. Present in all modes.

**UI Location:** Header, far right, before the play/pause button.

**Key Interactions:** None (display only).

**Component(s):** `components/layout/Header.tsx`

---

### 1.5 Session Tabs (Demo Mode)

**Description:** Clickable session tabs in both the header center and the ChatPanel top bar. Each tab shows a colored dot and session number (S1, S2, S3). The header also shows the current session title. In Demo mode, clicking a tab switches the visible chat messages and updates the graph session filter.

**UI Location:** Header center area; also duplicated in ChatPanel top bar (Demo mode only).

**Key Interactions:**

- Click a session tab to switch the active session.
- The graph panel session filter updates automatically via `graphStore.setSessionFilter`.
- Active tab shows a ring highlight and white text; inactive tabs are dimmed.

**Component(s):** `components/layout/Header.tsx`, `components/chat/ChatPanel.tsx`
**Store(s):** `stores/sessionStore.ts` (`currentSessionId`, `setCurrentSession`)

---

### 1.6 Play/Pause Controls in Header

**Description:** Mode-specific play/pause buttons in the header right area. Demo mode shows "Auto-Play"/"Pause" button. Simulator mode shows a purple Play/Pause button. Dynamic mode shows an orange Play/Pause button. These are quick-access duplicates of the main transport controls in each mode's panel.

**UI Location:** Header, far right.

**Key Interactions:**

- Demo: Toggles auto-play of the scripted walkthrough (drives `sessionStore.play/pause`).
- Simulator: Toggles scripted playback (drives `simulatorStore.play/pause`).
- Dynamic: Toggles auto-play of LLM turns (drives `dynamicSimStore.startAutoPlay/pauseAutoPlay`).

**Component(s):** `components/layout/Header.tsx`
**Store(s):** `stores/sessionStore.ts`, `stores/simulatorStore.ts`, `stores/dynamicSimStore.ts`

---

## Category 2: Demo Mode Playback

### 2.1 Three-Session Scripted Walkthrough

**Description:** Demo mode presents a pre-built Sarah Chen support story across 3 sessions (S1, S2, S3). Each session contains scripted chat messages between a user and agent. Messages reveal progressively as the user steps through the walkthrough, building the context graph over time.

**UI Location:** Chat panel (left, 400px wide) with messages; graph panel (center) with accumulating nodes.

**Key Interactions:**

- Messages appear one at a time during playback.
- Session transitions happen automatically when messages cross session boundaries.
- The graph shows mock data (pre-computed nodes and edges from `mockGraph.ts`).

**Component(s):** `components/chat/ChatPanel.tsx`, `components/chat/ChatMessage.tsx`
**Store(s):** `stores/sessionStore.ts` (`messages`, `visibleMessagesPerSession`, `currentStepIndex`)
**Data:** `data/mockSessions.ts` (sessions, messages), `data/mockGraph.ts` (nodes, edges)

---

### 2.2 Play/Pause/Step Forward/Backward Controls

**Description:** Full transport controls for stepping through the demo walkthrough. Play auto-advances messages at the configured speed. Step forward/backward moves one message at a time. Skip to start resets to before the first message; skip to end reveals all messages.

**UI Location:** Bottom timeline bar (SessionTimeline), and header play/pause button.

**Key Interactions:**

- Play: Auto-advances at interval = 2000ms / playbackSpeed.
- Pause: Stops auto-advance.
- Step Forward: Reveals next message; auto-switches session if next message is in a different session.
- Step Backward: Hides the last message; switches session back if needed.
- Skip to Start: Resets to step -1 (no messages visible).
- Skip to End: Reveals all messages across all sessions.
- GoToStep(index): Jump to any specific message by global index.

**Component(s):** `components/timeline/SessionTimeline.tsx`, `components/layout/Header.tsx`
**Store(s):** `stores/sessionStore.ts` (`play`, `pause`, `stepForward`, `stepBackward`, `skipToStart`, `skipToEnd`, `goToStep`)

---

### 2.3 Keyboard Shortcuts

**Description:** Global keyboard shortcuts for demo mode navigation. Active when focus is not in an input or textarea.

**UI Location:** Global (document-level keydown listener).

**Key Interactions:**

- Right Arrow: Step forward one message.
- Left Arrow: Step backward one message.
- Space: Toggle play/pause.
- 1/2/3: Switch to session 1/2/3 directly.
- Home: Skip to start.
- End: Skip to end.

**Component(s):** `hooks/useKeyboardNavigation.ts`
**Store(s):** `stores/sessionStore.ts`

---

### 2.4 Playback Speed (1x/2x/5x)

**Description:** Cycle through playback speeds by clicking the speed button in the timeline. Speed affects the auto-play interval (2000ms / speed). Available speeds are 1x, 2x, and 5x.

**UI Location:** Bottom timeline bar, left side, after the play/pause buttons.

**Key Interactions:**

- Click to cycle: 1x -> 2x -> 5x -> 1x.
- Speed is displayed as a monospace badge (e.g., "2x").
- Also persisted in URL hash.

**Component(s):** `components/timeline/SessionTimeline.tsx`
**Store(s):** `stores/sessionStore.ts` (`playbackSpeed`, `setPlaybackSpeed`)

---

### 2.5 URL Persistence (Hash-Based State)

**Description:** The current playback state is persisted in the URL hash for bookmarking and sharing. Includes session, step, speed, and layout type. On page load, state is restored from the hash.

**UI Location:** Browser URL bar (e.g., `#session=session-2&step=5&speed=2&layout=force`).

**Key Interactions:**

- State updates are debounced (300ms) before writing to the hash.
- On mount, hash is parsed and applied to sessionStore and graphStore.
- Supports: `session`, `step`, `speed`, `layout` parameters.

**Component(s):** `hooks/usePlaybackUrl.ts`
**Store(s):** `stores/sessionStore.ts`, `stores/graphStore.ts`

---

### 2.6 Session Timeline Scrubber

**Description:** A horizontal timeline at the bottom of the screen showing all 3 sessions as colored bands. Each band contains event dots representing individual messages. Dots are clickable to jump to that specific step. The currently active dot is enlarged with a white ring.

**UI Location:** Bottom of the screen, full width, 100px tall.

**Key Interactions:**

- Click a session band to switch to that session.
- Click an individual event dot to jump to that step (via `goToStep`).
- Active dot is visually distinguished (larger, ring, scale-125).
- Past dots have higher opacity than future dots.
- Step counter shown on the right (e.g., "5/18").

**Component(s):** `components/timeline/SessionTimeline.tsx`
**Store(s):** `stores/sessionStore.ts`, `stores/graphStore.ts`

---

### 2.7 Inter-Session Gap Labels

**Description:** Between session bands in the timeline, vertical markers show the time gap between sessions (e.g., "2 weeks", "3 days"). Demonstrates how Engram tracks cross-session temporal relationships.

**UI Location:** Between session bands in the bottom timeline.

**Key Interactions:** None (display only). Gap is calculated from session end_time to next session start_time.

**Component(s):** `components/timeline/SessionTimeline.tsx` (`getGapLabel` function)

---

## Category 3: Graph Visualization

### 3.1 Force-Directed (ForceAtlas2) Layout

**Description:** The default graph layout algorithm. Uses graphology-layout-forceatlas2 with 100 iterations, Barnes-Hut optimization, gravity=1, and scalingRatio=10. Produces organic, physics-based node positioning where connected nodes cluster together.

**UI Location:** Center panel, full graph area.

**Key Interactions:**

- Click "Force" button in GraphControls to activate.
- Re-runs layout algorithm when toggled from circular.
- Active state shown with blue highlight on the Force button.

**Component(s):** `components/graph/GraphVisualization.tsx`, `components/graph/GraphControls.tsx`
**Store(s):** `stores/graphStore.ts` (`layoutType`, `setLayoutType`)

---

### 3.2 Circular (Radial) Layout

**Description:** Alternative layout that positions all nodes in a circle. Radius is computed as max(100, nodeCount \* 8). Useful for seeing all nodes equally without clustering.

**UI Location:** Center panel, full graph area.

**Key Interactions:**

- Click "Circular" button in GraphControls to activate.
- Nodes are repositioned in a circle using trigonometric placement.

**Component(s):** `components/graph/GraphVisualization.tsx` (`computeCircularPositions`), `components/graph/GraphControls.tsx`
**Store(s):** `stores/graphStore.ts` (`layoutType`, `setLayoutType`)

---

### 3.3 Node Type Shapes (8 Types)

**Description:** Each of the 8 displayed node types has a distinct shape for visual differentiation:

- **Circle:** Event, UserProfile
- **Triangle:** Entity, Workflow, Goal
- **Diamond:** Preference, Skill, Belief
- **Square:** Summary, BehavioralPattern, Episode

Custom WebGL programs render each shape (NodeDiamondProgram, NodeSquareProgram, NodeTriangleProgram from `programs/` subdirectory).

**UI Location:** Graph nodes in the center panel.

**Key Interactions:** Visual only; shapes are automatically assigned based on node_type.

**Component(s):** `components/graph/GraphVisualization.tsx` (`NODE_TYPE_SHAPE` mapping, custom programs)

---

### 3.4 Edge Types with Directional Arrows and Colors

**Description:** 20 edge types are rendered with distinct colors. Directed edges (FOLLOWS, CAUSED_BY, REFERENCES, DERIVED_FROM, etc.) display arrowheads. Undirected edges (SIMILAR_TO) render as plain lines. Each edge type has a specific color defined in `EDGE_COLORS`.

**UI Location:** Edges connecting nodes in the graph panel.

**Key Interactions:** Visual differentiation only. Edge labels can be rendered via Sigma's `renderEdgeLabels: true`.

**Component(s):** `components/graph/GraphVisualization.tsx` (`DIRECTED_EDGE_TYPES` set)
**Data:** `types/graph.ts` (`EDGE_COLORS`)

---

### 3.5 Node Type Toggle Filters (8 Toggles)

**Description:** Eight toggle buttons to show/hide specific node types. Each toggle shows a colored dot and label (Event, Entity, Pref, Skill, Summary, Profile, Pattern, Workflow). Toggling off a type hides those nodes and their connected edges from the graph.

**UI Location:** GraphControls overlay, top-right of graph panel, middle section.

**Key Interactions:**

- Click a toggle to hide/show that node type.
- Active (visible) types show full-opacity colored dots; hidden types show 25% opacity.
- Hidden nodes return `hidden: true` from the nodeReducer.
- Edges connected to hidden nodes are also hidden.
- Screen reader announcement: "Event nodes hidden/shown".

**Component(s):** `components/graph/GraphControls.tsx`
**Store(s):** `stores/graphStore.ts` (`visibleNodeTypes`, `toggleNodeType`)

---

### 3.6 Session Filter (All/S1/S2/S3)

**Description:** Four buttons to filter the graph view by session. "All" shows all sessions; S1/S2/S3 focus on a specific session, dimming nodes from other sessions. In Simulator mode, session filters trigger fresh graph fetches from the backend.

**UI Location:** GraphControls overlay, top-right of graph panel, bottom section.

**Key Interactions:**

- Click "All" to show all sessions (removes filter).
- Click S1/S2/S3 to focus on that session.
- Non-matching nodes are dimmed (color set to #1e1e24, labels hidden).
- Non-matching edges are dimmed (color #1a1a22, size reduced to 0.5).
- Camera animates to center on the filtered session's nodes.
- In Simulator mode, "All" merges results from all session queries.

**Component(s):** `components/graph/GraphControls.tsx`
**Store(s):** `stores/graphStore.ts` (`sessionFilter`, `setSessionFilter`), `stores/simulatorStore.ts` (`fetchGraphForFilter`)

---

### 3.7 Click-to-Select Nodes

**Description:** Clicking a node in the graph selects it, highlights it with `zIndex: 10`, and automatically switches the InsightPanel to the Scores tab to show that node's scoring details.

**UI Location:** Any node in the graph panel.

**Key Interactions:**

- Click a node to select it (highlighted with higher z-index).
- InsightPanel switches to "Scores" tab automatically.
- Click the empty stage (background) to deselect.
- Screen reader announcement: "Selected: [node label]" or "Selection cleared".

**Component(s):** `components/graph/GraphVisualization.tsx` (`handleClickNode`, `handleClickStage`)
**Store(s):** `stores/graphStore.ts` (`selectedNodeId`, `selectNode`), `stores/insightStore.ts` (`setActiveTab`)

---

### 3.8 Hover Tooltips

**Description:** Hovering over a graph node displays a floating tooltip with: node type badge (colored dot + uppercase label), node label, event type or entity type (if applicable), and a decay score progress bar with color coding (green >0.7, amber >0.4, red <=0.4).

**UI Location:** Floating above/near the hovered node in the graph panel.

**Key Interactions:**

- Hover enter: tooltip appears offset 12px right and 10px above the node's viewport position.
- Hover leave: tooltip disappears.
- Hover duration is tracked for analytics.

**Component(s):** `components/graph/GraphVisualization.tsx` (tooltip state, `handleEnterNode`, `handleLeaveNode`)

---

### 3.9 Pan, Zoom, and Node Dragging

**Description:** The Sigma.js renderer supports mouse pan (click-drag on background), scroll-wheel zoom, and individual node dragging. During a drag, the camera is disabled to prevent pan conflicts. After a drag, the click event is suppressed to avoid accidental selection.

**UI Location:** Entire graph panel area.

**Key Interactions:**

- Pan: Click and drag on the background.
- Zoom: Scroll wheel.
- Drag node: Click-hold on a node, then move. Camera re-enables on mouse up.
- ARIA label: "Interactive knowledge graph. Use mouse to pan and zoom."

**Component(s):** `components/graph/GraphVisualization.tsx` (`handleDownNode`, `handleMouseMove`, `handleMouseUp`)

---

### 3.10 Collapsible Legend

**Description:** A collapsible panel showing the visual mapping for all node shapes and edge line styles. Nodes section shows 8 types with their shape icons (circle, triangle, diamond, square) and colors. Edges section shows 4 groups: Arrows (directed, solid), Dashed (SIMILAR_TO), Dotted (user relationships), and Solid (structural).

**UI Location:** Bottom-right of graph panel, expandable via "Legend" button.

**Key Interactions:**

- Click "Legend" button to expand/collapse.
- Expanded panel shows: Nodes section (8 items with SVG shape icons) + Edges section (4 groups with SVG line+arrow renderings).
- Animated expand/collapse with framer-motion.
- ChevronDown rotates 180 degrees when expanded.

**Component(s):** `components/graph/GraphLegend.tsx`

---

### 3.11 Decay Score Visualization (Node Size)

**Description:** Node size in the graph is driven by the decay_score from the Atlas response. Nodes with higher decay scores appear larger, providing immediate visual indication of memory freshness. Node colors also vary by event subtype for Event nodes.

**UI Location:** Node rendering in the graph panel.

**Key Interactions:** Visual only. Size is set during graph data transformation.

**Component(s):** `components/graph/GraphVisualization.tsx`
**Data:** `types/graph.ts` (`GraphNode.size`, `GraphNode.decay_score`)

---

### 3.12 Event Subtype Coloring

**Description:** Event nodes are color-coded by their event_type subtype: agent.invoke (blue #3b82f6), tool.execute (green #22c55e), observation.input (amber #f59e0b), system.session_start and system.session_end (gray #6b7280). Non-Event node types have fixed colors per type.

**UI Location:** Node colors in the graph.

**Key Interactions:** Visual only. Colors assigned during Atlas response transformation.

**Component(s):** `components/graph/GraphVisualization.tsx`
**Data:** `types/graph.ts` (`NODE_COLORS`)

---

## Category 4: Context Insights Panel

### 4.1 Tab Navigation

**Description:** The Insight Panel on the right side has a tab bar with 4 base tabs: Context, User, Scores, API. Each tab has an icon (Layers, User, BarChart3, Terminal). An optional Debug tab (Bug icon) can be enabled. The active tab is indicated with a blue bottom border and text color.

**UI Location:** Right panel (350px wide), top tab bar.

**Key Interactions:**

- Click a tab to switch content.
- Active tab has blue underline + blue text.
- `aria-selected` attribute set on active tab.
- Scores tab is auto-selected when a graph node is clicked.

**Component(s):** `components/insight/InsightPanel.tsx`
**Store(s):** `stores/insightStore.ts` (`activeTab`, `setActiveTab`)

---

### 4.2 Context Tab

**Description:** Shows the retrieved context for the current session. Displays session vs global node counts, query latency (ms), an intent distribution chart, and a scrollable list of clickable node cards.

**UI Location:** Insight Panel, "Context" tab content.

**Key Interactions:**

- Session node count displayed in a blue badge; global count in a gray badge.
- Query latency shown (52ms/87ms/145ms depending on session).
- Intent distribution as horizontal bar chart (IntentChart component).
- Clickable NodeCard components -- clicking selects the node in the graph and switches to Scores tab.

**Component(s):** `components/insight/ContextTab.tsx`, `components/shared/IntentChart.tsx`, `components/shared/NodeCard.tsx`
**Store(s):** `stores/sessionStore.ts` (`currentSessionId`), `stores/graphStore.ts` (`nodes`)
**Data:** `data/mockScores.ts` (`sessionIntents`)

---

### 4.3 Intent Distribution Chart (IntentChart)

**Description:** Horizontal bar chart showing the inferred intents for the current session context query. Each intent type (why, when, what, related, general, who_is, how_does, personalize) is shown as a bar with its score (0-1). Bars are sorted by score descending.

**UI Location:** Inside the Context tab, below the node counts.

**Key Interactions:** Display only. Bar width animates via CSS transition (500ms).

**Component(s):** `components/shared/IntentChart.tsx`

---

### 4.4 Node Cards (Clickable)

**Description:** Compact cards showing node type badge, label, event type, and a decay score confidence bar. Clicking a card selects that node in the graph and opens the Scores tab. Available in both full and compact variants.

**UI Location:** Context tab (full list) and ContextUsed expandable in chat messages (compact).

**Key Interactions:**

- Click to select node in graph (via `graphStore.selectNode`).
- Click also sets the node in insight store (navigates to Scores tab).
- Full variant: shows type badge, label, event_type, decay confidence bar.
- Compact variant: shows type badge and label only.

**Component(s):** `components/shared/NodeCard.tsx`, `components/shared/ConfidenceBar.tsx`
**Store(s):** `stores/graphStore.ts` (`selectNode`), `stores/insightStore.ts` (`setSelectedNode`)

---

### 4.5 User Tab -- Profile Card

**Description:** Displays the user's profile information: name (large heading), role badge (purple), tech_level badge (blue), communication_style badge (gray). Below: a 2-column grid showing session count, total interactions, first seen date, and last seen date.

**UI Location:** Insight Panel, "User" tab, top section.

**Key Interactions:** Display only. Data comes from userStore (mock in Demo, live in Simulator/Dynamic).

**Component(s):** `components/insight/UserTab.tsx`
**Store(s):** `stores/userStore.ts` (`profile`)

---

### 4.6 User Tab -- Preferences with Confidence Bars

**Description:** Lists the user's extracted preferences with: polarity icon (ThumbsUp green, ThumbsDown red, Minus gray), preference value text, category badge, confidence bar (0-1), and source event IDs.

**UI Location:** Insight Panel, "User" tab, "Preferences" section.

**Key Interactions:** Display only. Confidence bars animate with CSS transitions (500ms duration).

**Component(s):** `components/insight/UserTab.tsx`, `components/shared/ConfidenceBar.tsx`
**Store(s):** `stores/userStore.ts` (`preferences`)

---

### 4.7 User Tab -- Skills with Proficiency Indicators

**Description:** Lists the user's detected skills with: skill name, category badge, and a horizontal proficiency bar (0-1). Bar colors are category-specific (Management=purple, Methodology=blue, default=teal).

**UI Location:** Insight Panel, "User" tab, "Skills" section.

**Key Interactions:** Display only. Proficiency bars use CSS width transitions.

**Component(s):** `components/insight/UserTab.tsx`
**Store(s):** `stores/userStore.ts` (`skills`)

---

### 4.8 User Tab -- Interests with Weight Indicators

**Description:** Displays user interests as tag pills with variable opacity and font size based on weight. Higher-weight interests appear larger and more opaque (teal-colored pills).

**UI Location:** Insight Panel, "User" tab, "Interests" section.

**Key Interactions:** Display only. Opacity = 0.4 + weight _ 0.6; font size = 11 + weight _ 3 px.

**Component(s):** `components/insight/UserTab.tsx`
**Store(s):** `stores/userStore.ts` (`interests`)

---

### 4.9 User Tab -- Behavioral Patterns

**Description:** Rich pattern cards showing: pattern name, status badge (active=green, emerging=blue, declining=amber), description, confidence bar, confidence trend sparkline (ConfidenceTrend), observation timeline (PatternTimeline), and action recommendations (PatternRecommendations).

**UI Location:** Insight Panel, "User" tab, "Behavioral Patterns" section.

**Key Interactions:**

- Confidence trend: 120x40px area chart (Recharts AreaChart) with color based on status.
- Pattern timeline: Vertical timeline with dots (green/red) showing confidence deltas per observation.
- Recommendations: Priority-labeled action cards (high=red, medium=amber, low=blue) with rationale.

**Component(s):** `components/insight/UserTab.tsx`, `components/insight/PatternTimeline.tsx`, `components/insight/ConfidenceTrend.tsx`, `components/insight/PatternRecommendations.tsx`
**Store(s):** `stores/userStore.ts` (`patterns`)

---

### 4.10 Scores Tab -- 4-Factor Radar Chart

**Description:** A Recharts RadarChart showing 4 scoring factors: Recency, Importance, Relevance, and User Affinity. Each axis ranges 0-1. The chart displays a blue filled polygon representing the selected node's scores. Appears only when a node is selected.

**UI Location:** Insight Panel, "Scores" tab, top section.

**Key Interactions:**

- No node selected: shows a placeholder with Target icon and "Select a node" message.
- Node selected: radar chart auto-populates with node's scores.

**Component(s):** `components/insight/ScoresTab.tsx`, `components/shared/ScoreRadar.tsx`
**Store(s):** `stores/graphStore.ts` (`selectedNodeId`, `nodes`)

---

### 4.11 Scores Tab -- Ebbinghaus Decay Curve

**Description:** A Recharts LineChart showing the Ebbinghaus forgetting curve for the selected node. X-axis shows days (D0-D30), Y-axis shows decay score (0-1). The curve is generated from the node's initial score and importance, demonstrating how memory strength decays over time.

**UI Location:** Insight Panel, "Scores" tab, "Decay Curve" section.

**Key Interactions:**

- Hover over data points to see tooltips with exact day and score.
- Curve is generated by `generateDecayCurve(initialScore, importance)`.

**Component(s):** `components/insight/ScoresTab.tsx`, `components/shared/DecayCurve.tsx`
**Data:** `data/mockScores.ts` (`generateDecayCurve`)

---

### 4.12 Scores Tab -- Adjustable Weight Sliders

**Description:** Four range sliders for adjusting the scoring weights: Recency, Importance, Relevance, User Affinity. Range 0-2 with step 0.1. Changes recalculate the composite score in real time.

**UI Location:** Insight Panel, "Scores" tab, "Scoring Weights" section.

**Key Interactions:**

- Drag a slider to adjust its weight (0.0 - 2.0).
- Current value displayed as monospace number to the right.
- Composite score updates immediately below.

**Component(s):** `components/insight/ScoresTab.tsx`
**Store(s):** Local state via `useState(weights)`.

---

### 4.13 Scores Tab -- Composite Score Calculation

**Description:** A prominent display showing the weighted average composite score, calculated as sum(factor \* weight) / sum(weights). Shown as a large blue monospace number (e.g., "0.742"). A factor breakdown table below shows each factor's raw value, weight, and weighted contribution.

**UI Location:** Insight Panel, "Scores" tab, bottom section.

**Key Interactions:**

- Real-time recalculation as weight sliders change.
- Table columns: Factor, Raw, Weight, Weighted.

**Component(s):** `components/insight/ScoresTab.tsx`

---

### 4.14 API Tab -- Call Log

**Description:** A scrollable list of API calls made during the session. In Demo mode, shows mock API calls. In Live mode, shows real intercepted calls from the EngramClient. Each entry is expandable to reveal the full request and response JSON.

**UI Location:** Insight Panel, "API" tab.

**Key Interactions:**

- Click a call entry to expand/collapse the request/response details.
- Method badge: GET=blue, POST=green, PUT=orange, DELETE=red.
- Endpoint shown in monospace font.
- Latency displayed (e.g., "52ms").
- Status code color-coded (200/201=green, 400=orange, 500=red).
- Request JSON shown in green; Response JSON shown in blue.
- Animated expand/collapse with framer-motion.

**Component(s):** `components/insight/ApiTab.tsx`
**Store(s):** `stores/apiLogStore.ts` (`calls`, `addCall`)
**Data:** `data/mockApiCalls.ts` (Demo mode fallback)

---

## Category 5: Simulator Mode (Scripted Playback)

### 5.1 Scenario Picker (4 Personas)

**Description:** A card-based selection screen showing 4 available scenarios: Sarah Chen (SaaS billing), Marcus Rivera (merchant payments), Priya Sharma (travel loyalty), and David Park (real estate). Each card shows: persona avatar (colored circle with initials), title, subtitle, description, and stats (session count, message count, node count).

**UI Location:** Chat panel (left, 400px) when Simulator mode is active and status is "picking".

**Key Interactions:**

- Click a scenario card to select it (triggers `pickScenario`).
- Cards have hover effects (blue border, Play icon color change).
- Stats shown with icons: Users (sessions), MessageSquare (messages), GitBranch (nodes).

**Component(s):** `components/simulator/SimulatorPicker.tsx`
**Store(s):** `stores/simulatorStore.ts` (`pickScenario`)
**Data:** `data/scenarios.ts` (`allScenarios`)

---

### 5.2 Multi-Session Scripted Playback with Auto-Ingest

**Description:** After picking a scenario, messages play back one at a time. Each message step ingests real events into the Engram backend: session_start events, message events (observation.input or agent.invoke), tool.execute events, and session_end events at session boundaries. Timestamps are rebased to current time to avoid future-drift rejection.

**UI Location:** Chat panel shows messages; graph accumulates nodes from the backend.

**Key Interactions:**

- Each step: (1) ingest events via EngramClient.ingestBatch, (2) wait 200ms for projection, (3) fetch live graph from backend, (4) at session end: wait 500ms for extraction, re-fetch graph, fetch user data.
- Session lifecycle events (start/end) are auto-generated at session boundaries.
- Timestamp rebasing maps scenario dates to current time with preserved relative offsets.

**Component(s):** `components/simulator/SimulatorChat.tsx`
**Store(s):** `stores/simulatorStore.ts` (`applyStep`, `ingestStepEvents`, `fetchLiveGraph`)

---

### 5.3 Transport Controls

**Description:** Full set of playback transport controls: skip to start, step backward, play/pause, step forward, skip to end. Speed selector with 0.5x, 1x, 2x, 3x options. Reset button to return to scenario picker.

**UI Location:** Bottom of chat panel, below the progress bar.

**Key Interactions:**

- Skip to start (SkipBack icon): Resets to step -1, clears graph.
- Step backward (ChevronLeft): Goes back one step; re-fetches graph (can't un-ingest events).
- Play/Pause (Play/Pause icon): Toggles auto-play. Disabled if backend not connected.
- Step forward (ChevronRight): Advances one step, ingests events.
- Skip to end (SkipForward): Ingests ALL events at once, triggers reconsolidation, fetches full graph.
- Speed selector: 4-button pill (0.5x, 1x, 2x, 3x). Auto-play interval = 2000ms / speed.
- Reset (RotateCcw icon): Returns to scenario picker.

**Component(s):** `components/simulator/SimulatorControls.tsx`
**Store(s):** `stores/simulatorStore.ts` (all transport actions)
**Hook:** `hooks/useSimulatorPlayback.ts` (timer driving auto-play)

---

### 5.4 Progress Slider with Step Counter

**Description:** A thin horizontal progress bar showing playback progress. Clickable to jump to any step. Step counter displays current/total (e.g., "5/18") with the current session name.

**UI Location:** Bottom of chat panel, between the pipeline status bar and transport controls.

**Key Interactions:**

- Click anywhere on the progress bar to jump to that proportional step.
- Hover reveals a draggable thumb indicator.
- Blue fill indicates progress percentage.
- Step counter on the left: "{step}/{total}".
- Current session indicator: colored dot + "S1: {title}".

**Component(s):** `components/simulator/SimulatorControls.tsx`
**Store(s):** `stores/simulatorStore.ts` (`currentStepIndex`, `goToStep`)

---

### 5.5 Session Tabs for Multi-Session Scenarios

**Description:** Session tabs in the SimulatorChat top bar. Tabs appear dimmed until a session's messages become visible during playback. Only visible sessions are clickable. Active session is highlighted.

**UI Location:** Top of chat panel in Simulator mode.

**Key Interactions:**

- Tabs for unreached sessions are dimmed (gray dot, faded text).
- Tabs for reached sessions are clickable to view that session's messages.
- Active session has bg-surface-hover and white text.
- Session title shown as truncated text next to the session number.

**Component(s):** `components/simulator/SimulatorChat.tsx`
**Store(s):** `stores/simulatorStore.ts` (`currentSessionId`, `visibleMessagesPerSession`)

---

### 5.6 Pipeline Status Display (C1-C4 Consumer Stats)

**Description:** A compact 4-column grid showing the status of each Engram consumer pipeline stage. Each consumer card shows: active indicator (green dot if producing output), consumer name (C1: Projection, C2: Extraction, C3: Enrichment, C4: Consolidation), description, and output counts (node/edge counts by type).

**UI Location:** Bottom of chat panel, above the transport controls.

**Key Interactions:**

- Green dot + green text for active consumers (have produced output).
- Gray dot + gray text for inactive consumers.
- Output counts shown in colored monospace (Event=blue, Entity=teal, Summary=gray, UserProfile=purple, etc.).
- Edge counts shown in muted text (FOLLOWS, CAUSED_BY, REFERENCES, etc.).
- Stream event counter at top.
- Per-session ingested events counter.

**Component(s):** `components/simulator/PipelineStatus.tsx`
**Store(s):** `stores/simulatorStore.ts` (`pipelineStats`, `ingestedEvents`)

---

### 5.7 Backend Connection Detection and Status Badge

**Description:** A badge in the controls status bar showing backend connection state: "Detecting..." (yellow, spinning loader), "Engram Live" (green, checkmark), or "Backend Offline" (red, warning triangle). Backend detection runs automatically when a scenario is picked.

**UI Location:** SimulatorControls status bar, top-left.

**Key Interactions:**

- Automatic detection on scenario pick via `detectBackend()`.
- If offline, shows error message with startup instructions.
- Transport controls are disabled when backend is not connected.
- Error messages are displayed inline in the status bar.

**Component(s):** `components/simulator/SimulatorControls.tsx`
**Store(s):** `stores/simulatorStore.ts` (`backendConnected`, `detecting`, `lastApiError`)

---

### 5.8 Clear Context Graph (with Confirmation Dialog)

**Description:** A destructive action that replays (rebuilds) the Neo4j graph from scratch via the admin replay endpoint. Requires a two-step confirmation: click "Clear Graph" to reveal "Confirm?" with Yes/No buttons.

**UI Location:** SimulatorControls status bar, right side.

**Key Interactions:**

- Click "Clear Graph" (Trash2 icon, red): Shows confirmation inline.
- Click "Yes": Executes `clearContextGraph()` -- calls `engram.replay()`, clears local graph and user data, resets state.
- Click "No": Cancels and hides confirmation.
- Spinner animation while clearing.
- Disabled when backend is not connected.

**Component(s):** `components/simulator/SimulatorControls.tsx`
**Store(s):** `stores/simulatorStore.ts` (`clearContextGraph`, `isClearing`)

---

### 5.9 Trigger Reconsolidation Button

**Description:** Manually triggers the Consumer 4 (Consolidation) pipeline to create Summary nodes, run forgetting, and detect behavioral patterns. Calls the admin reconsolidate endpoint.

**UI Location:** SimulatorControls status bar, right side (Zap icon, amber).

**Key Interactions:**

- Click "Consolidate" to trigger.
- Shows "Consolidating..." with pulsing Zap icon during execution.
- After completion: waits 500ms, re-fetches graph, re-fetches user data, updates pipeline stats.
- Disabled when: backend not connected, already consolidating, or no nodes exist.

**Component(s):** `components/simulator/SimulatorControls.tsx`
**Store(s):** `stores/simulatorStore.ts` (`triggerReconsolidate`, `isReconsolidating`)

---

### 5.10 Pipeline Stats Refresh

**Description:** A button to manually refresh the pipeline statistics from the backend admin stats endpoint. Also re-fetches the live graph and user data.

**UI Location:** SimulatorControls status bar, right side (RefreshCw icon, blue).

**Key Interactions:**

- Click "Stats" to refresh.
- Fetches `engram.stats()` and updates `pipelineStats` in store.
- Also re-fetches live graph and user data.
- Disabled when backend not connected.

**Component(s):** `components/simulator/SimulatorControls.tsx`
**Store(s):** `stores/simulatorStore.ts` (`refreshPipelineStats`)

---

## Category 6: Dynamic Mode (LLM Two-Agent Conversations)

### 6.1 Quick Start Presets (4 Scenario Pairs)

**Description:** Four pre-configured persona pairs for immediate conversation start: SaaS Billing Dispute (Sarah Chen vs Alex Support), Merchant Chargeback (Marcus Rivera vs Jordan Sr. Agent), Flight Rebooking (Priya Sharma vs Alex Support), API Integration (Marcus Rivera vs Sam Tech Support). Each preset card shows title, description, and both persona avatars.

**UI Location:** Chat panel, PersonaPicker component, "Quick Start" tab.

**Key Interactions:**

- Click a preset card to immediately start with those personas and their default topic.
- Cards show persona avatars side by side with "vs" separator.
- Hover: border turns purple, title text turns purple.

**Component(s):** `components/simulator/PersonaPicker.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`selectPersonas`)
**Data:** `data/personas.ts` (`presetPairs`)

---

### 6.2 Mix & Match Mode

**Description:** Custom persona selection with independent customer dropdown (3 options: Sarah Chen, Marcus Rivera, Priya Sharma), support dropdown (3 options: Alex Support, Jordan Sr. Agent, Sam Tech Support), and a text area for the conversation topic/opening issue. Personas are displayed as clickable grid cards.

**UI Location:** Chat panel, PersonaPicker component, "Mix & Match" tab.

**Key Interactions:**

- Toggle between "Quick Start" and "Mix & Match" tabs via pill toggle.
- Customer grid: 3 persona cards in a 3-column grid with avatar, name, description.
- Support grid: 3 persona cards in a 3-column grid with avatar, name, description.
- Selected persona has purple border and background tint.
- Topic textarea for custom issue description.
- "Start Conversation" button (disabled if topic is empty).
- Selecting a customer auto-fills the topic with that persona's first topic seed.

**Component(s):** `components/simulator/PersonaPicker.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`selectPersonas`)
**Data:** `data/personas.ts` (`customerPersonas`, `supportPersonas`)

---

### 6.3 Max Turns Configuration

**Description:** A numeric input field to set the maximum number of conversation turns (2-50, default 20). Shared between Quick Start and Mix & Match modes.

**UI Location:** PersonaPicker, above the preset/custom sections.

**Key Interactions:**

- Type a number or use browser spinner controls.
- Min=2, Max=50, default=20.
- Value passed to `selectPersonas` when starting.

**Component(s):** `components/simulator/PersonaPicker.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`maxTurns`, `setMaxTurns`)

---

### 6.4 Streaming Token-by-Token Response Display

**Description:** During LLM response generation, tokens stream in real-time via SSE (Server-Sent Events). The partial response is shown in a message bubble with a pulsing purple cursor indicator at the end. Content accumulates token-by-token as the stream progresses.

**UI Location:** Chat panel, streaming message at the bottom of the message list.

**Key Interactions:**

- Tokens appear progressively in the message bubble.
- A pulsing purple cursor block (1.5px wide, 12px tall) indicates streaming is active.
- Persona avatar and name shown on the message.
- Auto-scroll keeps the streaming content visible.
- Completed messages show token count footer.

**Component(s):** `components/simulator/DynamicChat.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`streamingContent`, `streamingPersona`)
**API:** `api/engram.ts` (`simulateTurnStream` async generator)

---

### 6.5 Typing Indicator Animation

**Description:** When an LLM turn is generating but no tokens have arrived yet, a typing indicator shows the active persona's avatar, name ("is typing"), and 3 pulsing dots with staggered animation delays (0, 0.2s, 0.4s).

**UI Location:** Chat panel, below existing messages, shown before streaming begins.

**Key Interactions:**

- Appears when status is "generating" and streamingContent is empty.
- 3 dots with opacity animation [0.3, 1, 0.3] cycling every 1.2s.
- Framer-motion enter/exit animation.
- Also used in SimulatorChat (without persona avatar).

**Component(s):** `components/simulator/DynamicChat.tsx`, `components/simulator/SimulatorChat.tsx` (TypingIndicator)

---

### 6.6 Turn-Based Alternating Conversation

**Description:** Conversations alternate between customer and support personas. Even turns (0, 2, 4...) are customer; odd turns (1, 3, 5...) are support. The LLM sees conversation history with perspective flipping (own messages as "assistant", other's as "user").

**UI Location:** Chat panel messages. Customer messages appear on the left; support messages appear on the right (flex-row-reverse).

**Key Interactions:**

- Customer messages: left-aligned with persona avatar on left, surface-hover background.
- Support messages: right-aligned with persona avatar on right, blue-tinted background.
- Each message shows persona name in their color, content, and optional token count.

**Component(s):** `components/simulator/DynamicChat.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`turnCount`, `messages`)

---

### 6.7 Auto-Play with Configurable Delay

**Description:** Auto-play mode automatically generates the next turn after a configurable delay. Delay options: 1s, 1.5s, 2s, 3s (default 1.5s). The timer fires only when status is "waiting" (after a turn completes and before the next begins).

**UI Location:** DynamicControls, right side delay selector; Play/Pause button in center.

**Key Interactions:**

- Click Play (purple) to start auto-play.
- Click Pause to stop.
- Select delay: 4-button pill with 1s/1.5s/2s/3s options.
- Timer driven by `useDynamicPlayback` hook.
- Active delay option has purple background.

**Component(s):** `components/simulator/DynamicControls.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`isAutoPlaying`, `turnDelayMs`, `startAutoPlay`, `pauseAutoPlay`)
**Hook:** `hooks/useDynamicPlayback.ts`

---

### 6.8 Step-by-Step Manual Advance

**Description:** A "Step" button to manually trigger a single turn without auto-play. Generates the next turn (customer or support based on turn count), streams the response, ingests events, and pauses.

**UI Location:** DynamicControls, center transport section, "Step" button with ChevronRight icon.

**Key Interactions:**

- Click "Step" to generate one turn.
- Disabled during active generation, when complete, or when backend is offline.
- After step completes, status goes to "paused" (not "waiting").

**Component(s):** `components/simulator/DynamicControls.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`generateNextTurn`)

---

### 6.9 End Session Button

**Description:** Manually ends the current conversation session. Sends a system.session_end event to trigger Consumer 2 (Extraction), which creates Entity, UserProfile, Preference, and Skill nodes from the conversation.

**UI Location:** DynamicControls, center transport section, "End" button with Square icon.

**Key Interactions:**

- Click "End" to terminate the session.
- Aborts any in-flight generation.
- Sends session_end event, waits 500ms for extraction consumer.
- Re-fetches graph (may now include Entity nodes from extraction).
- Fetches user data (profile, preferences, skills, interests).
- Updates pipeline stats.
- Sets status to "complete".
- Disabled when: backend offline, already complete, or no turns generated.

**Component(s):** `components/simulator/DynamicControls.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`endSession`)

---

### 6.10 Pipeline Status with Per-Session Ingest Counter

**Description:** Identical PipelineStatus component as Simulator mode, showing C1-C4 consumer stages. Additionally tracks ingested events count specific to the current dynamic session.

**UI Location:** Bottom of chat panel, above DynamicControls.

**Key Interactions:** Same as Category 5.6. Shared PipelineStatus component.

**Component(s):** `components/simulator/PipelineStatus.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`pipelineStats`, `ingestedEvents`)

---

### 6.11 Cross-Session Context Injection

**Description:** The support agent's system prompt is augmented with context retrieved from the Engram graph. Before each support turn, the store queries the user endpoints (getUserPreferences, getUserSkills, getUserInterests) and appends the results as a "CUSTOMER HISTORY" block to the system prompt. This enables the LLM support agent to reference past interactions and provide personalized service.

**UI Location:** Not directly visible in UI, but affects support agent responses. Effect is observable when the support agent references information from previous sessions.

**Key Interactions:**

- Automatic: runs before each support agent turn when backend is connected.
- Queries user:fe-dynamic-sim entity for preferences, skills, and interests.
- Formats results as natural language: "Customer preferences: ...; Customer skills: ...; Customer interests: ...".
- Appended to system prompt with instructions to use context naturally.
- Best-effort: failures are silently ignored (don't block conversation).

**Component(s):** N/A (behavior within store)
**Store(s):** `stores/dynamicSimStore.ts` (`_retrievePastContext`, `generateNextTurn`)
**API:** `api/engram.ts` (`getUserPreferences`, `getUserSkills`, `getUserInterests`)

---

### 6.12 Dynamic Controls -- Pipeline Action Buttons

**Description:** Same pipeline action buttons as Simulator mode: Refresh Stats (blue), Consolidate (amber), and Clear Graph (red with confirmation). Accessible in the DynamicControls status bar.

**UI Location:** DynamicControls status bar, right side.

**Key Interactions:** Same as Simulator mode (5.8, 5.9, 5.10). Uses dynamicSimStore equivalents.

**Component(s):** `components/simulator/DynamicControls.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`clearContextGraph`, `triggerReconsolidate`, `refreshPipelineStats`)

---

### 6.13 Error Recovery (Retry Button)

**Description:** When an LLM generation error occurs, the status bar shows the error message and a "Retry" button. Clicking Retry clears the error and sets status back to "paused", allowing the user to try again.

**UI Location:** DynamicControls status bar, next to the error message.

**Key Interactions:**

- Visible only when status is "error" and lastApiError is set.
- Click "Retry" to dismiss error and return to paused state.
- Accessible with focus-visible ring.

**Component(s):** `components/simulator/DynamicControls.tsx`
**Store(s):** `stores/dynamicSimStore.ts` (`status`, `lastApiError`)

---

## Category 7: Pipeline Integration

### 7.1 Real-Time Event Ingestion to Redis Streams

**Description:** Both Simulator and Dynamic modes ingest events into the real Engram backend via `EngramClient.ingestBatch()`. Events flow into Redis Streams, the immutable event ledger. Each message step generates: observation.input (user messages), agent.invoke (agent messages), tool.execute (tool usage), system.session_start and system.session_end (session lifecycle).

**UI Location:** Not directly visible, but reflected in PipelineStatus stream counter and ingested events counter.

**Key Interactions:**

- Automatic on each step (Simulator) or each turn completion (Dynamic).
- Batch ingestion for efficiency (multiple events per API call).
- Timestamp rebasing in Simulator mode to avoid future-drift rejection.
- `createEvent` and `messageToEvents` helpers generate properly structured EventPayload objects.
- `sessionLifecycleEvents` generates paired start/end events with shared trace_id.

**Component(s):** N/A (store-level integration)
**Store(s):** `stores/simulatorStore.ts`, `stores/dynamicSimStore.ts`
**API:** `api/engram.ts` (`ingestBatch`, `messageToEvents`, `sessionLifecycleEvents`, `rebaseTimestamp`)

---

### 7.2 Consumer 1 -- Projection (Event to Graph Nodes/Edges)

**Description:** The projection consumer reads events from Redis Streams and creates Event nodes with FOLLOWS and CAUSED_BY edges in Neo4j. This is the first pipeline stage. In the frontend, its output is visible as Event node counts and FOLLOWS/CAUSED_BY edge counts in PipelineStatus.

**UI Location:** PipelineStatus C1 card shows Event node count and FOLLOWS/CAUSED_BY edge counts.

**Key Interactions:**

- Runs per-event as events are ingested.
- No LLM required.
- Frontend waits 200ms after ingestion for projection to process before fetching graph.

**Component(s):** `components/simulator/PipelineStatus.tsx` (display)
**Store(s):** `stores/simulatorStore.ts`, `stores/dynamicSimStore.ts` (applyStep timing)

---

### 7.3 Consumer 2 -- Extraction (Session End to Entities/Profile)

**Description:** The extraction consumer triggers on system.session_end events and uses LLM to extract entities, user profile, preferences, skills, and interests from the session's events. Creates Entity, UserProfile, Preference, Skill nodes with REFERENCES, HAS_PROFILE, HAS_PREFERENCE, DERIVED_FROM edges.

**UI Location:** PipelineStatus C2 card shows Entity, UserProfile, Preference, Skill counts and related edge counts.

**Key Interactions:**

- Triggered by session_end event.
- Requires LLM (configured via CG_LLM_MODEL_ID).
- Frontend waits 500ms after session_end for extraction to process.
- After extraction, graph is re-fetched to show new Entity nodes.
- User data (profile, preferences, skills) is fetched and populates the User tab.

**Component(s):** `components/simulator/PipelineStatus.tsx` (display)
**Store(s):** `stores/simulatorStore.ts`, `stores/dynamicSimStore.ts` (post-session-end pipeline)

---

### 7.4 Consumer 3 -- Enrichment (Keywords, Importance, Embeddings)

**Description:** The enrichment consumer processes events to add keywords, importance scores, and (optionally) embeddings. Creates SIMILAR_TO edges between semantically related events. Does not require LLM (uses embedding model).

**UI Location:** PipelineStatus C3 card shows enriched Event count and SIMILAR_TO edge count.

**Key Interactions:**

- Runs per-event-batch.
- Output visible as SIMILAR_TO edges in the graph.
- No direct frontend trigger (runs asynchronously in background).

**Component(s):** `components/simulator/PipelineStatus.tsx` (display)

---

### 7.5 Consumer 4 -- Consolidation (Summaries, Forgetting, Patterns)

**Description:** The consolidation consumer creates Summary nodes, runs forgetting (retention tier enforcement), and detects behavioral patterns. Triggered on schedule (6h) or manually via the "Consolidate" button. Creates Summary and Episode nodes with SUMMARIZES edges.

**UI Location:** PipelineStatus C4 card shows Summary and Episode node counts and SUMMARIZES edge count.

**Key Interactions:**

- Manual trigger via "Consolidate" button in Simulator/Dynamic controls.
- Automatic trigger during skip-to-end in Simulator mode.
- After consolidation: graph re-fetched to show Summary nodes, user data re-fetched.

**Component(s):** `components/simulator/PipelineStatus.tsx` (display), `components/simulator/SimulatorControls.tsx`, `components/simulator/DynamicControls.tsx` (trigger button)
**Store(s):** `stores/simulatorStore.ts` (`triggerReconsolidate`), `stores/dynamicSimStore.ts` (`triggerReconsolidate`)

---

### 7.6 Stream Event Counter

**Description:** The PipelineStatus header displays the total number of events in the Redis Stream (`pipelineStats.streamLength`). This represents the raw event count in the immutable ledger.

**UI Location:** PipelineStatus component header, "Stream: X events".

**Key Interactions:** Display only. Updated on stats refresh.

**Component(s):** `components/simulator/PipelineStatus.tsx`

---

### 7.7 Ingested Events Counter Per Session

**Description:** A running counter showing how many events have been ingested during the current simulator or dynamic session. Displayed both in PipelineStatus and in the SimulatorControls/DynamicControls status bar.

**UI Location:** PipelineStatus header "(X ingested this session)"; also in controls status bar "X ingested".

**Key Interactions:** Display only. Increments on each successful `ingestBatch` call.

**Component(s):** `components/simulator/PipelineStatus.tsx`, `components/simulator/SimulatorControls.tsx`, `components/simulator/DynamicControls.tsx`
**Store(s):** `stores/simulatorStore.ts` (`ingestedEvents`), `stores/dynamicSimStore.ts` (`ingestedEvents`)

---

### 7.8 Graph Auto-Refresh After Ingestion

**Description:** After each event ingestion step, the frontend automatically queries the Engram backend for the updated graph. Uses `querySubgraph` first (returns all node types including Entities, Summaries), falling back to `getContext` if no seed nodes are found. The graph panel updates in place with the new data.

**UI Location:** Graph panel updates automatically after each step.

**Key Interactions:**

- Automatic after ingestion + 200ms delay (for projection consumer).
- Falls back from querySubgraph to getContext on failure.
- Sets graphStore nodes/edges/meta from the Atlas response.
- In Simulator's "All" session filter: merges results from all session queries.

**Component(s):** N/A (store-level integration)
**Store(s):** `stores/simulatorStore.ts` (`fetchLiveGraph`), `stores/dynamicSimStore.ts`
**API:** `api/pipeline.ts` (`fetchLiveGraph`), `api/engram.ts` (`querySubgraph`, `getContext`)

---

## Appendix: Technical Architecture Summary

### Stores (Zustand)

| Store             | File                        | Purpose                                                        |
| ----------------- | --------------------------- | -------------------------------------------------------------- |
| `sessionStore`    | `stores/sessionStore.ts`    | Demo mode playback state, session navigation, auto-play        |
| `graphStore`      | `stores/graphStore.ts`      | Graph nodes/edges, filters, layout, selection, Sigma renderer  |
| `simulatorStore`  | `stores/simulatorStore.ts`  | Simulator scenario state, ingestion, pipeline stats, transport |
| `dynamicSimStore` | `stores/dynamicSimStore.ts` | Dynamic LLM conversation state, streaming, auto-play timer     |
| `userStore`       | `stores/userStore.ts`       | User profile, preferences, skills, interests, patterns         |
| `insightStore`    | `stores/insightStore.ts`    | Active insight tab, debug toggle                               |
| `apiLogStore`     | `stores/apiLogStore.ts`     | API call log for the API tab                                   |

### Hooks

| Hook                    | File                             | Purpose                                 |
| ----------------------- | -------------------------------- | --------------------------------------- |
| `usePlaybackUrl`        | `hooks/usePlaybackUrl.ts`        | Sync demo playback state with URL hash  |
| `useSimulatorPlayback`  | `hooks/useSimulatorPlayback.ts`  | Timer driving simulator auto-play       |
| `useDynamicPlayback`    | `hooks/useDynamicPlayback.ts`    | Timer driving dynamic mode auto-play    |
| `useKeyboardNavigation` | `hooks/useKeyboardNavigation.ts` | Global keyboard shortcuts for demo mode |

### API Layer

| Module         | File              | Purpose                                                                        |
| -------------- | ----------------- | ------------------------------------------------------------------------------ |
| `EngramClient` | `api/engram.ts`   | Full TypeScript SDK for Engram REST API                                        |
| `pipeline`     | `api/pipeline.ts` | Shared utilities: backend detection, stats fetch, graph fetch, user data fetch |
| `mode`         | `api/mode.ts`     | Data mode (mock/live) and sub-mode persistence                                 |

### Type System

| Module  | File             | Key Types                                                                                 |
| ------- | ---------------- | ----------------------------------------------------------------------------------------- |
| `atlas` | `types/atlas.ts` | AtlasResponse, AtlasNode, AtlasEdge, QueryMeta, 11 NodeTypes, 20 EdgeTypes, 8 IntentTypes |
| `graph` | `types/graph.ts` | GraphNode, GraphEdge, NODE_COLORS, EDGE_COLORS                                            |
| `chat`  | `types/chat.ts`  | ChatMessage, Session, ScenarioStep, TraversalStep                                         |

### Data

| Module      | File                | Content                                                                                 |
| ----------- | ------------------- | --------------------------------------------------------------------------------------- |
| `personas`  | `data/personas.ts`  | 3 customer + 3 support personas, 4 preset pairs                                         |
| `scenarios` | `data/scenarios.ts` | 4 full scenarios (Sarah, Marcus, Priya, David) with sessions, messages, atlas snapshots |
