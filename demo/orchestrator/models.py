from pydantic import BaseModel


class ChatRequest(BaseModel):
    session_id: str
    user_message: str
    scenario_id: str


class ChatResponse(BaseModel):
    agent_message: str
    context_used: int
    events_ingested: int
    inferred_intents: dict[str, float] = {}


class ScenarioInfo(BaseModel):
    id: str
    title: str
    subtitle: str
    color: str
    description: str
    persona_name: str
    suggested_opener: str


class SessionCreateRequest(BaseModel):
    scenario_id: str


class SessionCreateResponse(BaseModel):
    session_id: str
    scenario: ScenarioInfo
