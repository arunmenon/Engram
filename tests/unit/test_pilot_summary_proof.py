import json

import pytest
from engram_pilot_summary_proof import matching_calls, source_records


def case():
    steps = [
        {
            "request": {
                "event_id": "one",
                "payload": {"content": "Investigation completed; rollout uncertain."},
            }
        },
        {"request": {"event_id": "two", "payload": {"content": "Progress only."}}},
    ]
    records = [
        {
            "event_id": s["request"]["event_id"],
            "source_content": json.dumps(s["request"]["payload"]),
        }
        for s in steps
    ]
    call = {
        "model": "gpt-6-luna",
        "state": "returned",
        "output": "Investigation completed; rollout uncertain.",
        "input_messages": [
            {"role": "user", "content": "Events:\n" + "\n".join(json.dumps(r) for r in records)}
        ],
    }
    return steps, records, call


def test_exact_sources_match():
    steps, records, call = case()
    assert matching_calls([call], steps) == [call]
    assert source_records(call["input_messages"]) == [
        (r["event_id"], json.loads(r["source_content"])) for r in records
    ]


@pytest.mark.parametrize(
    "tamper",
    [
        "extra",
        "duplicate",
        "missing",
        "wrong_content",
        "failed",
        "wrong_model",
        "substring",
        "malformed",
    ],
)
def test_false_provider_source_proofs_rejected(tamper):
    steps, records, call = case()
    if tamper == "extra":
        records.append({"event_id": "foreign", "source_content": "{}"})
    if tamper == "duplicate":
        records.append(records[0])
    if tamper == "missing":
        records.pop()
    if tamper == "wrong_content":
        records[0]["source_content"] = '{"content":"opposite"}'
    if tamper == "failed":
        call["state"] = "failed"
    if tamper == "wrong_model":
        call["model"] = "other"
    if tamper == "substring":
        records = []
    if tamper == "malformed":
        records[0]["source_content"] = "not JSON"
    call["input_messages"][0]["content"] = "\n".join(json.dumps(r) for r in records)
    if tamper == "substring":
        call["input_messages"][0]["content"] = str(steps)
    assert matching_calls([call], steps) == []
