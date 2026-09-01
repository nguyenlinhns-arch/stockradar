from __future__ import annotations

from dataclasses import dataclass

from .models import DataGrade, MarketRegime


@dataclass(frozen=True)
class BuyGateInput:
    data_grade: DataGrade
    market_regime: MarketRegime
    setup_pass: bool
    score_coverage_pass: bool
    trigger_pass: bool
    volume_pass: bool
    extension_pass: bool
    liquidity_pass: bool
    event_risk_pass: bool
    corporate_action_pass: bool
    rr: float | None
    stop_exists: bool
    horizon_consistent: bool
    execution_pass: bool
    portfolio_pass: bool | None = None


@dataclass(frozen=True)
class BuyGateResult:
    action: str
    passed: bool
    failures: tuple[str, ...]


def evaluate_buy_gate(value: BuyGateInput) -> BuyGateResult:
    failures: list[str] = []
    if value.data_grade is not DataGrade.DECISION_GRADE:
        failures.append("data_grade")
    if value.market_regime in {MarketRegime.RED, MarketRegime.UNKNOWN}:
        failures.append("market_regime")
    checks = {
        "setup": value.setup_pass,
        "score_coverage": value.score_coverage_pass,
        "trigger": value.trigger_pass,
        "volume": value.volume_pass,
        "extension": value.extension_pass,
        "liquidity": value.liquidity_pass,
        "event_risk": value.event_risk_pass,
        "corporate_action": value.corporate_action_pass,
        "stop": value.stop_exists,
        "horizon": value.horizon_consistent,
        "execution": value.execution_pass,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    if value.rr is None or value.rr < 2:
        failures.append("risk_reward")
    if value.portfolio_pass is False:
        failures.append("portfolio")

    if not failures:
        return BuyGateResult(action="MUA", passed=True, failures=())
    if "data_grade" in failures:
        action = "RESEARCH ONLY"
    elif "market_regime" in failures:
        action = "THEO DÕI"
    else:
        action = "CHỜ MUA"
    return BuyGateResult(action=action, passed=False, failures=tuple(failures))


def signal_is_current(
    signal_snapshot_id: str,
    current_snapshot_id: str,
    price_still_in_plan: bool,
    market_changed: bool,
    material_event: bool,
) -> bool:
    return (
        signal_snapshot_id == current_snapshot_id
        and price_still_in_plan
        and not market_changed
        and not material_event
    )

