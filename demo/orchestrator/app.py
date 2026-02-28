import os
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .chat import handle_chat
from .models import (
    ChatRequest,
    ChatResponse,
    ScenarioInfo,
    SessionCreateRequest,
    SessionCreateResponse,
)
from .scenarios import get_scenario, load_scenarios

# Configurable CORS origins via env var (comma-separated)
_DEFAULT_CORS_ORIGINS = "http://localhost:5173,http://localhost:3000"


def create_app() -> FastAPI:
    app = FastAPI(title="Engram Demo Orchestrator", version="0.1.0")
    cors_origins = os.environ.get("CORS_ORIGINS", _DEFAULT_CORS_ORIGINS)
    allowed_origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/scenarios", response_model=list[ScenarioInfo])
    async def list_scenarios():
        scenarios = load_scenarios()
        return [
            ScenarioInfo(
                id=s["id"],
                title=s["title"],
                subtitle=s.get("subtitle", ""),
                color=s.get("color", "#3b82f6"),
                description=s.get("description", ""),
                persona_name=s["persona"]["name"],
                suggested_opener=s.get("suggested_opener", ""),
            )
            for s in scenarios
        ]

    @app.post("/api/sessions", response_model=SessionCreateResponse)
    async def create_session(req: SessionCreateRequest):
        scenario = get_scenario(req.scenario_id)
        if not scenario:
            raise HTTPException(status_code=404, detail="Scenario not found")
        session_id = f"live-{uuid.uuid4().hex[:8]}"
        return SessionCreateResponse(
            session_id=session_id,
            scenario=ScenarioInfo(
                id=scenario["id"],
                title=scenario["title"],
                subtitle=scenario.get("subtitle", ""),
                color=scenario.get("color", "#3b82f6"),
                description=scenario.get("description", ""),
                persona_name=scenario["persona"]["name"],
                suggested_opener=scenario.get("suggested_opener", ""),
            ),
        )

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(req: ChatRequest):
        return await handle_chat(req.session_id, req.user_message, req.scenario_id)

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    return app
