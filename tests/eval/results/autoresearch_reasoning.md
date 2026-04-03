# Autoresearch Log — 2026-03-16T09:05:40.032642+00:00

## Baseline: 0.5183

# Autoresearch Log — 2026-03-16T09:06:30.696887+00:00

## Baseline: 0.5183

## Cycle 1 — ACCEPTED (score=0.5684)

**Changed:** ['w_relevance', 'w_user_affinity', 'intent_relevance_bias', 'intent_affinity_bias', 'node_type_profile_bonus', 'entity_s_base', 'entity_s_boost', 'w_importance', 'degree_boost_coeff', 'degree_boost_cap']

### LLM Reasoning:

```json
{
  "w_relevance": 2.2,
  "w_user_affinity": 1.1,
  "intent_relevance_bias": 2.6,
  "intent_affinity_bias": 2.2,
  "node_type_profile_bonus": 1.35,
  "entity_s_base": 720.0,
  "entity_s_boost": 48.0,
  "w_importance": 0.85,
  "degree_boost_coeff": 0.08,
  "degree_boost_cap": 0.25
}
```

---

## Cycle 2 — REJECTED (score=0.5504)

**Changed:** ['w_recency', 'w_relevance', 'w_user_affinity', 'intent_relevance_bias', 'intent_affinity_bias', 'node_type_profile_bonus', 'node_type_event_bonus', 'access_boost_coeff', 'access_boost_cap']

### LLM Reasoning:

```json
{
  "w_recency": 0.8,
  "w_relevance": 2.5,
  "w_user_affinity": 1.25,
  "intent_relevance_bias": 3.2,
  "intent_affinity_bias": 2.8,
  "node_type_profile_bonus": 1.5,
  "node_type_event_bonus": 0.92,
  "access_boost_coeff": 0.035,
  "access_boost_cap": 0.14
}
```

---

## Cycle 3 — REJECTED (score=0.5595)

**Changed:** ['w_recency', 'w_importance', 'w_relevance', 'w_user_affinity', 'intent_relevance_bias', 'intent_affinity_bias', 'node_type_profile_bonus', 'entity_s_base']

### LLM Reasoning:

```json
{
  "w_recency": 0.85,
  "w_importance": 0.75,
  "w_relevance": 2.45,
  "w_user_affinity": 1.0,
  "intent_relevance_bias": 2.9,
  "intent_affinity_bias": 2.0,
  "node_type_profile_bonus": 1.45,
  "entity_s_base": 900.0
}
```

---

## Cycle 4 — ACCEPTED (score=0.5796)

**Changed:** ['w_recency', 'w_relevance', 'w_user_affinity', 'intent_relevance_bias', 'intent_affinity_bias', 'node_type_profile_bonus', 'intent_recency_bias']

### LLM Reasoning:

```json
{
  "w_recency": 0.8,
  "w_relevance": 2.5,
  "w_user_affinity": 1.0,
  "intent_relevance_bias": 3.0,
  "intent_affinity_bias": 2.0,
  "node_type_profile_bonus": 1.25,
  "intent_recency_bias": 1.2
}
```

---

## Cycle 5 — REJECTED (score=0.5790)

**Changed:** ['w_relevance', 'w_user_affinity', 'intent_relevance_bias', 'node_type_profile_bonus', 'intent_affinity_bias', 'w_importance']

### LLM Reasoning:

```json
{
  "w_relevance": 2.8,
  "w_user_affinity": 0.9,
  "intent_relevance_bias": 3.4,
  "node_type_profile_bonus": 1.18,
  "intent_affinity_bias": 1.8,
  "w_importance": 0.8
}
```

---

## Cycle 6 — ACCEPTED (score=0.5828)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'degree_boost_coeff', 'degree_boost_cap']

### LLM Reasoning:

```json
{
  "w_relevance": 2.7,
  "intent_relevance_bias": 3.4,
  "w_user_affinity": 0.9,
  "intent_affinity_bias": 1.8,
  "node_type_profile_bonus": 1.2,
  "degree_boost_coeff": 0.06,
  "degree_boost_cap": 0.2
}
```

---

## Cycle 7 — ACCEPTED (score=0.5875)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'w_recency', 'intent_recency_bias', 'degree_boost_coeff', 'degree_boost_cap']

### LLM Reasoning:

```json
{
  "w_relevance": 3.0,
  "intent_relevance_bias": 3.8,
  "w_user_affinity": 0.82,
  "intent_affinity_bias": 1.6,
  "node_type_profile_bonus": 1.1,
  "w_recency": 0.72,
  "intent_recency_bias": 1.1,
  "degree_boost_coeff": 0.05,
  "degree_boost_cap": 0.16
}
```

---

## Cycle 8 — ACCEPTED (score=0.5897)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'w_importance', 'degree_boost_cap']

### LLM Reasoning:

```json
{
  "w_relevance": 3.2,
  "intent_relevance_bias": 4.2,
  "w_user_affinity": 0.78,
  "intent_affinity_bias": 1.5,
  "node_type_profile_bonus": 1.05,
  "w_importance": 0.8,
  "degree_boost_cap": 0.14
}
```

---

## Cycle 9 — REJECTED (score=0.5891)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'w_importance', 'degree_boost_cap']

### LLM Reasoning:

```json
{
  "w_relevance": 3.35,
  "intent_relevance_bias": 4.5,
  "w_user_affinity": 0.72,
  "intent_affinity_bias": 1.4,
  "node_type_profile_bonus": 1.0,
  "w_importance": 0.76,
  "degree_boost_cap": 0.12
}
```

---

## Cycle 10 — REJECTED (score=0.5891)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'w_importance', 'degree_boost_cap']

### LLM Reasoning:

```json
{
  "w_relevance": 3.35,
  "intent_relevance_bias": 4.45,
  "w_user_affinity": 0.72,
  "intent_affinity_bias": 1.4,
  "node_type_profile_bonus": 1.0,
  "w_importance": 0.76,
  "degree_boost_cap": 0.12
}
```

---

## Cycle 11 — REJECTED (score=0.5868)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'w_recency']

### LLM Reasoning:

```json
{
  "w_relevance": 3.0,
  "intent_relevance_bias": 4.6,
  "w_user_affinity": 0.72,
  "intent_affinity_bias": 1.7,
  "node_type_profile_bonus": 1.1,
  "w_recency": 0.68
}
```

---

## Cycle 12 — REJECTED (score=0.5891)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'w_importance']

### LLM Reasoning:

```json
{
  "w_relevance": 3.35,
  "intent_relevance_bias": 4.45,
  "w_user_affinity": 0.74,
  "intent_affinity_bias": 1.35,
  "node_type_profile_bonus": 1.0,
  "w_importance": 0.76
}
```

---

## Cycle 13 — REJECTED (score=0.5891)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'w_importance', 'degree_boost_cap']

### LLM Reasoning:

```json
{
  "w_relevance": 3.35,
  "intent_relevance_bias": 4.5,
  "w_user_affinity": 0.72,
  "intent_affinity_bias": 1.4,
  "node_type_profile_bonus": 1.0,
  "w_importance": 0.76,
  "degree_boost_cap": 0.12
}
```

---

## Cycle 14 — REJECTED (score=0.5877)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus', 'node_type_event_bonus']

### LLM Reasoning:

```json
{
  "w_relevance": 3.0,
  "intent_relevance_bias": 4.6,
  "w_user_affinity": 0.72,
  "intent_affinity_bias": 1.7,
  "node_type_profile_bonus": 1.1,
  "node_type_event_bonus": 0.95
}
```

---

## Cycle 15 — REJECTED (score=0.5889)

**Changed:** ['w_relevance', 'intent_relevance_bias', 'w_user_affinity', 'intent_affinity_bias', 'node_type_profile_bonus']

### LLM Reasoning:

```json
{
  "w_relevance": 3.05,
  "intent_relevance_bias": 4.45,
  "w_user_affinity": 0.74,
  "intent_affinity_bias": 1.65,
  "node_type_profile_bonus": 1.08
}
```

---

