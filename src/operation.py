"""Local-first Operation v0.1 builder and validator."""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

try:
    from .decision_log import DecisionLogInput
    from .models import Affair, Interest, Mission, OntologyModel
except ImportError:  # Allows `python src/operation.py` from the repo root.
    from decision_log import DecisionLogInput  # type: ignore[no-redef]
    from models import Affair, Interest, Mission, OntologyModel  # type: ignore[no-redef]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "operation"


class OperationOutput(OntologyModel):
    """Executable operation payload generated from a DecisionLog."""

    id: str
    type: Literal["Operation"]
    name: str
    mission_id: str
    owner_id: str
    objective: str
    operation_type: Literal["horizontal", "vertical"]
    priority: Literal["low", "medium", "high", "critical"]
    supporting_affair_ids: list[str] = Field(default_factory=list)
    supporting_interest_ids: list[str] = Field(default_factory=list)
    protocol_ids: list[str] = Field(default_factory=list)
    start_date: date
    target_date: date
    success_criteria: list[str] = Field(min_length=1)
    abort_conditions: list[str] = Field(min_length=1)
    status: Literal["planned", "active", "complete", "aborted", "archived"]

    @model_validator(mode="after")
    def must_support_affair_or_interest(self) -> "OperationOutput":
        if not self.supporting_affair_ids and not self.supporting_interest_ids:
            raise ValueError("Operation must support at least one Affair or Interest")
        return self


class OperationBuildInput(OntologyModel):
    """A non-ontology request that turns a DecisionLog into an Operation."""

    type: Literal["OperationBuild"]
    decision_log_input: DecisionLogInput
    mission: Mission
    affairs: list[Affair]
    interests: list[Interest]
    expected_operation: OperationOutput | None = None

    @model_validator(mode="after")
    def references_must_exist(self) -> "OperationBuildInput":
        decision_mission = self.decision_log_input.war_game_input.mission
        if self.mission.id != decision_mission.id:
            raise ValueError(
                "OperationBuild mission must match DecisionLog mission: "
                f"{self.mission.id!r} != {decision_mission.id!r}"
            )

        affair_ids = {affair.id for affair in self.affairs}
        interest_ids = {interest.id for interest in self.interests}
        missing_affairs = sorted(set(self.mission.affair_ids) - affair_ids)
        missing_interests = sorted(set(self.mission.interest_ids) - interest_ids)

        missing = []
        if missing_affairs:
            missing.append(f"affairs: {', '.join(missing_affairs)}")
        if missing_interests:
            missing.append(f"interests: {', '.join(missing_interests)}")
        if missing:
            raise ValueError("OperationBuild references are missing: " + "; ".join(missing))

        return self


def build_operation(input_data: OperationBuildInput) -> OperationOutput:
    decision = input_data.decision_log_input
    mission = input_data.mission
    abort_condition = mission.blueprint.get("abort_condition")
    abort_conditions = [abort_condition.strip()] if isinstance(abort_condition, str) and abort_condition.strip() else []

    if decision.selected_decision in {"Abort", "Review"}:
        priority = "critical"
    elif decision.selected_decision == "Hedge":
        priority = "high"
    else:
        priority = "medium"

    operation_type = "vertical" if mission.interest_ids else "horizontal"
    success_criteria = [
        f"Selected decision remains {decision.selected_decision}.",
        "All recorded next actions are completed or explicitly reviewed.",
        "Mission progress is reviewed by the target date.",
    ]

    return OperationOutput(
        id=f"operation.{_slug(mission.name)}.v1",
        type="Operation",
        name=f"{mission.name} Operation v1",
        mission_id=mission.id,
        owner_id=mission.owner_id,
        objective=f"{decision.selected_decision} execution for mission: {mission.target_trajectory}",
        operation_type=operation_type,
        priority=priority,
        supporting_affair_ids=list(mission.affair_ids),
        supporting_interest_ids=list(mission.interest_ids),
        protocol_ids=[],
        start_date=decision.created_at.date(),
        target_date=decision.review_date,
        success_criteria=success_criteria,
        abort_conditions=abort_conditions,
        status="planned",
    )


def validate_operation_references(input_data: OperationBuildInput, operation: OperationOutput) -> None:
    if operation.mission_id != input_data.mission.id:
        raise ValueError(
            "Operation must belong to exactly the provided Mission: "
            f"{operation.mission_id!r} != {input_data.mission.id!r}"
        )

    affair_ids = {affair.id for affair in input_data.affairs}
    interest_ids = {interest.id for interest in input_data.interests}
    missing_affairs = sorted(set(operation.supporting_affair_ids) - affair_ids)
    missing_interests = sorted(set(operation.supporting_interest_ids) - interest_ids)

    if missing_affairs or missing_interests:
        details = []
        if missing_affairs:
            details.append(f"affairs: {', '.join(missing_affairs)}")
        if missing_interests:
            details.append(f"interests: {', '.join(missing_interests)}")
        raise ValueError("Operation references do not exist: " + "; ".join(details))


def load_operation_build(path: Path) -> OperationBuildInput:
    with path.open("r", encoding="utf-8") as file:
        return OperationBuildInput.model_validate(json.load(file))


def validate_operation_payload(payload: dict[str, object]) -> None:
    scenario = OperationBuildInput.model_validate(payload)
    operation = build_operation(scenario)
    validate_operation_references(scenario, operation)

    if scenario.expected_operation is not None and operation != scenario.expected_operation:
        expected_json = json.dumps(
            scenario.expected_operation.model_dump(mode="json"), indent=2, sort_keys=True
        )
        actual_json = json.dumps(operation.model_dump(mode="json"), indent=2, sort_keys=True)
        raise ValueError(
            f"Operation expected_operation mismatch.\nexpected:\n{expected_json}\nactual:\n{actual_json}"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build an executable Operation from a DecisionLog.")
    parser.add_argument("path", type=Path, help="OperationBuild JSON file to evaluate")
    args = parser.parse_args(argv)

    try:
        scenario = load_operation_build(args.path)
        operation = build_operation(scenario)
        validate_operation_references(scenario, operation)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"FAIL {args.path}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(operation.model_dump(mode="json"), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
