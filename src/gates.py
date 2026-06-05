"""Deterministic War Gaming gates for the v0.1 ontology prototype."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

try:
    from .models import Affair, Interest, Mission, Resource
except ImportError:  # Allows `python src/validate.py` from the repo root.
    from models import Affair, Interest, Mission, Resource  # type: ignore[no-redef]


Recommendation = str


@dataclass(frozen=True)
class WarGameContext:
    mission: Mission
    affairs: list[Affair]
    interests: list[Interest]
    resources: list[Resource]


@dataclass(frozen=True)
class GateResult:
    name: str
    triggered: bool
    recommendation: Recommendation
    reasoning: str
    next_actions: tuple[str, ...]
    review_required: bool = False


class Gate(Protocol):
    name: str

    def evaluate(self, context: WarGameContext) -> GateResult:
        """Evaluate one deterministic gate."""


def _average(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _has_bounded_downside(interest: Interest) -> bool:
    text = interest.downside.lower()
    unbounded_terms = ("uncapped", "unlimited", "ruin", "catastrophic", "fatal")
    return not any(term in text for term in unbounded_terms)


class ErgodicityGate:
    name = "ErgodicityGate"

    def evaluate(self, context: WarGameContext) -> GateResult:
        ruin_affairs = [affair.name for affair in context.affairs if affair.ruin_risk]
        fragile_affairs = [
            affair.name
            for affair in context.affairs
            if affair.fragility_score >= 0.75 or affair.priority_score >= 0.9
        ]
        depleted_resources = [
            resource.name
            for resource in context.resources
            if resource.status in {"depleted", "impaired"} and resource.criticality_score >= 0.7
        ]
        high_death_spiral = context.mission.death_spiral_risk >= 0.65

        if ruin_affairs:
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Abort",
                reasoning=f"Ruin-risk affairs are exposed: {', '.join(ruin_affairs)}.",
                next_actions=(
                    "Pause mission expansion until ruin exposure is removed.",
                    "Create an explicit hedge plan for each ruin-risk affair.",
                ),
                review_required=True,
            )

        if fragile_affairs or depleted_resources or high_death_spiral:
            reasons = []
            if fragile_affairs:
                reasons.append(f"fragile high-priority affairs: {', '.join(fragile_affairs)}")
            if depleted_resources:
                reasons.append(f"critical impaired resources: {', '.join(depleted_resources)}")
            if high_death_spiral:
                reasons.append("mission death spiral risk is elevated")
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Hedge",
                reasoning="Sequence survival needs protection because " + "; ".join(reasons) + ".",
                next_actions=(
                    "Protect the base routine before increasing mission exposure.",
                    "Limit mission work to a recoverable daily allocation.",
                ),
                review_required=True,
            )

        return GateResult(
            name=self.name,
            triggered=False,
            recommendation="Review",
            reasoning="No ruin-risk affair or critical sequence survival constraint was detected.",
            next_actions=(),
        )


class ConvexityGate:
    name = "ConvexityGate"

    def evaluate(self, context: WarGameContext) -> GateResult:
        active_interests = [interest for interest in context.interests if interest.status == "active"]
        edge_interests = [
            interest
            for interest in active_interests
            if interest.end == "edge"
            and interest.convexity_score >= 0.7
            and interest.optionality_score >= 0.65
            and _has_bounded_downside(interest)
        ]
        unbounded_interests = [
            interest.name for interest in active_interests if not _has_bounded_downside(interest)
        ]

        if unbounded_interests:
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Abort",
                reasoning=f"Unbounded downside appears in interests: {', '.join(unbounded_interests)}.",
                next_actions=("Reclassify or kill interests with uncapped downside.",),
                review_required=True,
            )

        if edge_interests:
            names = ", ".join(interest.name for interest in edge_interests)
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Edge",
                reasoning=f"Bounded-downside, high-convexity interests support edge-taking: {names}.",
                next_actions=(
                    "Advance the highest-convexity interest with a small reversible bet.",
                    "Convert validated upside into mission roadmap updates.",
                ),
            )

        return GateResult(
            name=self.name,
            triggered=False,
            recommendation="Review",
            reasoning="No active interest met the convexity and optionality thresholds.",
            next_actions=("Review whether the mission has enough asymmetric upside to proceed.",),
            review_required=True,
        )


class JensenGate:
    name = "JensenGate"

    def evaluate(self, context: WarGameContext) -> GateResult:
        posture = str(context.mission.blueprint.get("volatility_exposure", "unknown")).lower()

        if posture in {"beneficial", "long", "helps"}:
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Edge",
                reasoning="Mission blueprint says volatility helps this exposure.",
                next_actions=("Prefer options that gain from variability without risking the base.",),
            )

        if posture in {"harmful", "short", "hurts"}:
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Hedge",
                reasoning="Mission blueprint says volatility hurts this exposure.",
                next_actions=("Reduce volatility exposure or add stabilizing routines.",),
                review_required=True,
            )

        return GateResult(
            name=self.name,
            triggered=False,
            recommendation="Review",
            reasoning="Volatility posture is not specified in the mission blueprint.",
            next_actions=("Specify whether volatility helps, hurts, or is neutral for this mission.",),
            review_required=True,
        )


class KellyGate:
    name = "KellyGate"

    def evaluate(self, context: WarGameContext) -> GateResult:
        exposure_size = context.mission.blueprint.get("exposure_size")
        if not isinstance(exposure_size, int | float):
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Review",
                reasoning="Mission blueprint does not define exposure_size.",
                next_actions=("Add a numeric exposure_size between 0 and 1 before execution.",),
                review_required=True,
            )

        average_resource_criticality = _average(
            [resource.criticality_score for resource in context.resources]
        )
        survivable_size = max(0.05, 0.35 - (context.mission.death_spiral_risk * 0.2))
        if average_resource_criticality >= 0.75:
            survivable_size -= 0.05

        if exposure_size > survivable_size:
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Hedge",
                reasoning=(
                    f"Exposure size {exposure_size:.2f} exceeds survivable size "
                    f"{survivable_size:.2f}."
                ),
                next_actions=("Reduce exposure size to the survivable range.",),
                review_required=True,
            )

        return GateResult(
            name=self.name,
            triggered=True,
            recommendation="Edge",
            reasoning=(
                f"Exposure size {exposure_size:.2f} is inside survivable size "
                f"{survivable_size:.2f}."
            ),
            next_actions=("Keep exposure small and increase only after review evidence improves.",),
        )


class AbortGate:
    name = "AbortGate"

    def evaluate(self, context: WarGameContext) -> GateResult:
        abort_condition = context.mission.blueprint.get("abort_condition")
        if context.mission.death_spiral_risk >= 0.8:
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Abort",
                reasoning="Mission death spiral risk is at or above the abort threshold.",
                next_actions=("Stop the mission and rebuild the base before reconsidering.",),
                review_required=True,
            )

        if not isinstance(abort_condition, str) or not abort_condition.strip():
            return GateResult(
                name=self.name,
                triggered=True,
                recommendation="Review",
                reasoning="Mission blueprint does not define a usable abort condition.",
                next_actions=("Write the abort condition before mission entry.",),
                review_required=True,
            )

        abort_text = abort_condition.strip().rstrip(".")
        return GateResult(
            name=self.name,
            triggered=True,
            recommendation="Edge",
            reasoning=f"Abort condition is defined: {abort_text}.",
            next_actions=("Review the abort condition at the next mission checkpoint.",),
        )


DEFAULT_GATES: tuple[Gate, ...] = (
    ErgodicityGate(),
    ConvexityGate(),
    JensenGate(),
    KellyGate(),
    AbortGate(),
)
