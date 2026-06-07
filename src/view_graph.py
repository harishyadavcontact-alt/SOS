"""Generate a static Mermaid ontology relationship graph."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

try:
    from .index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index
except ImportError:  # Allows `python src/view_graph.py` from the repo root.
    from index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index  # type: ignore[no-redef]


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "output" / "ontology_graph.mmd"


def _node_id(object_id: str) -> str:
    return "n_" + re.sub(r"[^A-Za-z0-9_]", "_", object_id)


def _label(item: IndexedObject) -> str:
    name = item.payload.get("name")
    label = name if isinstance(name, str) else item.id
    return f"{label}\\n{item.type}\\n{item.id}"


def _edge(lines: list[str], source: IndexedObject, target: IndexedObject, label: str) -> None:
    lines.append(f"  {_node_id(source.id)} -->|{label}| {_node_id(target.id)}")


def _targets(indexed: dict[str, IndexedObject], ids: Iterable[str]) -> list[IndexedObject]:
    return [indexed[item_id] for item_id in ids if item_id in indexed]


def render_graph(examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> str:
    index = build_index(examples_dir)
    objects: dict[str, IndexedObject] = index["unique_objects"]
    lines = ["```mermaid", "graph TD"]

    for item in sorted(objects.values(), key=lambda value: value.id):
        lines.append(f"  {_node_id(item.id)}[\"{_label(item)}\"]")

    for item in sorted(objects.values(), key=lambda value: value.id):
        payload = item.payload

        if item.type == "Agent":
            lineage_id = payload.get("lineage_id")
            if isinstance(lineage_id, str) and lineage_id in objects:
                _edge(lines, item, objects[lineage_id], "Lineage")

        if item.type in {"Affair", "Interest", "Mission", "Resource"}:
            owner_id = payload.get("owner_id")
            if isinstance(owner_id, str) and owner_id in objects:
                _edge(lines, objects[owner_id], item, item.type)

        if item.type == "Mission":
            for target in _targets(objects, payload.get("affair_ids", [])):
                _edge(lines, item, target, "Affair")
            for target in _targets(objects, payload.get("interest_ids", [])):
                _edge(lines, item, target, "Interest")
            for target in _targets(objects, payload.get("resource_ids", [])):
                _edge(lines, item, target, "Resource")

        if item.type == "Operation":
            mission_id = payload.get("mission_id")
            if isinstance(mission_id, str) and mission_id in objects:
                _edge(lines, objects[mission_id], item, "Operation")
            for target in _targets(objects, payload.get("protocol_ids", [])):
                _edge(lines, item, target, "Protocol")

        if item.type == "Regimen":
            for target in _targets(objects, payload.get("routine_ids", [])):
                _edge(lines, item, target, "Routine")

        if item.type == "Signal":
            for target in _targets(objects, payload.get("related_entity_ids", [])):
                if target.type == "Review":
                    _edge(lines, item, target, "Review")

        if item.type in {"Review", "ReviewAAR"}:
            mission_id = payload.get("mission_id")
            if not isinstance(mission_id, str):
                decision_log = payload.get("decision_log_input")
                if isinstance(decision_log, dict):
                    war_game = decision_log.get("war_game_input")
                    if isinstance(war_game, dict):
                        mission = war_game.get("mission")
                        if isinstance(mission, dict):
                            candidate = mission.get("id")
                            if isinstance(candidate, str):
                                mission_id = candidate
            if isinstance(mission_id, str) and mission_id in objects:
                _edge(lines, item, objects[mission_id], "Mission")
            for target in _targets(objects, payload.get("protocol_updates", [])):
                _edge(lines, item, target, "Protocol")

    lines.extend(["```", ""])
    return "\n".join(lines)


def write_graph(output_path: Path = DEFAULT_OUTPUT_PATH, examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_graph(examples_dir), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate output/ontology_graph.mmd.")
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    write_graph(args.output, args.examples_dir)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
