export interface PatternObservation {
  timestamp: string;
  session_id: string;
  description: string;
  confidence_delta: number;
}

export interface PatternRecommendation {
  action: string;
  rationale: string;
  priority: 'high' | 'medium' | 'low';
}

export type PatternStatus = 'active' | 'emerging' | 'declining';

export interface EnhancedPattern {
  id: string;
  name: string;
  description: string;
  confidence: number;
  status: PatternStatus;
  observations: PatternObservation[];
  confidence_history: Array<{ date: string; confidence: number }>;
  recommendations: PatternRecommendation[];
  session_ids: string[];
}
