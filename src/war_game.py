"""Local-first War Gaming v0.1 orchestration."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Literal

from pydantic import ValidationError, model_validator

try:
    from .gates import DEFAULT_GATES, Gate, GateResult, WarGameContext
    from .models import Affair, Interest, Mission, OntologyModel, Resource
except ImportError:  # Allows `python src/war_game.py` from the repo root.
    from gates import DEFAULT_GATES, Gate, GateResult, WarGameContext  # type: ignore[no-redef]
    from models import Affair, Interest, Mission, OntologyModel, Resource  # type: ignore[no-redef]


Recommendation = Literal["Hedge", "Edge", "Abort", "Review"]


class WarGameInput(OntologyModel):
    """A non-ontology validation scenario for War Gaming a mission."""

    type: Literal["WarGame"]
    mission: Mission
    affairs: list[Affair]
    interests: list[Interest]
    resources: list[Resource]
    expected_output: dict[str, object] | None = None

    @model_validator(mode="after")
    def linked_entities_must_match_mission(self) -> "WarGameInput":
        affair_ids = {affair.id for affair in self.affairs}
        interest_ids = {interest.id for interest in self.interests}
        resource_ids = {resource.id for resource in self.resources}

        missing_affairs = sorted(set(self.mission.affair_ids) - affair_ids)
        missing_interests = sorted(set(self.mission.interest_ids) - interest_ids)
        missing_resources = sorted(set(self.mission.resource_ids) - resource_ids)

        missing = []
        if missing_affairs:
            missing.append(f"affairs: {', '.join(missing_affairs)}")
        if missing_interests:
            missing.append(f"interests: {', '.join(missing_interests)}")
        if missing_resources:
            missing.append(f"resources: {', '.join(missing_resources)}")

        if missing:
            raise ValueError("mission links are missing from WarGame input: " + "; ".join(missing))

        return self


def _combine_recommendations(results: list[GateResult]) -> Recommendation:
    triggered = [result for result in results if result.triggered]
    if any(result.recommendation == "Abort" for result in triggered):
        return "Abort"
    if any(result.recommendation == "Hedge" for result in triggered):
        return "Hedge"
    if any(result.recommendation == "Review" for result in triggered):
        return "Review"
    if any(result.recommendation == "Edge" for result in triggered):
        return "Edge"
    return "Review"


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            output.append(item)
    return output


def run_war_game(input_data: WarGameInput, gates: tuple[Gate, ...] = DEFAULT_GATES) -> dict[str, object]:
    """Run all War Gaming gates and return a deterministic recommendation."""

    context = WarGameContext(
        mission=input_data.mission,
        affairs=input_data.affairs,
        interests=input_data.interests,
        resources=input_data.resources,
    )
    results = [gate.evaluate(context) for gate in gates]
    triggered = [result for result in results if result.triggered]
    recommendation = _combine_recommendations(results)
    reasoning = [result.reasoning for result in results if result.triggered or result.review_required]
    next_actions = _dedupe(
        [action for result in triggered for action in result.next_actions]
    )

    if not next_actions:
        next_actions = ["Review mission state after the next real-world signal."]

    return {
        "recommendation": recommendation,
        "triggered_gates": [result.name for result in triggered],
        "reasoning_summary": " ".join(reasoning),
        "next_actions": next_actions,
        "review_required": recommendation in {"Abort", "Hedge", "Review"}
        or any(result.review_required for result in results),
    }


def load_war_game(path: Path) -> WarGameInput:
    with path.open("r", encoding="utf-8") as file:
        return WarGameInput.model_validate(json.load(file))


def validate_war_game_payload(payload: dict[str, object]) -> None:
    scenario = WarGameInput.model_validate(payload)
    actual = run_war_game(scenario)
    if scenario.expected_output is not None and actual != scenario.expected_output:
        expected_json = json.dumps(scenario.expected_output, indent=2, sort_keys=True)
        actual_json = json.dumps(actual, indent=2, sort_keys=True)
        raise ValueError(f"WarGame expected_output mismatch.\nexpected:\n{expected_json}\nactual:\n{actual_json}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a local War Gaming scenario.")
    parser.add_argument("path", type=Path, help="WarGame JSON scenario to evaluate")
    args = parser.parse_args(argv)

    try:
        result = run_war_game(load_war_game(args.path))
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"FAIL {args.path}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
