"""Local-first Decision Log v0.1 validation and CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError, model_validator

try:
    from .models import OntologyModel
    from .war_game import WarGameInput, run_war_game
except ImportError:  # Allows `python src/decision_log.py` from the repo root.
    from models import OntologyModel  # type: ignore[no-redef]
    from war_game import WarGameInput, run_war_game  # type: ignore[no-redef]


Decision = Literal["Hedge", "Edge", "Abort", "Review"]


class DecisionLogInput(OntologyModel):
    """A non-ontology record of a WarGame recommendation and chosen decision."""

    type: Literal["DecisionLog"]
    war_game_input: WarGameInput
    recommendation: Decision
    selected_decision: Decision
    rationale: str = Field(min_length=1)
    next_actions: list[str] = Field(min_length=1)
    owner: str = Field(min_length=1)
    created_at: datetime
    review_date: date
    status: Literal["draft", "recorded", "review_pending", "reviewed", "closed"]

    @model_validator(mode="after")
    def recorded_recommendation_must_match_war_game(self) -> "DecisionLogInput":
        actual = run_war_game(self.war_game_input)
        if self.recommendation != actual["recommendation"]:
            raise ValueError(
                "DecisionLog recommendation does not match WarGame output: "
                f"{self.recommendation!r} != {actual['recommendation']!r}"
            )
        return self


def load_decision_log(path: Path) -> DecisionLogInput:
    with path.open("r", encoding="utf-8") as file:
        return DecisionLogInput.model_validate(json.load(file))


def validate_decision_log_payload(payload: dict[str, object]) -> None:
    DecisionLogInput.model_validate(payload)


def summarize_decision_log(decision_log: DecisionLogInput) -> dict[str, object]:
    war_game_output = run_war_game(decision_log.war_game_input)
    return {
        "recommendation": decision_log.recommendation,
        "selected_decision": decision_log.selected_decision,
        "owner": decision_log.owner,
        "status": decision_log.status,
        "review_date": decision_log.review_date.isoformat(),
        "review_required": war_game_output["review_required"],
        "triggered_gates": war_game_output["triggered_gates"],
        "next_actions": decision_log.next_actions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and summarize a DecisionLog JSON file.")
    parser.add_argument("path", type=Path, help="DecisionLog JSON file to validate")
    args = parser.parse_args(argv)

    try:
        result = summarize_decision_log(load_decision_log(args.path))
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"FAIL {args.path}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
