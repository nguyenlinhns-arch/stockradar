from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .models import Candidate, DataGrade, SetupState, UniverseSnapshot
from .state_machine import validate_transition


ELIGIBLE_STATES = {
    SetupState.WATCH,
    SetupState.NEAR_TRIGGER,
    SetupState.READY,
    SetupState.TRIGGERED,
}

STATE_PRIORITY = {
    SetupState.TRIGGERED: 4,
    SetupState.READY: 3,
    SetupState.NEAR_TRIGGER: 2,
    SetupState.WATCH: 1,
    SetupState.EXTENDED: 0,
    SetupState.INVALIDATED: -1,
    SetupState.EXPIRED: -2,
}


@dataclass(frozen=True)
class GateResult:
    passed: bool
    failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"passed": self.passed, "failures": list(self.failures)}


def full_universe_gate(snapshot: UniverseSnapshot) -> GateResult:
    failures: list[str] = []
    if snapshot.exchange != "HOSE":
        failures.append("exchange_not_hose")
    if snapshot.expected_total <= 0:
        failures.append("expected_universe_missing")
    if snapshot.scanned_count != snapshot.expected_total:
        failures.append("processed_universe_incomplete")
    if snapshot.valid_count + snapshot.excluded_count != snapshot.expected_total:
        failures.append("universe_reconciliation_failed")
    if len(snapshot.exclusion_log) != snapshot.excluded_count:
        failures.append("exclusion_log_incomplete")
    if snapshot.stale_count:
        failures.append("stale_records_present")
    if snapshot.missing_count:
        failures.append("missing_records_present")
    if not snapshot.same_snapshot:
        failures.append("same_snapshot_failed")
    if not snapshot.adjusted_basis_consistent:
        failures.append("adjusted_basis_conflict")
    if not snapshot.corporate_action_checked:
        failures.append("corporate_action_not_checked")
    if snapshot.data_grade is not DataGrade.DECISION_GRADE:
        failures.append("data_grade_not_decision_grade")
    if not snapshot.snapshot_id or not snapshot.as_of or not snapshot.source_timestamp:
        failures.append("snapshot_metadata_missing")
    return GateResult(passed=not failures, failures=tuple(failures))


def _is_eligible(candidate: Candidate) -> bool:
    return (
        candidate.state in ELIGIBLE_STATES
        and candidate.liquidity_pass
        and candidate.event_risk_pass
        and candidate.score_coverage_pct == 100
    )


def rank_candidates(candidates: Iterable[Candidate]) -> list[Candidate]:
    checked: list[Candidate] = []
    for candidate in candidates:
        if candidate.previous_state is not None:
            validate_transition(candidate.previous_state, candidate.state)
        if _is_eligible(candidate):
            checked.append(candidate)
    return sorted(
        checked,
        key=lambda item: (item.score, STATE_PRIORITY[item.state], item.ticker),
        reverse=True,
    )


def build_radar(
    snapshot: UniverseSnapshot,
    candidates: Iterable[Candidate],
    limit: int = 5,
) -> dict[str, Any]:
    candidate_list = list(candidates)
    ranked = rank_candidates(candidate_list)
    gate = full_universe_gate(snapshot)
    failures = list(gate.failures)
    if len(ranked) < limit:
        failures.append("fewer_than_requested_eligible_setups")

    top5_allowed = gate.passed and len(ranked) >= limit
    if top5_allowed:
        status = "TOP5_HOSE"
        display_name = "STOCKRADAR 5"
    elif snapshot.data_grade is DataGrade.MOCK:
        status = "SHORTLIST_FROM_AVAILABLE_DATA"
        display_name = "STOCKRADAR DEMO"
    else:
        status = "INCOMPLETE_UNIVERSE"
        display_name = "SHORTLIST FROM AVAILABLE DATA"

    selected = ranked[:limit]
    return {
        "schema_version": "1.0",
        "status": status,
        "display_name": display_name,
        "is_top5_hose": top5_allowed,
        "is_mock": snapshot.data_grade is DataGrade.MOCK or any(item.is_mock for item in selected),
        "snapshot": snapshot.to_dict(),
        "gate": {"passed": top5_allowed, "failures": failures},
        "market_regime": selected[0].market_regime.value if selected else "UNKNOWN",
        "items": [item.to_dict(rank=index) for index, item in enumerate(selected, start=1)],
        "excluded_candidate_count": len(candidate_list) - len(ranked),
        "legal_label": "Sàng lọc và theo dõi setup; không phải cam kết lợi nhuận.",
    }

