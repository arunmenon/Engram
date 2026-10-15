# Pilot model configuration: Luna

User decision: use `gpt-6-luna` and remove the artificial model-call ceiling.

The default extraction, text-generation and optional intent-classification clients now select Luna. Luna requests use `reasoning_effort=none` and `max_completion_tokens`; explicit other-model overrides keep their existing request options. Per-response lengths, timeouts, retries, validation and database ownership checks remain. There is no runner call-count or spend ceiling. Actual provider calls and usage remain recorded.

Three real provider calls passed: text generation, JSON extraction and intent classification. See [provider evidence](luna-provider-smoke.json). This is API compatibility evidence, not proof of extraction quality or a pilot acceptance run. The model returned an additional supported person entity in the JSON smoke response; no exact extraction oracle was claimed.

## Retained tenants

No Spanner data or ownership was changed. Retained tenant policies include the old model in their interpretation digest. Changing the default therefore causes the runner's existing owner-match check to refuse startup. Do not override that check: accepted historical events also pin their processing interpretation. Supported activation/recovery belongs to issue #63, alongside the retained consolidation/preservation conflict exposed by the earlier run.

Earlier attempt records retain their original GPT-5.2 settings and 12-call ceiling as historical evidence. This decision supersedes that ceiling for future attempts. No cloud rerun was performed for this change.
