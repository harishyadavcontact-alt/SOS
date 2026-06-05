"""Local-first Review / AAR v0.1 validation and CLI."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError

try:
    from .decision_log import DecisionLogInput
    from .models import OntologyModel
except ImportError:  # Allows `python src/review.py` from the repo root.
    from decision_log import DecisionLogInput  # type: ignore[no-redef]
    from models import OntologyModel  # type: ignore[no-redef]


class ReviewInput(OntologyModel):
    """A non-ontology after-action review for a recorded DecisionLog."""

    type: Literal["ReviewAAR"]
    decision_log_input: DecisionLogInput
    what_happened: str = Field(min_length=1)
    what_changed: str = Field(min_length=1)
    what_was_learned: str = Field(min_length=1)
    doctrine_updates: list[str]
    protocol_updates: list[str]
    mission_updates: list[str]
    follow_up_actions: list[str] = Field(min_length=1)
    created_at: datetime
    status: Literal["draft", "completed", "archived"]


def load_review(path: Path) -> ReviewInput:
    with path.open("r", encoding="utf-8") as file:
        return ReviewInput.model_validate(json.load(file))


def validate_review_payload(payload: dict[str, object]) -> None:
    ReviewInput.model_validate(payload)


def summarize_review(review: ReviewInput) -> dict[str, object]:
    decision = review.decision_log_input
    return {
        "decision": decision.selected_decision,
        "mission_id": decision.war_game_input.mission.id,
        "owner": decision.owner,
        "status": review.status,
        "created_at": review.created_at.isoformat(),
        "doctrine_update_count": len(review.doctrine_updates),
        "protocol_update_count": len(review.protocol_updates),
        "mission_update_count": len(review.mission_updates),
        "follow_up_actions": review.follow_up_actions,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate and summarize a Review / AAR JSON file.")
    parser.add_argument("path", type=Path, help="Review / AAR JSON file to validate")
    args = parser.parse_args(argv)

    try:
        result = summarize_review(load_review(args.path))
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"FAIL {args.path}: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
