# Agent Research Log (Extended Dataset)

Prior experiments on the original 59-node dataset are archived in `agent_research_log_original.md`. This log tracks optimization on the extended 287-node / 80-query / 10-scenario dataset.

## Cycle 0: BASELINE score=0.6990

**Hypothesis**: Carry forward best config from original dataset optimization (Cycle 17 of prior log).
**Change**: None -- establishing baseline on extended dataset.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.8 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.6990, violation_rate=0.0000, baseline=0.2729 (+156.1%)
**Per-intent nDCG (worst to best)**: RELATED=0.5577, HOW_DOES=0.6364, WHO_IS=0.6441, WHAT=0.6745, PERSONALIZE=0.7119, WHEN=0.7862, GENERAL=0.7868, WHY=0.7949
**Worst queries**: lu-how-does-01 (0.1331), cr-why-01 (0.2038), ar-how_does-01 (0.3184), at-personalize-01 (0.3212), lu-related-01 (0.3985)
**Lesson**: The config tuned on 3 original scenarios transfers reasonably to 10 scenarios (0.6990), but the generated scenarios expose new weaknesses. RELATED, HOW_DOES, and WHO_IS are the primary optimization targets. The worst individual queries are in lending (lu), chargeback (cr), API rate-limit (ar), and account takeover (at) -- all generated scenarios.
