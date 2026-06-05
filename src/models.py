"""Hard-coded System-of-Systems ontology models.

The ontology is intentionally represented as typed Pydantic models rather than
runtime-created concepts. User-specific domains, affairs, interests, missions,
routines, protocols, and related objects are configuration data that should be
validated against these models.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


Score = float


class OntologyModel(BaseModel):
    """Base model for all hard-coded ontology entities."""

    model_config = ConfigDict(extra="forbid")


class Agent(OntologyModel):
    id: str
    type: Literal["Agent"]
    name: str
    lineage_id: str | None = None
    authority_level: str
    skin_in_game_score: Score
    status: Literal["active", "inactive"]


class Lineage(OntologyModel):
    id: str
    type: Literal["Lineage"]
    name: str
    scale: Literal["individual", "family", "clan", "institution", "civilization"]
    parent_lineage_id: str | None = None
    continuity_goal: str | None = None


class SourceOfVolatility(OntologyModel):
    id: str
    type: Literal["SourceOfVolatility"]
    name: str
    description: str
    force_type: Literal[
        "complexity",
        "evolution",
        "history",
        "market",
        "politics",
        "biology",
        "culture",
        "technology",
        "law",
    ]
    volatility_profile: dict[str, Any] | None = None


class Domain(OntologyModel):
    id: str
    type: Literal["Domain"]
    name: str
    source_ids: list[str]
    constraints: list[str] | None = None
    parent_domain_id: str | None = None


class Craft(OntologyModel):
    id: str
    type: Literal["Craft"]
    name: str
    domain_ids: list[str]
    source_ids: list[str]
    position: Literal["meta_craft", "craft", "subcraft"]
    principles: list[str] | None = None
    maxims: list[str] | None = None
    heuristics: list[str] | None = None
    models: list[str] | None = None
    status: Literal["memo", "draft", "forged", "honed", "ratified", "archived"]


class CodeOfConduct(OntologyModel):
    id: str
    type: Literal["CodeOfConduct"]
    name: str
    craft_ids: list[str]
    policies: list[str]
    prohibited_actions: list[str]
    required_constraints: list[str]
    status: Literal["draft", "ratified", "active", "archived"]


class RulesOfEngagement(OntologyModel):
    id: str
    type: Literal["RulesOfEngagement"]
    name: str
    context: str
    permitted_actions: list[str]
    prohibited_actions: list[str]
    escalation_conditions: list[str] | None = None
    code_of_conduct_id: str


class Affair(OntologyModel):
    id: str
    type: Literal["Affair"]
    name: str
    owner_id: str
    domain_ids: list[str]
    scope: Literal["horizontal", "vertical"]
    front: Literal["inner", "private", "public", "outer"]
    end: Literal["hedge", "abort"]
    stake: str
    deadline: date | None = None
    cadence: Literal["daily", "weekly", "monthly", "quarterly", "annual", "event_driven"] | None = None
    fragility_score: Score = Field(ge=0, le=1)
    ruin_risk: bool
    priority_score: Score = Field(ge=0, le=1)
    status: Literal["active", "deferred", "hedged", "aborted", "closed"]
    parent_affair_id: str | None = None


class Interest(OntologyModel):
    id: str
    type: Literal["Interest"]
    name: str
    owner_id: str
    domain_ids: list[str]
    scope: Literal["horizontal", "vertical"]
    front: Literal["inner", "private", "public", "outer"]
    end: Literal["edge", "abort"]
    cost: float | None = None
    downside: str
    upside: str
    convexity_score: Score = Field(ge=0, le=1)
    optionality_score: Score = Field(ge=0, le=1)
    priority_score: Score = Field(ge=0, le=1)
    status: Literal["active", "dormant", "pursued", "killed", "converted_to_mission"]
    parent_interest_id: str | None = None


class Resource(OntologyModel):
    id: str
    type: Literal["Resource"]
    name: str
    resource_type: Literal["asset", "liability"]
    owner_id: str
    domain_ids: list[str] | None = None
    quantity: float | None = None
    unit: str | None = None
    liquidity: Literal["low", "medium", "high"] | None = None
    criticality_score: Score = Field(ge=0, le=1)
    status: Literal["active", "depleted", "growing", "impaired"]


class Signal(OntologyModel):
    id: str
    type: Literal["Signal"]
    name: str
    source: str
    observed_at: datetime
    strength: Score = Field(ge=0, le=1)
    confidence: Score = Field(ge=0, le=1)
    skin_in_game_weight: Score = Field(ge=0, le=1)
    related_entity_ids: list[str] | None = None
    triggers_review: bool


class Mission(OntologyModel):
    id: str
    type: Literal["Mission"]
    name: str
    owner_id: str
    current_state: str
    target_trajectory: str
    affair_ids: list[str]
    interest_ids: list[str]
    resource_ids: list[str]
    roadmap: list[str]
    blueprint: dict[str, Any]
    path_dependence_notes: str | None = None
    scale_dependence_notes: str | None = None
    interdependence_notes: str | None = None
    death_spiral_risk: Score = Field(ge=0, le=1)
    virtuous_spiral_score: Score = Field(ge=0, le=1)
    status: Literal["draft", "active", "paused", "completed", "aborted", "archived"]


class Protocol(OntologyModel):
    id: str
    type: Literal["Protocol"]
    name: str
    craft_id: str | None = None
    code_of_conduct_id: str | None = None
    trigger_conditions: list[str]
    steps: list[str]
    kill_rule: str
    review_cadence: Literal["daily", "weekly", "monthly", "quarterly", "event_driven"]
    status: Literal["draft", "active", "retired"]


class Operation(OntologyModel):
    id: str
    type: Literal["Operation"]
    name: str
    operation_type: Literal["horizontal", "vertical"]
    mission_id: str | None = None
    owner_id: str
    protocol_ids: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: Literal["planned", "active", "complete", "aborted", "archived"]


class Routine(OntologyModel):
    id: str
    type: Literal["Routine"]
    name: str
    cadence: Literal["daily", "weekly", "monthly", "event_driven"]
    supports_affair_ids: list[str] | None = None
    supports_interest_ids: list[str] | None = None
    steps: list[str]
    status: Literal["active", "paused", "retired"]


class Regimen(OntologyModel):
    id: str
    type: Literal["Regimen"]
    name: str
    routine_ids: list[str]
    purpose: str
    supports_affair_ids: list[str] | None = None
    supports_mission_ids: list[str] | None = None
    status: Literal["active", "paused", "retired"]


class Review(OntologyModel):
    id: str
    type: Literal["Review"]
    name: str
    reviewed_entity_ids: list[str]
    what_happened: str
    what_changed: str
    what_was_learned: str
    doctrine_updates: list[str] | None = None
    protocol_updates: list[str] | None = None
    mission_updates: list[str] | None = None
    created_at: datetime


class Artifact(OntologyModel):
    id: str
    type: Literal["Artifact"]
    name: str
    artifact_type: Literal[
        "primary_source",
        "memo",
        "draft",
        "doctrine",
        "report",
        "decision_log",
        "aar",
        "checklist",
    ]
    lifecycle_state: Literal[
        "source",
        "memo",
        "draft",
        "forge",
        "hone",
        "ratified",
        "wield",
        "review",
        "updated",
        "aborted",
        "archived",
    ]
    linked_entity_ids: list[str] | None = None
    content_path: str | None = None


ENTITY_MODELS: dict[str, type[OntologyModel]] = {
    model.__name__: model
    for model in (
        Agent,
        Lineage,
        SourceOfVolatility,
        Domain,
        Craft,
        CodeOfConduct,
        RulesOfEngagement,
        Affair,
        Interest,
        Resource,
        Signal,
        Mission,
        Protocol,
        Operation,
        Routine,
        Regimen,
        Review,
        Artifact,
    )
}

SCHEMA_FILENAMES: dict[str, str] = {
    "Agent": "agent.schema.json",
    "Lineage": "lineage.schema.json",
    "SourceOfVolatility": "source_of_volatility.schema.json",
    "Domain": "domain.schema.json",
    "Craft": "craft.schema.json",
    "CodeOfConduct": "code_of_conduct.schema.json",
    "RulesOfEngagement": "rules_of_engagement.schema.json",
    "Affair": "affair.schema.json",
    "Interest": "interest.schema.json",
    "Resource": "resource.schema.json",
    "Signal": "signal.schema.json",
    "Mission": "mission.schema.json",
    "Protocol": "protocol.schema.json",
    "Operation": "operation.schema.json",
    "Routine": "routine.schema.json",
    "Regimen": "regimen.schema.json",
    "Review": "review.schema.json",
    "Artifact": "artifact.schema.json",
}
