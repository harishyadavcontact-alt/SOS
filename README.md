# System-of-Systems Ontology Engine Prototype

This repository is a local-first prototype for a personal System-of-Systems (SoS) ontology engine.

The design rule is:

> Hard-code the ontology. Configure the world.

The ontology is represented in Python models and JSON Schemas. User-specific affairs, interests, missions, routines, regimens, protocols, domains, crafts, and other objects should be stored as local JSON/YAML configuration and validated against the hard-coded ontology.

## What is included

- `schema/*.schema.json` — JSON Schema files for the core ontology entities.
- `examples/*.json` — one valid example each for:
  - `Affair`
  - `Interest`
  - `Mission`
  - `Protocol`
  - `Routine`
  - `Regimen`
- `src/models.py` — Pydantic models matching the schemas.
- `src/validate.py` — local validation command for example JSON files.

## What is intentionally not included yet

- No UI.
- No database.
- No graph store.
- No new ontology concepts beyond the v0.1 ontology.
- No architecture redesign.

## Setup

Create and activate a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
```

Install the local package and dependencies:

```bash
pip install -e .
```

## Usage

Validate all bundled examples:

```bash
python -m src.validate
```

Validate a specific file:

```bash
python -m src.validate examples/affair.json
```

Validate every JSON file in a directory:

```bash
python -m src.validate examples
```

The validator reads each JSON object's `type` field, selects the matching Pydantic model from `src/models.py`, and validates the object locally. It does not require a database or network service.

## Workflow

```text
Signal
→ WarGame
→ DecisionLog
→ Operation
→ Execution
→ Review
→ Doctrine Update
```

Run local validation:

```bash
python -B -m src.validate
```

Run a WarGame scenario:

```bash
python -B -m src.war_game examples/war_game_mission_build_ai_business.json
```

Summarize a DecisionLog:

```bash
python -B -m src.decision_log examples/decision_log_ai_business_hedge.json
```

Validate an Operation:

```bash
python -B -m src.operation examples/operation_ai_business_v1.json
```

Run a Review / AAR:

```bash
python -B -m src.review examples/review_ai_business_hedge_aar.json
```

## Visual Inspection

Build a local reference index:

```bash
python -B -m src.index
```

Generate a taxonomy tree:

```bash
python -B -m src.view_taxonomy
```

Generate a Mermaid graph:

```bash
python -B -m src.view_graph
```

Generate the static War Room dashboard:

```bash
python -B -m src.view_war_room
```

## Interactive War Room

Generate the interactive local four-state visualizer:

```bash
python -B -m src.view_interactive_war_room
```

Output:

```text
output/interactive_war_room.html
```

Open the file in a browser. The visualizer includes the four Genesis states, a collapsible tree, an ontology graph, a right-side inspector, and derived agenda/calendar sections inside State of Operations.

Outputs:

```text
output/taxonomy.md
output/ontology_graph.mmd
output/war_room.html
```

## Local-first workflow

1. Edit ontology state/configuration as JSON or YAML files.
2. Validate JSON files before committing changes.
3. Use Git as the first versioned state/history layer.
4. Keep the ontology grammar in code and schemas; keep the user's world in data files.

## Schema naming

The schema files use snake-case names for entity types:

```text
schema/agent.schema.json
schema/lineage.schema.json
schema/source_of_volatility.schema.json
schema/domain.schema.json
schema/craft.schema.json
schema/code_of_conduct.schema.json
schema/rules_of_engagement.schema.json
schema/affair.schema.json
schema/interest.schema.json
schema/resource.schema.json
schema/signal.schema.json
schema/mission.schema.json
schema/protocol.schema.json
schema/operation.schema.json
schema/routine.schema.json
schema/regimen.schema.json
schema/review.schema.json
schema/artifact.schema.json
```
