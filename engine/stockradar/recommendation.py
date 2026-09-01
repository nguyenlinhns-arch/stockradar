from __future__ import annotations

from dataclasses import dataclass

from .models import DataGrade, Horizon, RecommendationStatus


@dataclass(frozen=True)
class RecommendationGateInput:
    horizon: Horizon
    data_grade: DataGrade
    stale: bool
    horizon_score: float | None
    score_threshold: float
    score_coverage_pct: float
    minimum_coverage_pct: float
    liquidity_pass: bool
    event_risk_pass: bool
    extension_pass: bool
    market_pass: bool
    evidence_pass: bool
    horizon_consistent: bool
    unresolved_contradictions: int
    entry_valid: bool | None = None
    target_valid: bool | None = None
    stop_or_risk_valid: bool | None = None
    risk_reward: float | None = None
    minimum_risk_reward: float = 2.0


@dataclass(frozen=True)
class RecommendationGateResult:
    can_publish: bool
    public_state: RecommendationStatus
    failures: tuple[str, ...]


def evaluate_recommendation_gate(value: RecommendationGateInput) -> RecommendationGateResult:
    failures: list[str] = []
    if value.data_grade is not DataGrade.DECISION_GRADE:
        failures.append("data_grade")
    if value.stale:
        failures.append("stale")
    if value.horizon_score is None or value.horizon_score < value.score_threshold:
        failures.append("horizon_score")
    if value.score_coverage_pct < value.minimum_coverage_pct:
        failures.append("score_coverage")

    checks = {
        "liquidity": value.liquidity_pass,
        "event_risk": value.event_risk_pass,
        "extension": value.extension_pass,
        "market": value.market_pass,
        "evidence": value.evidence_pass,
        "horizon": value.horizon_consistent,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    if value.unresolved_contradictions:
        failures.append("contradiction")

    if value.horizon in {Horizon.SHORT_TERM, Horizon.MEDIUM_TERM}:
        tactical_checks = {
            "entry": value.entry_valid is True,
            "target": value.target_valid is True,
            "stop_or_risk": value.stop_or_risk_valid is True,
        }
        failures.extend(name for name, passed in tactical_checks.items() if not passed)
        if value.risk_reward is None or value.risk_reward < value.minimum_risk_reward:
            failures.append("risk_reward")

    if not failures:
        return RecommendationGateResult(
            can_publish=True,
            public_state=RecommendationStatus.UNACTIVATED,
            failures=(),
        )

    watch_failures = {"data_grade", "stale", "market", "evidence", "contradiction", "horizon"}
    state = RecommendationStatus.WATCH if watch_failures.intersection(failures) else RecommendationStatus.WAIT_BUY
    return RecommendationGateResult(can_publish=False, public_state=state, failures=tuple(failures))
