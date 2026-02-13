export interface DecayDataPoint {
  day: number;
  score: number;
}

export interface IntentScore {
  intent: string;
  score: number;
}

export function generateDecayCurve(initialScore: number, importance: number): DecayDataPoint[] {
  const points: DecayDataPoint[] = [];
  const lambda = 0.1 + (10 - importance) * 0.05;
  for (let day = 0; day <= 7; day++) {
    const score = initialScore * Math.exp(-lambda * day);
    points.push({ day, score: Math.round(score * 100) / 100 });
  }
  return points;
}

export const sessionIntents: Record<string, IntentScore[]> = {
  'session-1': [
    { intent: 'what', score: 0.8 },
    { intent: 'why', score: 0.3 },
    { intent: 'how_does', score: 0.2 },
  ],
  'session-2': [
    { intent: 'what', score: 0.6 },
    { intent: 'related', score: 0.5 },
    { intent: 'how_does', score: 0.4 },
    { intent: 'personalize', score: 0.3 },
  ],
  'session-3': [
    { intent: 'why', score: 0.9 },
    { intent: 'what', score: 0.7 },
    { intent: 'related', score: 0.5 },
    { intent: 'who_is', score: 0.4 },
    { intent: 'personalize', score: 0.6 },
  ],
};
