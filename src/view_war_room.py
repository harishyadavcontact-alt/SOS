"""Generate a static local War Room dashboard."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
from typing import Any

try:
    from .index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index
except ImportError:  # Allows `python src/view_war_room.py` from the repo root.
    from index import DEFAULT_EXAMPLES_DIR, IndexedObject, build_index  # type: ignore[no-redef]


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "output" / "war_room.html"


SECTIONS: tuple[tuple[str, tuple[tuple[str, tuple[str, ...]], ...]], ...] = (
    (
        "State of the Art",
        (
            ("Sources of Volatility", ("SourceOfVolatility",)),
            ("Domains", ("Domain",)),
            ("Crafts", ("Craft",)),
            ("Models", ("Model",)),
            ("Signals", ("Signal",)),
        ),
    ),
    (
        "State of Affairs",
        (
            ("Affairs", ("Affair",)),
            ("Interests", ("Interest",)),
            ("Resources", ("Resource",)),
            ("Missions", ("Mission",)),
        ),
    ),
    (
        "State of Functions",
        (
            ("WarGaming", ("WarGame",)),
            ("DecisionLogs", ("DecisionLog",)),
            ("Reviews", ("Review", "ReviewAAR")),
            ("Protocols", ("Protocol",)),
        ),
    ),
    (
        "State of Operations",
        (
            ("Operations", ("Operation",)),
            ("Routines", ("Routine",)),
            ("Regimens", ("Regimen",)),
        ),
    ),
)


LINK_FIELDS = (
    "affair_ids",
    "decision_log_id",
    "domain_ids",
    "interest_ids",
    "lineage_id",
    "mission_id",
    "owner_id",
    "protocol_ids",
    "resource_ids",
    "routine_ids",
    "supports_affair_ids",
    "supports_interest_ids",
    "supports_mission_ids",
)


def _escape(value: object) -> str:
    return html.escape(str(value), quote=True)


def _name(item: IndexedObject) -> str:
    name = item.payload.get("name")
    return name if isinstance(name, str) else item.id


def _field(payload: dict[str, Any], field: str) -> str | None:
    value = payload.get(field)
    if value is None:
        return None
    if isinstance(value, float):
        return f"{value:.2f}"
    return str(value)


def _linked_ids(payload: dict[str, Any]) -> list[str]:
    linked: list[str] = []
    for field in LINK_FIELDS:
        value = payload.get(field)
        if isinstance(value, str):
            linked.append(value)
        elif isinstance(value, list):
            linked.extend(item for item in value if isinstance(item, str))
    return linked


def _card(item: IndexedObject) -> str:
    payload = item.payload
    fields = [
        ("type", item.type),
        ("status", _field(payload, "status")),
        ("owner", _field(payload, "owner_id") or _field(payload, "owner")),
        ("scope", _field(payload, "scope")),
        ("end", _field(payload, "end")),
        ("priority", _field(payload, "priority_score") or _field(payload, "priority")),
    ]
    details = "\n".join(
        f"<div><span>{_escape(label)}</span>{_escape(value)}</div>"
        for label, value in fields
        if value
    )
    links = _linked_ids(payload)
    link_html = ""
    if links:
        link_html = (
            "<div class=\"links\">"
            + "".join(f"<code>{_escape(link)}</code>" for link in links)
            + "</div>"
        )
    return (
        "<article class=\"card\">"
        f"<h4>{_escape(_name(item))}</h4>"
        f"<p>{_escape(item.id)}</p>"
        f"<div class=\"meta\">{details}</div>"
        f"{link_html}"
        "</article>"
    )


def render_war_room(examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> str:
    index = build_index(examples_dir)
    grouped: dict[str, list[IndexedObject]] = index["grouped"]
    sections: list[str] = []

    for section, groups in SECTIONS:
        group_html: list[str] = []
        for title, types in groups:
            items = [item for object_type in types for item in grouped.get(object_type, [])]
            cards = "".join(_card(item) for item in items) if items else "<p class=\"empty\">none detected</p>"
            group_html.append(
                f"<section class=\"group\"><h3>{_escape(title)}</h3><div class=\"grid\">{cards}</div></section>"
            )
        sections.append(f"<section class=\"state\"><h2>{_escape(section)}</h2>{''.join(group_html)}</section>")

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>SoS War Room</title>
  <style>
    :root {{
      color-scheme: light;
      --ink: #17211b;
      --muted: #5f6b63;
      --line: #d8ddd7;
      --paper: #fbfcfa;
      --panel: #ffffff;
      --accent: #176a5b;
      --soft: #eef4f1;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      background: var(--paper);
      color: var(--ink);
      line-height: 1.45;
    }}
    header {{
      padding: 28px 32px 18px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
    }}
    h1, h2, h3, h4, p {{ margin: 0; }}
    h1 {{ font-size: 28px; }}
    header p {{ margin-top: 6px; color: var(--muted); }}
    main {{ padding: 24px 32px 40px; }}
    .state {{ margin-bottom: 34px; }}
    .state > h2 {{
      font-size: 20px;
      margin-bottom: 14px;
      color: var(--accent);
    }}
    .group {{ margin-bottom: 20px; }}
    .group > h3 {{
      font-size: 15px;
      margin-bottom: 10px;
      text-transform: uppercase;
      letter-spacing: 0;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: var(--panel);
      padding: 14px;
      min-height: 156px;
    }}
    .card h4 {{ font-size: 16px; margin-bottom: 4px; }}
    .card p {{ color: var(--muted); font-size: 12px; overflow-wrap: anywhere; }}
    .meta {{ margin-top: 12px; display: grid; gap: 4px; }}
    .meta div {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 13px;
    }}
    .meta span {{ color: var(--muted); }}
    .links {{
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 12px;
    }}
    code {{
      background: var(--soft);
      color: var(--accent);
      padding: 3px 5px;
      border-radius: 4px;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .empty {{
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 8px;
      padding: 14px;
      background: var(--panel);
    }}
  </style>
</head>
<body>
  <header>
    <h1>SoS War Room</h1>
    <p>Static local inspection view generated from examples.</p>
  </header>
  <main>
    {''.join(sections)}
  </main>
</body>
</html>
"""


def write_war_room(output_path: Path = DEFAULT_OUTPUT_PATH, examples_dir: Path = DEFAULT_EXAMPLES_DIR) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_war_room(examples_dir), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate output/war_room.html.")
    parser.add_argument("--examples-dir", type=Path, default=DEFAULT_EXAMPLES_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    write_war_room(args.output, args.examples_dir)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
