from __future__ import annotations

from typing import Any, Mapping
from .ticker_symbol import is_valid_hose_ticker


HORIZONS = frozenset({"SHORT_TERM", "MEDIUM_TERM", "LONG_TERM", "ACCUMULATION"})


class ReportContractError(ValueError):
    pass


def _ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if not is_valid_hose_ticker(ticker):
        raise ReportContractError(f"invalid report ticker: {ticker!r}")
    return ticker


def _horizon(value: object) -> str:
    horizon = str(value or "").strip().upper()
    if horizon not in HORIZONS:
        raise ReportContractError(f"invalid report horizon: {horizon!r}")
    return horizon


def _nonempty_text(payload: Mapping[str, Any], key: str) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        raise ReportContractError(f"report {key} is required")
    return value


def _optional_number(payload: Mapping[str, Any], key: str) -> float | None:
    value = payload.get(key)
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ReportContractError(f"report {key} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ReportContractError(f"report {key} must be numeric") from error
    if number != number or number in (float("inf"), float("-inf")):
        raise ReportContractError(f"report {key} must be finite")
    return number


def _positive_if_present(payload: Mapping[str, Any], key: str) -> None:
    value = _optional_number(payload, key)
    if value is not None and value <= 0:
        raise ReportContractError(f"report {key} must be positive")


def _string_list_if_present(payload: Mapping[str, Any], key: str) -> None:
    value = payload.get(key)
    if value is None:
        return
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ReportContractError(f"report {key} must be a list of strings")


def validate_report_payload(
    payload: Mapping[str, Any],
    *,
    expected_ticker: str,
    expected_horizon: str,
) -> dict[str, Any]:
    result = dict(payload)
    ticker = _ticker(result.get("ticker"))
    horizon = _horizon(result.get("horizon"))
    if ticker != _ticker(expected_ticker):
        raise ReportContractError("report ticker does not match cache key")
    if horizon != _horizon(expected_horizon):
        raise ReportContractError("report horizon does not match cache key")

    if str(result.get("data_status") or "").strip().upper() != "READY":
        raise ReportContractError("production report data_status must be READY")
    if str(result.get("data_grade") or "").strip().upper() != "DECISION_GRADE":
        raise ReportContractError("production report data_grade must be DECISION_GRADE")

    _nonempty_text(result, "new_position_state")
    _nonempty_text(result, "holding_state")

    current_price = _optional_number(result, "current_price")
    if current_price is None or current_price <= 0:
        raise ReportContractError("report current_price must be positive")

    score = _optional_number(result, "score")
    if score is not None and not 0 <= score <= 100:
        raise ReportContractError("report score must be between 0 and 100")

    rvol = _optional_number(result, "rvol")
    if rvol is None:
        rvol = _optional_number(result, "volume_rvol")
    if rvol is not None and rvol < 0:
        raise ReportContractError("report RVOL must be non-negative")

    for key in (
        "stop_loss",
        "target_near",
        "target_price",
        "target_3_6m",
        "target_12m",
        "fair_value",
    ):
        _positive_if_present(result, key)

    buy_low = _optional_number(result, "buy_zone_low")
    buy_high = _optional_number(result, "buy_zone_high")
    if buy_low is None and isinstance(result.get("buy_zone"), list) and len(result["buy_zone"]) >= 2:
        try:
            buy_low = float(result["buy_zone"][0])
            buy_high = float(result["buy_zone"][1])
        except (TypeError, ValueError) as error:
            raise ReportContractError("report buy_zone values must be numeric") from error
    if (buy_low is None) != (buy_high is None):
        raise ReportContractError("report Buy Zone requires both low and high")
    if buy_low is not None:
        if buy_low <= 0 or buy_high is None or buy_high <= 0 or buy_low > buy_high:
            raise ReportContractError("report Buy Zone is invalid")

    upside = _optional_number(result, "upside_pct")
    if upside is not None and upside < 0:
        raise ReportContractError("report upside_pct must be non-negative")
    downside = _optional_number(result, "downside_pct")
    if downside is not None and downside > 0:
        raise ReportContractError("report downside_pct must be zero or negative")
    risk_reward = _optional_number(result, "risk_reward")
    if risk_reward is not None and risk_reward <= 0:
        raise ReportContractError("report risk_reward must be positive")

    calibrated = result.get("probability_calibrated") is True
    probability = _optional_number(result, "probability_pct")
    if probability is not None and not calibrated:
        raise ReportContractError("uncalibrated probability must not be published")
    if calibrated:
        if probability is None or not 0 <= probability <= 100:
            raise ReportContractError("calibrated probability_pct must be between 0 and 100")
        if result.get("probability_oos") is not True:
            raise ReportContractError("calibrated probability requires OOS evidence")
        _nonempty_text(result, "probability_method")
        sample_size = result.get("probability_sample_size")
        if isinstance(sample_size, bool):
            raise ReportContractError("probability_sample_size must be a positive integer")
        try:
            sample_size_int = int(sample_size)
        except (TypeError, ValueError) as error:
            raise ReportContractError("probability_sample_size must be a positive integer") from error
        if sample_size_int <= 0 or float(sample_size_int) != float(sample_size):
            raise ReportContractError("probability_sample_size must be a positive integer")
        _nonempty_text(result, "probability_scope")

    for key in ("thesis", "catalysts", "risks", "invalidation_conditions"):
        _string_list_if_present(result, key)

    return result
