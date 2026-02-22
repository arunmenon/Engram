import { apiGet, apiPost } from './client';

export interface ScenarioInfo {
  id: string;
  title: string;
  subtitle: string;
  color: string;
  description: string;
  persona_name: string;
  suggested_opener: string;
}

interface SessionCreateResponse {
  session_id: string;
  scenario: ScenarioInfo;
}

interface ChatResponse {
  agent_message: string;
  context_used: number;
  events_ingested: number;
  inferred_intents: Record<string, number>;
}

export async function getScenarios(): Promise<ScenarioInfo[]> {
  return apiGet<ScenarioInfo[]>('/api/scenarios');
}

export async function startSession(
  scenarioId: string,
): Promise<SessionCreateResponse> {
  return apiPost<SessionCreateResponse>('/api/sessions', {
    scenario_id: scenarioId,
  });
}

export async function sendMessage(
  sessionId: string,
  message: string,
  scenarioId: string,
): Promise<ChatResponse> {
  return apiPost<ChatResponse>('/api/chat', {
    session_id: sessionId,
    user_message: message,
    scenario_id: scenarioId,
  });
}
