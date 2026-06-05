"""Validate local JSON examples against the hard-coded ontology models."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

try:
    from .decision_log import validate_decision_log_payload
    from .models import ENTITY_MODELS
    from .review import validate_review_payload
    from .war_game import validate_war_game_payload
except ImportError:  # Allows `python src/validate.py` from the repo root.
    from decision_log import validate_decision_log_payload  # type: ignore[no-redef]
    from models import ENTITY_MODELS  # type: ignore[no-redef]
    from review import validate_review_payload  # type: ignore[no-redef]
    from war_game import validate_war_game_payload  # type: ignore[no-redef]


DEFAULT_EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"


def validate_file(path: Path) -> None:
    """Validate one JSON file using its `type` discriminator."""

    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)

    entity_type = payload.get("type")
    if not isinstance(entity_type, str):
        raise ValueError(f"{path}: missing string field 'type'")

    if entity_type == "WarGame":
        validate_war_game_payload(payload)
        return

    if entity_type == "DecisionLog":
        validate_decision_log_payload(payload)
        return

    if entity_type == "ReviewAAR":
        validate_review_payload(payload)
        return

    model = ENTITY_MODELS.get(entity_type)
    if model is None:
        known = ", ".join(sorted(ENTITY_MODELS))
        raise ValueError(f"{path}: unknown type {entity_type!r}; expected one of: {known}")

    model.model_validate(payload)


def iter_json_files(path: Path) -> list[Path]:
    """Return JSON files from a path or directory in deterministic order."""

    if path.is_file():
        return [path]
    return sorted(path.glob("*.json"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate SoS ontology JSON files.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[DEFAULT_EXAMPLES_DIR],
        help="JSON files or directories to validate; defaults to ./examples",
    )
    args = parser.parse_args(argv)

    files: list[Path] = []
    for path in args.paths:
        files.extend(iter_json_files(path))

    if not files:
        print("No JSON files found to validate.", file=sys.stderr)
        return 1

    failures = 0
    for path in files:
        try:
            validate_file(path)
        except (OSError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            failures += 1
            print(f"FAIL {path}: {exc}", file=sys.stderr)
        else:
            print(f"OK   {path}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
