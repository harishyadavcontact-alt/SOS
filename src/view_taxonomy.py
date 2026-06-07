"""Generate a static Markdown taxonomy view for local examples."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    from .index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index
except ImportError:  # Allows `python src/view_taxonomy.py` from the repo root.
    from index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index  # type: ignore[no-redef]


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "output" / "taxonomy.md"


BRANCHES: tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    (
        "Intelligence",
        (
            ("State of the Art", ("SourceOfVolatility", "Domain", "Craft")),
        ),
    ),
    (
        "Directorial",
        (
            ("State of Affairs", ("Affair", "Interest", "Resource", "Mission")),
        ),
    ),
    (
        "Executive",
        (
            ("State of Functions", ("Protocol", "Review", "ReviewAAR")),
            ("State of Operations", ("Operation", "Routine", "Regimen")),
        ),
    ),
)


TYPE_LABELS = {
    "SourceOfVolatility": "Sources of Volatility",
    "Domain": "Domains",
    "Craft": "Crafts",
    "Affair": "Affairs",
    "Interest": "Interests",
    "Resource": "Resources",
    "Mission": "Missions",
    "Protocol": "Protocols",
    "Review": "Reviews",
    "ReviewAAR": "Reviews / AARs",
    "Operation": "Operations",
    "Routine": "Routines",
    "Regimen": "Regimens",
}


def _label(item: IndexedObject) -> str:
    name = item.payload.get("name")
    if isinstance(name, str):
        return f"{name} ({item.id})"
    return item.id


def _append_type(lines: list[str], prefix: str, object_type: str, items: list[IndexedObject]) -> None:
    lines.append(f"{prefix}├── {TYPE_LABELS.get(object_type, object_type)}")
    if not items:
        lines.append(f"{prefix}│   └── none detected")
        return
    for index, item in enumerate(items):
        connector = "└──" if index == len(items) - 1 else "├──"
        lines.append(f"{prefix}│   {connector} {_label(item)}")


def render_taxonomy(examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> str:
    index = build_index(examples_dir)
    grouped: dict[str, list[IndexedObject]] = index["grouped"]
    lines = ["# Taxonomy Tree", "", "```text", "System of Systems"]

    for branch_index, (branch, states) in enumerate(BRANCHES):
        branch_last = branch_index == len(BRANCHES) - 1
        branch_connector = "└──" if branch_last else "├──"
        branch_prefix = "    " if branch_last else "│   "
        lines.append(f"{branch_connector} {branch}")

        for state_index, (state, types) in enumerate(states):
            state_last = state_index == len(states) - 1
            state_connector = "└──" if state_last else "├──"
            state_prefix = branch_prefix + ("    " if state_last else "│   ")
            lines.append(f"{branch_prefix}{state_connector} {state}")
            for object_type in types:
                _append_type(lines, state_prefix, object_type, grouped.get(object_type, []))

    lines.extend(["```", ""])
    return "\n".join(lines)


def write_taxonomy(output_path: Path = DEFAULT_OUTPUT_PATH, examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_taxonomy(examples_dir), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate output/taxonomy.md.")
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    write_taxonomy(args.output, args.examples_dir)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
