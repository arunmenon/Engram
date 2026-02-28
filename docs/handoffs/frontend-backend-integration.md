# Frontend-Backend Integration Plan

> **Status:** DRAFT — pending PRD finalization
> **Created:** 2026-02-13
> **Branch:** demo/fe-shell
> **Revisit when:** PRD for expanded frontend shell scope is complete

## Context

The Engram frontend shell (`demo/frontend/`) is a 4-zone React SPA running on mock data. The FastAPI backend (`src/context_graph/api/`) has a complete REST API but no CORS config and no frontend connection. This plan integrates them with **real interactive chat** — a separate demo orchestrator service drives conversations between simulated user-personas and an LLM-powered agent, with every message flowing through the Context Graph as events.

**Goal:** Users can pick a PayPal-domain scenario (e.g. "Billing Dispute", "Fraud Alert"), chat in real-time, and watch the knowledge graph, context panel, user profile, and API log update live as events are ingested and the graph grows.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend Shell (React SPA on :5173)                            │
│  - Scenario picker → chat input → graph/context/user/API panels │
│  - Calls /api/chat on the orchestrator                          │
│  - Calls /v1/* on the Context Graph API (via Vite proxy)        │
└──────────┬──────────────────────────────┬───────────────────────┘
           │                              │
     POST /api/chat                 GET/POST /v1/*
     POST /api/scenarios            (context, events, users, etc.)
           │                              │
           ▼                              ▼
┌─────────────────────┐    ┌──────────────────────────────────────┐
│ Demo Orchestrator    │───▶│ Context Graph API (FastAPI on :8000) │
│ (FastAPI on :8100)   │    │ - Event ingest (POST /v1/events)     │
│                      │    │ - Context retrieval (GET /v1/context) │
│ Chat loop:           │    │ - Graph query (POST /v1/query)       │
│ 1. Ingest user msg   │    │ - User profile (GET /v1/users)       │
│ 2. Query context     │    │ - Health (GET /v1/health)            │
│ 3. Call LLM          │    └──────────┬──────────┬───────────────┘
│ 4. Ingest agent resp │               │          │
│ 5. Return reply      │           Redis       Neo4j
│                      │          (:6379)     (:7687)
│ Scenarios:           │
│ - PayPal personas    │
│ - System prompts     │
│ - Seed events        │
└──────────────────────┘
```

**Key principle:** The Context Graph API remains a pure context/traceability service. It does NOT own chat orchestration or LLM calls. The demo orchestrator is a separate service that sits above it.

---

## Team Composition (4 agents + team lead)

| Agent | Type | Scope |
|-------|------|-------|
| **backend-infra** | general-purpose | CORS middleware, settings, Vite proxy, Docker Compose, Dockerfiles |
| **orchestrator** | general-purpose | Demo orchestrator service: chat loop, LLM integration, scenario engine, PayPal personas |
| **frontend-api** | general-purpose | API client, transforms, store refactoring (graphStore, new stores), mode management |
| **frontend-ui** | general-purpose | Chat input, scenario picker, loading/error states, component rewiring, mode toggle |
| **Team Lead** | (self) | Task orchestration, quality gate, final verification |

---

## Task Graph

### Wave 1 — Foundation (all parallel, no dependencies)

**T1: Add CORS to backend + Vite proxy** — `backend-infra`
- `src/context_graph/settings.py` — add `cors_origins: list[str]` field (default: `["http://localhost:5173"]`)
- `src/context_graph/api/middleware.py` — add `CORSMiddleware` in `register_middleware()`
- `demo/frontend/vite.config.ts` — add proxy: `/v1` → `:8000`, `/api` → `:8100`

**T2: Create demo orchestrator service** — `orchestrator`
- New directory: `demo/orchestrator/`
- Files:
  - `demo/orchestrator/app.py` — FastAPI app (port 8100)
  - `demo/orchestrator/chat.py` — chat loop: ingest user event → query context → call LLM → ingest agent event → return
  - `demo/orchestrator/llm.py` — litellm wrapper (configurable model via env: `DEMO_LLM_MODEL`)
  - `demo/orchestrator/scenarios.py` — scenario loader (reads JSON files)
  - `demo/orchestrator/models.py` — Pydantic models for chat request/response
  - `demo/orchestrator/requirements.txt` — fastapi, uvicorn, litellm, httpx

**T3: Create PayPal-domain scenarios** — `orchestrator`
- New directory: `demo/orchestrator/scenarios/`
- JSON scenario files:
  - `billing_dispute.json` — Duplicate charge, refund request (persona: frustrated customer)
  - `payment_failure.json` — Card declined, retry flow (persona: confused user)
  - `fraud_alert.json` — Suspicious transaction, account security (persona: alarmed account holder)
  - `merchant_dispute.json` — Chargeback, seller complaint (persona: small business owner)
  - `account_support.json` — Profile update, payment method management (persona: new user)
- Each scenario includes:
  ```json
  {
    "id": "billing_dispute",
    "title": "Billing Dispute",
    "description": "Customer charged twice for a subscription",
    "persona": {
      "name": "Sarah Chen",
      "role": "Engineering Team Lead",
      "style": "Direct, technical, time-pressured"
    },
    "agent_system_prompt": "You are a PayPal support agent. Use the context graph...",
    "seed_events": [],
    "suggested_opener": "Hi, I was charged twice for my subscription this month."
  }
  ```

**T4: Create frontend API client + transforms** — `frontend-api`
- New files:
  - `demo/frontend/src/api/client.ts` — typed fetch wrapper (`apiGet<T>`, `apiPost<T>`), `ApiError` class, request interceptor for API log
  - `demo/frontend/src/api/transforms.ts` — `transformAtlasResponse()` → `{ GraphNode[], GraphEdge[] }`, label/color/size derivation
  - `demo/frontend/src/api/mode.ts` — `getDataMode()` / `setDataMode()` backed by localStorage (`'mock'` | `'live'`)
  - `demo/frontend/src/api/orchestrator.ts` — typed client for the orchestrator (`sendMessage()`, `getScenarios()`, `startSession()`)

**T5: Docker Compose + Dockerfiles** — `backend-infra`
- `docker/Dockerfile.api` — Python 3.12 slim + uvicorn for Context Graph API
- `docker/Dockerfile.orchestrator` — Python 3.12 slim for demo orchestrator
- `docker/docker-compose.yml` — add `api` (port 8000) and `orchestrator` (port 8100) services (existing redis/neo4j untouched)

### Wave 2 — Store Refactoring + Orchestrator Endpoints (depends on Wave 1)

**T6: Refactor graphStore for async** — `frontend-api` (depends on T4)
- File: `demo/frontend/src/stores/graphStore.ts`
- Add: `loading`, `error`, `lastAtlasMeta: QueryMeta | null`
- Add actions: `fetchSessionContext(sessionId)`, `fetchSubgraph(query, sessionId, agentId)`
- Mock mode: keep existing mock data; Live mode: fetch from API → transform → set

**T7: Create apiLogStore + userStore** — `frontend-api` (depends on T4)
- `demo/frontend/src/stores/apiLogStore.ts` — captures real API calls from client interceptor (mock mode: pre-populated with mockApiCalls)
- `demo/frontend/src/stores/userStore.ts` — `fetchUserData(userId)` → parallel fetch of profile/preferences/skills/interests/patterns (mock mode: pre-populated from mockUserProfile)

**T8: Create chatStore** — `frontend-api` (depends on T4)
- New file: `demo/frontend/src/stores/chatStore.ts`
- State: `scenarios[]`, `activeScenario`, `sessionId`, `messages[]`, `isStreaming`, `error`
- Actions:
  - `fetchScenarios()` — GET `/api/scenarios` from orchestrator
  - `startScenario(scenarioId)` — POST `/api/sessions` → creates session, seeds events, returns sessionId
  - `sendMessage(content)` — POST `/api/chat` → sends user message, gets agent reply, appends both to messages
  - `resetChat()` — clear messages, start fresh session
- Each `sendMessage` also triggers `graphStore.fetchSessionContext()` to refresh the graph

**T9: Orchestrator endpoints** — `orchestrator` (depends on T2, T3)
- `GET /api/scenarios` — list available scenarios
- `POST /api/sessions` — start a new session (create session_id, optionally ingest seed events)
- `POST /api/chat` — the chat loop:
  ```
  Request:  { session_id, user_message, scenario_id }
  Response: { agent_message, context_used: { node_count, intent_scores }, events_ingested: 2 }
  ```
  Internal flow:
  1. Build user event → POST /v1/events (to Context Graph)
  2. GET /v1/context/{session_id}?query={user_message} (retrieve context)
  3. Call LLM with: system prompt (from scenario) + context (from graph) + user message
  4. Build agent event → POST /v1/events (to Context Graph)
  5. Return agent message + metadata

### Wave 3 — Component Updates (depends on Wave 2)

**T10: Scenario picker + chat input** — `frontend-ui` (depends on T8)
- `demo/frontend/src/components/chat/ScenarioPicker.tsx` (new) — modal/drawer with scenario cards showing title, description, persona. Shown when no active scenario.
- `demo/frontend/src/components/chat/ChatInput.tsx` (edit) — enable the input, wire to `chatStore.sendMessage()`, show streaming indicator
- `demo/frontend/src/components/chat/ChatPanel.tsx` (edit) — when in Live mode, render ScenarioPicker if no active scenario, then render real messages from chatStore; Demo mode unchanged (uses sessionStore)

**T11: Rewire insight panels** — `frontend-ui` (depends on T6, T7)
- `ApiTab.tsx` — switch from `mockApiCalls` to `useApiLogStore(s => s.calls)`
- `UserTab.tsx` — switch from static mock imports to `useUserStore()`
- `ContextTab.tsx` — use `lastAtlasMeta` from graphStore for real intents + timing

**T12: Mode toggle + loading/error states** — `frontend-ui` (depends on T6, T7)
- `Header.tsx` — add Demo/Live toggle pill + health indicator (green/red dot via `/v1/health` polling)
- `GraphPanel.tsx` — add loading overlay + error banner
- New shared components: `LoadingOverlay.tsx`, `ErrorBanner.tsx`

### Wave 4 — Quality Gate (depends on all above)

**T13: Quality gate** — Team Lead
- Backend: `ruff check src/`, `ruff format --check src/`, `mypy src/context_graph/`, `pytest tests/unit`
- Orchestrator: basic smoke test (start service, call `/api/scenarios`, verify response)
- Frontend: `cd demo/frontend && npx tsc -b && npx vite build`
- E2E: start all services → pick scenario → send message → verify graph updates + API log fills

---

## Dependency DAG

```
T1 (CORS + proxy) ───────────────────────────────────────────────────────┐
T2 (Orchestrator service) ──┬── T9 (Orchestrator endpoints) ────────────┤
T3 (PayPal scenarios)  ─────┘                                           │
T4 (API client + transforms) ──┬── T6 (graphStore async) ──┐            │
                                ├── T7 (apiLog + userStore) ├── T11 ────┤
                                └── T8 (chatStore) ─────────┤── T10 ────┤── T13 (Quality)
T5 (Docker) ────────────────────────────────────────────────┤── T12 ────┘
                                                             └──────────┘
```

**Critical path:** T4 → T8 → T10 → T13
**Parallel path:** T2 → T9 (orchestrator), T1 (CORS), T5 (Docker)

---

## Demo Orchestrator Design (`demo/orchestrator/`)

### Chat Loop Detail

```python
# demo/orchestrator/chat.py (pseudocode)

async def handle_chat(session_id: str, user_message: str, scenario: Scenario) -> ChatResponse:
    # 1. Ingest user message as event
    user_event = build_event(
        event_type="observation.input",
        session_id=session_id,
        agent_id=scenario.persona.name,
        payload={"content": user_message, "role": "user"},
    )
    await context_graph_client.ingest_event(user_event)

    # 2. Query context graph for relevant context
    atlas = await context_graph_client.get_session_context(
        session_id=session_id,
        query=user_message,
        max_nodes=50,
    )

    # 3. Build LLM prompt with context
    context_text = format_atlas_as_context(atlas)
    messages = [
        {"role": "system", "content": scenario.agent_system_prompt},
        {"role": "system", "content": f"Relevant context from the knowledge graph:\n{context_text}"},
        # ... conversation history ...
        {"role": "user", "content": user_message},
    ]

    # 4. Call LLM
    agent_reply = await llm_client.chat(messages, model=settings.llm_model)

    # 5. Ingest agent response as event
    agent_event = build_event(
        event_type="agent.invoke",
        session_id=session_id,
        agent_id="support-agent",
        payload={"content": agent_reply, "role": "agent"},
        parent_event_id=user_event.event_id,
    )
    await context_graph_client.ingest_event(agent_event)

    # 6. Return response
    return ChatResponse(
        agent_message=agent_reply,
        context_used=len(atlas.nodes),
        events_ingested=2,
        inferred_intents=atlas.meta.inferred_intents,
    )
```

### LLM Configuration
- Uses `litellm` for model-agnostic LLM calls
- Configured via env: `DEMO_LLM_MODEL=claude-sonnet-4-5-20250929` (default)
- API key via: `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` depending on model
- Falls back gracefully with error message if no key configured

---

## PayPal-Domain Scenarios

### Scenario 1: Billing Dispute
```json
{
  "id": "billing_dispute",
  "title": "Billing Dispute",
  "subtitle": "Duplicate charge on subscription",
  "color": "#3b82f6",
  "persona": {
    "name": "Sarah Chen",
    "role": "Engineering Team Lead",
    "tech_level": "Advanced",
    "communication_style": "Direct, technical, values efficiency"
  },
  "agent_system_prompt": "You are a PayPal customer support agent specializing in billing...",
  "suggested_opener": "Hi, I was charged twice for my team's Pro subscription this month — $49.99 on March 1st and again on March 3rd.",
  "seed_events": []
}
```

### Scenario 2: Payment Failure
- Persona: Alex Rivera, freelance designer, moderate tech level
- Issue: Card declined on invoice payment, needs alternative
- System prompt: focus on payment methods, troubleshooting

### Scenario 3: Fraud Alert
- Persona: Michael Torres, small business owner, low tech level
- Issue: Unauthorized transaction, account security concern
- System prompt: prioritize security, escalation to fraud team

### Scenario 4: Merchant Dispute
- Persona: Priya Patel, online store owner, moderate tech level
- Issue: Customer filed chargeback, needs resolution
- System prompt: seller-side support, evidence gathering

### Scenario 5: Account Support
- Persona: Jordan Kim, new user, basic tech level
- Issue: Setting up business account, adding payment methods
- System prompt: onboarding guidance, step-by-step help

---

## Frontend Chat Flow (Live Mode)

```
1. User opens app → sees ScenarioPicker (grid of 5 scenario cards)
2. User picks "Billing Dispute" → chatStore.startScenario("billing_dispute")
   - Orchestrator creates session, optionally seeds events
   - Frontend shows suggested opener in chat input
3. User sends message → chatStore.sendMessage(text)
   - POST /api/chat to orchestrator
   - While waiting: "Agent is typing..." indicator
   - On response: append both user + agent messages
   - Trigger graphStore.fetchSessionContext() → graph re-renders with new nodes
   - API log updates in real-time (intercepted calls)
4. User profile / preferences build up as conversation progresses
   - Orchestrator can trigger extraction after session milestones
   - UserTab refreshes periodically or on demand
5. User can "Reset" to pick a new scenario or "Continue" for multi-turn
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Chat orchestration location | Separate Python demo service | Keeps Context Graph API pure; LLM keys server-side |
| LLM provider | litellm (model-agnostic) | Supports Claude, OpenAI, others via single API |
| Data mode | Demo (mock) / Live (API) toggle | Preserves existing demo experience; Live mode requires services |
| AtlasNode → GraphNode | Transform layer in `transforms.ts` | Bridges backend schema to rendering requirements |
| Vite proxy + CORS | Both | Proxy for dev, CORS for production |
| Graph refresh | On-action (after each message) | No polling; natural fit for request-response |
| Scenario storage | JSON files in repo | Easy to version, modify, and extend |

---

## Files Changed/Created Summary

### Context Graph Backend (Python) — minimal changes
| File | Action | Scope |
|------|--------|-------|
| `src/context_graph/settings.py` | EDIT | Add `cors_origins` field |
| `src/context_graph/api/middleware.py` | EDIT | Add `CORSMiddleware` |
| `docker/docker-compose.yml` | EDIT | Add `api` + `orchestrator` services |
| `docker/Dockerfile.api` | CREATE | Backend container |

### Demo Orchestrator (Python) — new service
| File | Action |
|------|--------|
| `demo/orchestrator/app.py` | CREATE — FastAPI app, CORS, routes |
| `demo/orchestrator/chat.py` | CREATE — chat loop (ingest → context → LLM → ingest) |
| `demo/orchestrator/llm.py` | CREATE — litellm wrapper |
| `demo/orchestrator/models.py` | CREATE — Pydantic request/response models |
| `demo/orchestrator/scenarios.py` | CREATE — scenario loader |
| `demo/orchestrator/context_graph_client.py` | CREATE — httpx client for the CG API |
| `demo/orchestrator/requirements.txt` | CREATE — dependencies |
| `demo/orchestrator/Dockerfile` | CREATE — container |
| `demo/orchestrator/scenarios/*.json` | CREATE — 5 PayPal-domain scenario files |

### Frontend (TypeScript/React)
| File | Action | Scope |
|------|--------|-------|
| `demo/frontend/vite.config.ts` | EDIT | Add proxy: `/v1` → :8000, `/api` → :8100 |
| `demo/frontend/src/api/client.ts` | CREATE | Typed fetch wrapper + interceptor |
| `demo/frontend/src/api/transforms.ts` | CREATE | AtlasResponse → GraphNode/GraphEdge |
| `demo/frontend/src/api/mode.ts` | CREATE | Data mode manager (mock/live) |
| `demo/frontend/src/api/orchestrator.ts` | CREATE | Orchestrator client (chat, scenarios) |
| `demo/frontend/src/stores/graphStore.ts` | EDIT | Add async actions, loading/error, lastAtlasMeta |
| `demo/frontend/src/stores/chatStore.ts` | CREATE | Scenarios, active session, messages, sendMessage |
| `demo/frontend/src/stores/apiLogStore.ts` | CREATE | Live API call log |
| `demo/frontend/src/stores/userStore.ts` | CREATE | User profile/prefs/skills from API |
| `demo/frontend/src/components/chat/ScenarioPicker.tsx` | CREATE | Scenario selection UI |
| `demo/frontend/src/components/chat/ChatInput.tsx` | EDIT | Enable real input, wire to chatStore |
| `demo/frontend/src/components/chat/ChatPanel.tsx` | EDIT | Live mode: chatStore; Demo mode: sessionStore |
| `demo/frontend/src/components/insight/ApiTab.tsx` | EDIT | Switch to apiLogStore |
| `demo/frontend/src/components/insight/UserTab.tsx` | EDIT | Switch to userStore |
| `demo/frontend/src/components/insight/ContextTab.tsx` | EDIT | Use lastAtlasMeta |
| `demo/frontend/src/components/layout/Header.tsx` | EDIT | Mode toggle + health indicator |
| `demo/frontend/src/components/graph/GraphPanel.tsx` | EDIT | Loading overlay + error banner |
| `demo/frontend/src/components/shared/LoadingOverlay.tsx` | CREATE | Reusable loading spinner |
| `demo/frontend/src/components/shared/ErrorBanner.tsx` | CREATE | Dismissible error banner |

---

## Verification

1. **Backend:** `ruff check src/ && mypy src/context_graph/ && pytest tests/unit`
2. **Frontend:** `cd demo/frontend && npx tsc -b && npx vite build`
3. **Orchestrator:** Start service, `curl localhost:8100/api/scenarios` → verify 5 scenarios returned
4. **E2E Integration:**
   - Start infra: `docker compose up -d redis neo4j`
   - Start CG API: `uvicorn context_graph.api.app:create_app --factory --port 8000`
   - Start orchestrator: `uvicorn demo.orchestrator.app:create_app --factory --port 8100`
   - Start frontend: `cd demo/frontend && npm run dev`
   - Open http://localhost:5173 → toggle to Live mode → verify green health dot
   - Pick "Billing Dispute" scenario → send the suggested opener
   - Verify: agent responds, graph shows new Event nodes + FOLLOWS edges, API tab logs real calls
   - Send 2-3 more messages → verify graph grows, context panel updates intents
   - Switch to Demo mode → verify mock data reappears unchanged

---

## Risk Mitigations

| Risk | Mitigation |
|------|------------|
| No LLM API key configured | Orchestrator returns clear error: "Set ANTHROPIC_API_KEY env var". Frontend shows error banner. Demo mode always works. |
| Backend not running | Live mode health dot turns red. Error banner shown. Demo mode unaffected. |
| Type mismatches (API vs frontend) | Transform layer explicitly maps all fields. No raw API types leak into components. |
| Slow LLM responses | "Agent is typing..." indicator. Frontend remains interactive during wait. |
| Docker changes breaking infra | Only adding new services; existing redis/neo4j untouched. |
| Orchestrator → CG API connection | Uses httpx async client with configurable base URL and retry logic. |
