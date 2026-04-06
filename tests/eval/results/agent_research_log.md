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

## Cycle 1: ACCEPTED score=0.7118 (delta=+0.0128 vs Cycle 0)

**Hypothesis**: RELATED queries are mostly scenario-local in the extended dataset, but `scenario_focus` still applies a loose out-of-scenario penalty (`related_cross_scenario_multiplier=0.8`). Tightening that penalty should suppress cross-scenario leakage without affecting non-RELATED intents.
**Change**: Lowered `scenario_focus.related_cross_scenario_multiplier` from `0.8` to `0.5`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7118, weakest intent=HOW_DOES at 0.6364
**Lesson**: This was the right fix for RELATED. RELATED jumped from 0.5577 to 0.6596 with zero violation cost, and the weakest-query list no longer includes a RELATED query. The next bottleneck is HOW_DOES, especially `lu-how-does-01` and `ar-how_does-01`.

## Cycle 2: ACCEPTED score=0.7133 (delta=+0.0015 vs Cycle 1)

**Hypothesis**: The weakest `how_does` queries stay in the correct scenario but miss multi-step workflow nodes, suggesting `edge_boost` is not traversing far enough through event/entity chains. Allowing one extra hop should surface linked process steps before MMR reranking.
**Change**: Added `max_hops=2` to `edge_boost` while keeping the hook order unchanged (`scenario_focus -> negative_similarity -> edge_boost -> mmr_diversity`).
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7133, weakest intent=HOW_DOES at 0.6309
**Lesson**: Deeper traversal improved the overall score, but not by fixing `how_does`. It helped chain-heavy event intents instead (`WHY` rose to 0.8154, `WHEN` to 0.7934, `GENERAL` to 0.7879), while `HOW_DOES` slipped slightly and introduced a tiny violation rate (0.0013). Keep this baseline because the scalar metric improved, but the next cycle still needs to target `how_does` directly.

## Cycle 3: REJECTED score=0.7030 (delta=-0.0103 vs Cycle 2)

**Hypothesis**: `mmr_diversity` looked too aggressive on the weak `how_does` queries, so making it more relevance-heavy should preserve the process-chain nodes already surfaced by deeper `edge_boost`.
**Change**: Set `mmr_diversity.lambda_param=0.85`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity:lambda_param=0.85 --compare-baseline`
**Result**: score=0.7030, weakest intent=WHO_IS at 0.6277
**Lesson**: Softer MMR did improve `HOW_DOES` (0.6309 -> 0.6477), but it cost too much elsewhere: `WHY` fell from 0.8154 to 0.7635, `RELATED` from 0.6596 to 0.6394, and `WHO_IS` from 0.6441 to 0.6277. Keep the Cycle 2 baseline and look for a change that helps `how_does` without dismantling MMR’s gains on other intents.

## Cycle 4: REJECTED score=0.7133 (delta=+0.0000 vs Cycle 2)

**Hypothesis**: The worst `how_does` queries may be suffering from centroid dilution across mixed event/entity gold nodes, so switching `how_does` to the first-node embedding strategy in `harness.py` could sharpen the semantic target.
**Change**: Removed `how_does` from `CENTROID_INTENTS` in `harness.py`, after backing up the file first.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7133, weakest intent=HOW_DOES at 0.6309
**Lesson**: This change had no measurable effect on the accepted config, so it must be discarded. The baseline comparator changed because the default scorer changed too, which confirms the code path executed, but the optimization metric stayed flat. Restored `harness.py` from backup immediately.

## Cycle 5: ACCEPTED score=0.7199 (delta=+0.0066 vs Cycle 2)

**Hypothesis**: `how_does` queries are being over-penalized by a bad semantic signal because the current scorer multiplies relevance by `intent_relevance_bias=4.2` for that intent, even when key explanatory nodes get weak or zero relevance. Removing the extra relevance boost specifically for `how_does` should let graph boosts, importance, and recency contribute more sanely.
**Change**: Removed `how_does` from `INTENT_WEIGHT_MAP` / `INTENT_BIAS_MAP`, so `how_does` no longer gets the extra `intent_relevance_bias` multiplier.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7199, weakest intent=WHO_IS at 0.6441
**Per-intent nDCG**: RELATED=0.6596, WHO_IS=0.6441, WHAT=0.6745, HOW_DOES=0.6839, PERSONALIZE=0.7119, WHEN=0.7934, GENERAL=0.7879, WHY=0.8154
**Lesson**: This directly fixed the bottleneck. `HOW_DOES` jumped from 0.6309 to 0.6839, with `lu-how-does-01` rising from 0.1609 to 0.3816. `ar-how_does-01` is still weak, but the overall balance is much better and the next weakest average intent is now `WHO_IS`.

## Cycle 6: REJECTED score=0.7157 (delta=-0.0042 vs Cycle 5)

**Hypothesis**: The weakest `who_is` queries appear to need more actor/profile context, so increasing `intent_affinity_bias` should raise user-affinity-linked entities, profiles, and actor events for `who_is` and possibly help the weak `personalize` cases too.
**Change**: Raised `intent_affinity_bias` from `1.5` to `2.2`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=2.2 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7157, weakest intent=WHO_IS at 0.6460
**Lesson**: The affinity increase was too blunt. `WHO_IS` improved only slightly (0.6441 -> 0.6460), but `PERSONALIZE` fell sharply (0.7119 -> 0.6759), which more than erased the gain. Keep the Cycle 5 baseline and look for a more `who_is`-specific change.

## Cycle 7: REJECTED score=0.7143 (delta=-0.0056 vs Cycle 5)

**Hypothesis**: `who_is` queries in the extended set often expect actor events as supporting evidence, but `edge_boost` currently treats `who_is` as entity-only and skips event neighbors. Allowing event neighbors for `who_is` might surface the missing actor events without changing other intents.
**Change**: Removed `who_is` from the `entity_focused_intents` set in `hooks.py`, so `edge_boost` no longer skips event neighbors for `who_is`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7143, weakest intent=WHO_IS at 0.5992
**Lesson**: This confirmed the opposite of the hypothesis. Letting `who_is` propagate into event neighbors adds noise rather than useful actor evidence, and `WHO_IS` drops sharply. Restored `hooks.py` from backup immediately and keep the Cycle 5 baseline.

## Cycle 8: REJECTED score=0.6860 (delta=-0.0339 vs Cycle 5)

**Hypothesis**: The weakest `who_is` queries often miss user-profile / preference / skill nodes entirely, so a much larger `node_type_profile_bonus` might let those profile-family nodes compete when their raw semantic similarity is weak.
**Change**: Raised `node_type_profile_bonus` from `1.05` to `2.0`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=2.0 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.6860, weakest intent=RELATED at 0.5570
**Lesson**: The profile bonus is extremely sensitive. It does lift the profile-heavy intents (`WHO_IS` to 0.6767 and `PERSONALIZE` to 0.8496), but it destroys the rest of the ranking distribution and causes broad regressions across `RELATED`, `WHAT`, `HOW_DOES`, `WHEN`, `GENERAL`, and `WHY`. Keep the Cycle 5 baseline and pivot away from blunt profile-family weighting.

## Cycle 9: REJECTED score=0.7168 (delta=-0.0031 vs Cycle 5)

**Hypothesis**: `who_is` queries often need multiple semantically similar nodes about the same actor, so `mmr_diversity` may be the wrong post-processing step for that intent. Skipping MMR for `who_is` could let the redundant-but-correct actor evidence stay together at the top.
**Change**: Modified `mmr_diversity` in `hooks.py` to skip `who_is` in addition to `what`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7168, weakest intent=WHO_IS at 0.6188
**Lesson**: MMR is not the main `who_is` problem. Skipping it actually makes `WHO_IS` worse, so the real issue is upstream scoring, not diversity reranking. Restored `hooks.py` from backup immediately and keep the Cycle 5 baseline.

## Cycle 10: REJECTED score=0.7175 (delta=-0.0024 vs Cycle 5)

**Hypothesis**: The weak `who_is` queries have almost no usable `user_affinity` signal, but their relevant support nodes do carry importance / mention information. Redirecting `who_is`’s boosted factor from `w_user_affinity` to `w_importance` might surface the actor events and linked entities without touching `personalize`.
**Change**: Changed `INTENT_WEIGHT_MAP["who_is"]` from `w_user_affinity` to `w_importance` in `harness.py`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7175, weakest intent=WHO_IS at 0.6244
**Lesson**: This was directionally plausible but still wrong in aggregate. `WHO_IS` remained worse than the Cycle 5 baseline (0.6244 vs 0.6441), so importance weighting alone does not recover the missing actor/profile nodes. Restored `harness.py` from backup immediately.

## Cycle 11: REJECTED score=0.3112 (delta=-0.4087 vs Cycle 5)

**Hypothesis**: Replacing `mmr_diversity` with `rrf` might help weak `who_is` support nodes by injecting importance and recency into the final ranking instead of diversity pressure.
**Change**: Replaced the tail hook `mmr_diversity` with `rrf`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=rrf --compare-baseline`
**Result**: score=0.3112, weakest intent=RELATED at 0.0097
**Lesson**: Full reranker replacement is a non-starter. `rrf` destroys the ranking distribution for `RELATED`, `WHO_IS`, and `PERSONALIZE`, so future work should keep the current MMR-based tail and focus on narrower upstream fixes instead.

## Cycle 12: ACCEPTED score=0.7221 (delta=+0.0022 vs Cycle 5)

**Hypothesis**: After fixing cross-scenario noise and removing the excessive `how_does` relevance bias, the remaining weak `how_does` cases look like graph-propagation misses rather than semantic misses. In particular, their rationales explicitly rely on `REFERENCES` edges from implementation events to supporting entities, so boosting `REFERENCES` for `how_does` should surface the missing explanatory nodes.
**Change**: Added a `how_does`-specific `REFERENCES` multiplier (`2.0`) to `_INTENT_EDGE_MULTIPLIERS` in `hooks.py`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7221, weakest intent=WHO_IS at 0.6441
**Lesson**: This is a successful revisit of intent-aware edge weighting under the new baseline. The narrower `how_does`-specific `REFERENCES` boost improves `HOW_DOES` from 0.6839 to 0.7014, lifts `ar-how_does-01` from 0.2893 to 0.3734, and preserves the rest of the intent distribution. The main remaining bottleneck is still `WHO_IS`, but the current best score is now 0.7221.

## Cycle 13: REJECTED score=0.7220 (delta=-0.0001 vs Cycle 12)

**Hypothesis**: The weak `who_is` queries mostly have zero-valued `user_affinity`, so the extra `intent_affinity_bias` for `who_is` may just be inflating the denominator in the composite score and diluting the useful signals. Removing the extra bias for `who_is` might slightly improve the actor/profile ranking without touching `personalize`.
**Change**: Removed `who_is` from `INTENT_WEIGHT_MAP` / `INTENT_BIAS_MAP`, so `who_is` no longer gets the extra affinity bias.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7220, weakest intent=WHO_IS at 0.6432
**Lesson**: This was very close but still not an improvement. Removing the wasted affinity bias does not meaningfully fix the `who_is` bottleneck, so keep the Cycle 12 baseline and continue looking for a more structural explanation of the missing actor/profile nodes.

## Cycle 14: ACCEPTED score=0.7248 (delta=+0.0027 vs Cycle 12)

**Hypothesis**: The loaded dataset contains identity/profile edge types beyond the original default `edge_boost` weights, and `HAS_PROFILE` is especially important for weak `who_is` queries. Right now unknown edge types fall back to a tiny `0.1` weight, so giving `HAS_PROFILE` a real default weight should let profile-to-identity propagation work.
**Change**: Added `HAS_PROFILE: 1.5` to `EdgeBoostConfig.edge_type_weights` in `hooks.py`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7248, weakest intent=RELATED at 0.6589
**Lesson**: This exposed a real gap in the hook defaults. A proper `HAS_PROFILE` weight improves `WHO_IS` from 0.6441 to 0.6764 and raises the overall score, even though `RELATED`, `PERSONALIZE`, and `WHY` move slightly down. The next bottleneck is now `RELATED`, which likely points at the similarly underweighted `RELATED_TO` edge type.

## Cycle 15: ACCEPTED score=0.7263 (delta=+0.0015 vs Cycle 14)

**Hypothesis**: After fixing `HAS_PROFILE`, the new weakest intent is `RELATED`, and the dataset uses `RELATED_TO` edges extensively for exactly those queries. Since unknown edge types still fall back to `0.1`, giving `RELATED_TO` a real default weight should strengthen relation propagation without touching the rest of the scorer.
**Change**: Added `RELATED_TO: 1.0` to `EdgeBoostConfig.edge_type_weights` in `hooks.py`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7263, weakest intent=WHAT at 0.6704
**Lesson**: This is another real structural improvement. `RELATED` rises from 0.6589 to 0.6797, `WHO_IS` also improves to 0.6942, and the overall score reaches a new best of 0.7263. The next weakest average intent is now `WHAT`.

## Cycle 16: REJECTED score=0.7245 (delta=-0.0018 vs Cycle 15)

**Hypothesis**: The weakest `what` queries also depend heavily on `REFERENCES` edges, so adding a `what`-specific `REFERENCES` multiplier might lift the missing referenced evidence without affecting other intents.
**Change**: Added a `what`-specific `REFERENCES` multiplier (`1.5`) to `_INTENT_EDGE_MULTIPLIERS` in `hooks.py`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7245, weakest intent=WHAT at 0.6561
**Lesson**: The `what` revisit overfit to a couple of bad cases and hurt the average. Even though `cr-what-01` and `lu-what-01` ticked up slightly, the overall `WHAT` intent dropped from 0.6704 to 0.6561, so keep the Cycle 15 baseline and restore `hooks.py` from backup.

## Cycle 17: ACCEPTED score=0.7372 (delta=+0.0109 vs Cycle 15)

**Hypothesis**: The biggest remaining single-query gap is still `at-personalize-01`, and its rationale explicitly depends on `HAS_PREFERENCE` edges. Since unknown edge types still fall back to `0.1`, giving `HAS_PREFERENCE` a real default weight should let the profile-to-preference propagation work properly and may also help profile-heavy `who_is` cases.
**Change**: Added `HAS_PREFERENCE: 1.3` to `EdgeBoostConfig.edge_type_weights` in `hooks.py`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7372, weakest intent=WHAT at 0.6704
**Lesson**: This confirms the broader structural pattern: the extended graph’s identity/preference edge types were materially underweighted. `HAS_PREFERENCE` produces a large overall gain, lifting `WHO_IS` from 0.6942 to 0.7313 and `PERSONALIZE` from 0.6831 to 0.7347 while also improving `at-personalize-01` from 0.3212 to 0.4095. The next weakest average intent remains `WHAT`.

## Cycle 18: REJECTED score=0.7366 (delta=-0.0006 vs Cycle 17)

**Hypothesis**: After the `HAS_PREFERENCE` gain, the remaining gap in `at-personalize-01` may come from missing `skill-*` evidence, so `HAS_SKILL` should be the next profile-family edge type to weight properly.
**Change**: Added `HAS_SKILL: 1.3` to `EdgeBoostConfig.edge_type_weights` in `hooks.py`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7366, weakest intent=RELATED at 0.6677
**Lesson**: `HAS_SKILL` helps the intended slice (`PERSONALIZE` up to 0.7399 and `HOW_DOES` up slightly), but it bleeds enough score from `RELATED`, `WHAT`, and `WHO_IS` to lose overall. Keep the Cycle 17 baseline and do not add `HAS_SKILL`.

## Cycle 19: REJECTED score=0.7354 (delta=-0.0018 vs Cycle 17)

**Hypothesis**: The weak `what` queries still look reference-driven, but the `what`-specific multiplier was too sharp. A smaller global increase to the base `REFERENCES` weight might improve `WHAT` without the intent-specific overfit.
**Change**: Raised the base `REFERENCES` edge weight from `1.2` to `1.4` in `EdgeBoostConfig.edge_type_weights`.
**Command**: `uv run python tests/eval/run_eval.py --dataset=extended --w_relevance=3.2 --w_recency=0.72 --w_importance=0.8 --w_user_affinity=0.78 --intent_relevance_bias=4.2 --intent_affinity_bias=1.5 --intent_recency_bias=1.1 --entity_s_base=720 --entity_s_boost=48 --degree_boost_cap=0.14 --node_type_profile_bonus=1.05 --hook=scenario_focus:cross_scenario_multiplier=0.2,related_cross_scenario_multiplier=0.5 --hook=negative_similarity:penalty_factor=0.2 --hook=edge_boost:boost_factor=0.08,top_n_seeds=6,max_hops=2 --hook=mmr_diversity --compare-baseline`
**Result**: score=0.7354, weakest intent=WHAT at 0.6708
**Lesson**: The global `REFERENCES` increase is too broad. It nudges `WHAT` and `RELATED` up a bit, but the broader rank distribution degrades enough to lose overall. Keep the Cycle 17 baseline and do not raise the base `REFERENCES` weight.
