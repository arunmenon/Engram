"""Compose independent G07 slice oracles; never derive expectations from runtime rules."""

from datetime import UTC, datetime, timedelta

from engram_goal07_deployment_fixtures import fixtures as deployments
from engram_goal07_lifecycle_fixtures import fixtures as lifecycle
from engram_goal07_requests_fixtures import fixtures as requests
from engram_goal07_skipped_fixtures import fixtures as skipped


def fixtures(run_id, *, start=None):
    # Catalog remains an explicit prerequisite, rather than silently running a subset.
    from engram_goal07_catalog_fixtures import fixtures as catalog

    start = start or (datetime.now(UTC) - timedelta(hours=1)).replace(microsecond=0)
    result = dict(ids={}, steps=[], queries=[], webhook_cases=[], source_kind=[], limitations=[])
    for index, (label, factory) in enumerate(
        (("A", requests), ("B", lifecycle), ("C", skipped), ("D", deployments), ("E", catalog))
    ):
        data = factory(run_id, start=start + timedelta(minutes=index * 5))
        result["ids"].update({label + "-" + key: value for key, value in data["ids"].items()})
        for key in ("steps", "queries", "webhook_cases", "limitations"):
            result[key].extend(data.get(key, []))
        result["source_kind"].append(dict(slice=label, description=data["source_kind"]))
        if label == "A":
            result["fallback_seed"] = data["fallback_seed"]
    scenarios = [
        item["scenario"] for key in ("steps", "queries", "webhook_cases") for item in result[key]
    ]
    if len(scenarios) != len(set(scenarios)):
        raise ValueError("G07 scenario identities collide")
    result["catalog_expectation"] = dict(event_types=28, historical_passes_reused=False)
    return result
