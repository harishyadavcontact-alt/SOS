"""Local inspection index for example ontology JSON files."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_EXAMPLES_DIR = Path(__file__).resolve().parents[1] / "examples"
REFERENCE_SUFFIXES = ("_id", "_ids")
EMBEDDED_KEYS = {
    "affairs",
    "decision_log_input",
    "expected_operation",
    "interests",
    "objects",
    "mission",
    "resources",
    "war_game_input",
}


@dataclass(frozen=True)
class IndexedObject:
    id: str
    type: str
    payload: dict[str, Any]
    path: Path
    nested_path: str

    @property
    def is_top_level(self) -> bool:
        return self.nested_path == "$"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"{path}: expected JSON object")
    return payload


def _walk_objects(value: Any, path: Path, nested_path: str = "$") -> list[IndexedObject]:
    objects: list[IndexedObject] = []
    if isinstance(value, dict):
        object_id = value.get("id")
        object_type = value.get("type")
        if not isinstance(object_id, str) and isinstance(object_type, str) and nested_path == "$":
            object_id = f"{object_type.lower()}.{path.stem}"
        if isinstance(object_id, str) and isinstance(object_type, str):
            objects.append(
                IndexedObject(
                    id=object_id,
                    type=object_type,
                    payload=value,
                    path=path,
                    nested_path=nested_path,
                )
            )

        for key, child in value.items():
            if key in EMBEDDED_KEYS:
                objects.extend(_walk_objects(child, path, f"{nested_path}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            objects.extend(_walk_objects(item, path, f"{nested_path}[{index}]"))
    return objects


def read_example_objects(examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> list[IndexedObject]:
    objects: list[IndexedObject] = []
    for path in sorted(examples_dir.glob("*.json")):
        objects.extend(_walk_objects(_load_json(path), path))
    return objects


def _unique_by_id(objects: list[IndexedObject]) -> dict[str, IndexedObject]:
    unique: dict[str, IndexedObject] = {}
    for item in objects:
        unique.setdefault(item.id, item)
    return unique


def _duplicates(objects: list[IndexedObject]) -> dict[str, list[IndexedObject]]:
    by_id: dict[str, list[IndexedObject]] = defaultdict(list)
    for item in objects:
        by_id[item.id].append(item)
    return {object_id: hits for object_id, hits in sorted(by_id.items()) if len(hits) > 1}


def _global_duplicates(objects: list[IndexedObject]) -> dict[str, list[IndexedObject]]:
    return _duplicates([item for item in objects if item.is_top_level])


def _scenario_local_duplicates(objects: list[IndexedObject]) -> dict[str, list[IndexedObject]]:
    duplicates = _duplicates(objects)
    return {
        object_id: hits
        for object_id, hits in duplicates.items()
        if object_id not in _global_duplicates(objects)
    }


def _references_from_payload(payload: dict[str, Any]) -> list[tuple[str, str]]:
    references: list[tuple[str, str]] = []
    for key, value in payload.items():
        if key.endswith(REFERENCE_SUFFIXES):
            if isinstance(value, str):
                references.append((key, value))
            elif isinstance(value, list):
                references.extend((key, item) for item in value if isinstance(item, str))
    return references


def _missing_references(objects: list[IndexedObject]) -> list[dict[str, str]]:
    known_ids = set(_unique_by_id(objects))
    missing: list[dict[str, str]] = []
    for item in objects:
        for field, reference in _references_from_payload(item.payload):
            if reference not in known_ids:
                missing.append(
                    {
                        "source_id": item.id,
                        "source_type": item.type,
                        "field": field,
                        "missing_id": reference,
                        "path": str(item.path),
                    }
                )
    return missing


def build_index(examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> dict[str, Any]:
    objects = read_example_objects(examples_dir)
    unique_objects = _unique_by_id(objects)
    grouped: dict[str, list[IndexedObject]] = defaultdict(list)
    for item in unique_objects.values():
        grouped[item.type].append(item)

    return {
        "objects": objects,
        "unique_objects": unique_objects,
        "grouped": {key: sorted(value, key=lambda item: item.id) for key, value in sorted(grouped.items())},
        "duplicates": _duplicates(objects),
        "global_duplicates": _global_duplicates(objects),
        "scenario_local_duplicates": _scenario_local_duplicates(objects),
        "missing_references": _missing_references(objects),
    }


def _print_report(index: dict[str, Any]) -> None:
    grouped: dict[str, list[IndexedObject]] = index["grouped"]
    global_duplicates: dict[str, list[IndexedObject]] = index["global_duplicates"]
    scenario_local_duplicates: dict[str, list[IndexedObject]] = index["scenario_local_duplicates"]
    missing: list[dict[str, str]] = index["missing_references"]

    print(f"total objects: {len(index['unique_objects'])}")
    print("counts by type:")
    for object_type, objects in grouped.items():
        print(f"  {object_type}: {len(objects)}")

    print("global duplicate ids:")
    if not global_duplicates:
        print("  none")
    else:
        for object_id, hits in global_duplicates.items():
            locations = ", ".join(f"{hit.path.name}:{hit.nested_path}" for hit in hits)
            print(f"  {object_id}: {locations}")

    print("scenario-local duplicate id warnings:")
    if not scenario_local_duplicates:
        print("  none")
    else:
        for object_id, hits in scenario_local_duplicates.items():
            locations = ", ".join(f"{hit.path.name}:{hit.nested_path}" for hit in hits)
            print(f"  {object_id}: {locations}")

    print("missing references:")
    if not missing:
        print("  none")
    else:
        for item in missing:
            print(
                "  "
                f"{item['source_id']} ({item['source_type']}) "
                f"{item['field']} -> {item['missing_id']}"
            )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect local SoS example JSON files.")
    parser.add_argument(
        "examples_dir",
        nargs="?",
        type=Path,
        default=DEFAULT_EXAMPLES_DIR,
        help="Directory of JSON examples; defaults to ./examples",
    )
    args = parser.parse_args(argv)
    _print_report(build_index(args.examples_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
