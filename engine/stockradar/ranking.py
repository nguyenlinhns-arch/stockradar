from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

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


def build_top_hose(
    snapshot: UniverseSnapshot,
    candidates: Iterable[Candidate],
    sector_by_ticker: Mapping[str, str],
    *,
    strongest_limit: int = 30,
    per_sector_limit: int = 3,
) -> dict[str, Any]:
    """Build buyer-facing HOSE rankings only from a complete decision-grade snapshot."""

    if strongest_limit <= 0 or per_sector_limit <= 0:
        raise ValueError("ranking limits must be positive")

    candidate_list = list(candidates)
    ranked = [candidate for candidate in rank_candidates(candidate_list) if not candidate.is_mock]
    gate = full_universe_gate(snapshot)
    failures = list(gate.failures)

    eligible_with_sector: list[Candidate] = []
    missing_sector: list[str] = []
    for candidate in ranked:
        sector = str(sector_by_ticker.get(candidate.ticker, "")).strip()
        if not sector:
            missing_sector.append(candidate.ticker)
            continue
        eligible_with_sector.append(candidate)
    if missing_sector:
        failures.append("eligible_candidate_sector_missing")

    ranking_valid = gate.passed and not missing_sector and bool(eligible_with_sector)
    if not ranking_valid:
        return {
            "schema_version": "3.0",
            "ranking_valid": False,
            "method_version": "STOCKRADAR_SCORE_V1",
            "snapshot": snapshot.to_dict(),
            "gate": {"passed": False, "failures": failures},
            "market_regime": "UNKNOWN",
            "strongest": [],
            "by_sector": [],
            "eligible_count": 0,
        }

    global_rank = {candidate.ticker: index for index, candidate in enumerate(eligible_with_sector, start=1)}

    def public_item(candidate: Candidate, *, sector_rank: int | None = None) -> dict[str, Any]:
        return {
            "ticker": candidate.ticker,
            "score": candidate.score,
            "rank": global_rank[candidate.ticker],
            "sector": str(sector_by_ticker[candidate.ticker]),
            "sector_rank": sector_rank,
            "state": candidate.state.value,
            "setup": candidate.setup,
            "current_price": candidate.current_price,
            "pivot": candidate.pivot,
            "distance_to_pivot_pct": candidate.distance_to_pivot_pct,
            "extension_pct": candidate.extension_pct,
            "reason": candidate.reason,
        }

    grouped: dict[str, list[Candidate]] = defaultdict(list)
    for candidate in eligible_with_sector:
        grouped[str(sector_by_ticker[candidate.ticker])].append(candidate)

    by_sector: list[dict[str, Any]] = []
    for sector in sorted(grouped):
        sector_items = grouped[sector][:per_sector_limit]
        by_sector.append({
            "sector": sector,
            "items": [public_item(candidate, sector_rank=index) for index, candidate in enumerate(sector_items, start=1)],
        })

    strongest = [public_item(candidate) for candidate in eligible_with_sector[:strongest_limit]]
    return {
        "schema_version": "3.0",
        "ranking_valid": True,
        "method_version": "STOCKRADAR_SCORE_V1",
        "snapshot": snapshot.to_dict(),
        "gate": {"passed": True, "failures": []},
        "market_regime": eligible_with_sector[0].market_regime.value,
        "strongest": strongest,
        "by_sector": by_sector,
        "eligible_count": len(eligible_with_sector),
    }


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
