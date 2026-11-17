"""Sample observations do not infer business identity or repair missing evidence."""

import json

import pytest

from context_graph.workbench.authoring import evidence
from context_graph.workbench.models import Content, Source


@pytest.mark.parametrize("event", ["crm.contact.updated", "purchase.approved"])
def test_inventory_counts_missing_empty_repeats_without_changing_sources(event):
    content = Content(
        name="Intake",
        environment="test",
        sources=[
            Source(
                id="events",
                kind="samples",
                name="Examples",
                text=json.dumps(
                    [
                        {
                            "event_type": event,
                            "payload": {
                                "account": "east",
                                "id": "42",
                                "total": 0,
                                "approved": False,
                            },
                        },
                        {
                            "event_type": event,
                            "payload": {
                                "account": "west",
                                "id": "42",
                                "total": None,
                                "approved": True,
                            },
                        },
                        {
                            "event_type": event,
                            "payload": {"account": "east", "id": "43", "title": ""},
                        },
                    ]
                ),
            )
        ],
    )
    before = content.model_dump()
    inventory = evidence(content)
    assert inventory["events"] == [{"event_type": event, "count": 3}]
    records = inventory["sample_records"]
    repeated = [r for r in records if r["payload"]["id"] == "42"]
    assert [r["payload"]["account"] for r in repeated] == ["east", "west"]
    assert [r["number"] for r in repeated] == [1, 2]
    assert all(r["source_name"] == "Examples" for r in repeated)
    fields = {item["field"]: item for item in inventory["fields"]}
    assert fields["id"]["distinct"] == 2 and fields["id"]["repeated"] == 1
    assert fields["total"]["missing"] == 1 and fields["total"]["empty"] == 1
    assert fields["approved"]["empty"] == 0
    assert "not a global key guarantee" in inventory["note"]
    assert content.model_dump() == before


def test_inventory_does_not_treat_documents_or_schemas_as_samples():
    content = Content(
        name="Intake",
        environment="test",
        sources=[
            Source(
                id="spec", kind="specification", name="Rules", text="Identity is scoped by account."
            ),
            Source(id="schema", kind="schema", name="Schema", text='{"type":"object"}'),
        ],
    )
    assert evidence(content)["sample_count"] == 0
    assert evidence(content)["events"] == []


@pytest.mark.asyncio
async def test_author_receives_real_pattern_contract_and_business_clarification_rules(monkeypatch):
    from types import SimpleNamespace

    import regex

    from context_graph.workbench.authoring import ModelAuthor

    calls = []

    async def completion(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=json.dumps(
                            {
                                "summary": "The supplier connection is not described yet.",
                                "pack": None,
                                "decisions": [
                                    {
                                        "id": "supplier",
                                        "question": "Which source connects requests and suppliers?",
                                        "effect": "Supplier answers need that connection.",
                                    }
                                ],
                            }
                        )
                    )
                )
            ]
        )

    monkeypatch.setattr("litellm.acompletion", completion)
    result = await ModelAuthor("test")(Content(name="Intake", environment="test"))
    capability = json.loads(calls[0]["messages"][1]["content"])["engine_capabilities"][
        "retrieval_key_patterns"
    ]
    pattern = regex.compile(capability["example"])
    assert pattern.search("request R42").group(1) == "R42"
    assert pattern.search("") is None
    assert "LAST field" in capability["lookup"]
    assert "not {field}" in capability["syntax"]
    system = calls[0]["messages"][0]["content"]
    assert "intent is unset" in system
    assert "not for an" in system and "edge name" in system
    assert result.pack is None
