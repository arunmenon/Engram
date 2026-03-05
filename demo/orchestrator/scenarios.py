import json
from pathlib import Path
from typing import Any

SCENARIOS_DIR = Path(__file__).parent / "scenarios"


def load_scenarios() -> list[dict[str, Any]]:
    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        with open(path) as f:
            scenarios.append(json.load(f))
    return scenarios


def get_scenario(scenario_id: str) -> dict[str, Any] | None:
    for s in load_scenarios():
        if s["id"] == scenario_id:
            return s
    return None
