from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence


class PerformanceError(ValueError):
    pass


class CorporateActionType(str, Enum):
    CASH_DIVIDEND = "CASH_DIVIDEND"
    STOCK_SPLIT = "STOCK_SPLIT"
    STOCK_DIVIDEND = "STOCK_DIVIDEND"
    BONUS_SHARE = "BONUS_SHARE"
    RIGHTS_ISSUE = "RIGHTS_ISSUE"
    OTHER = "OTHER"


@dataclass(frozen=True)
class PriceBar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class ActivationResult:
    activated: bool
    activation_timestamp: str | None
    performance_entry_price: float | None
    method: str


@dataclass(frozen=True)
class CorporateAction:
    action_id: str
    action_type: CorporateActionType
    effective_at: str
    price_factor: float = 1.0
    cash_per_share: float = 0.0
    resolved: bool = True


@dataclass(frozen=True)
class ReturnResult:
    price_return_pct: float
    total_return_pct: float
    absolute_change: float
    adjusted_entry_price: float
    cash_distributions: float


def activate_on_first_eligible_bar(
    publication_timestamp: str,
    buy_low: float,
    buy_high: float,
    bars: Sequence[PriceBar],
) -> ActivationResult:
    if buy_low <= 0 or buy_high <= 0 or buy_low > buy_high:
        raise PerformanceError("Invalid recommended buy zone")

    for bar in sorted(bars, key=lambda item: item.timestamp):
        if bar.timestamp <= publication_timestamp:
            continue
        if not (0 < bar.low <= bar.high and bar.low <= bar.open <= bar.high):
            raise PerformanceError("Invalid OHLC bar")
        if bar.high < buy_low or bar.low > buy_high:
            continue

        if buy_low <= bar.open <= buy_high:
            entry = bar.open
            method = "FIRST_ELIGIBLE_BAR_OPEN_IN_ZONE"
        elif bar.open < buy_low and bar.high >= buy_low:
            entry = buy_low
            method = "FIRST_TOUCH_LOWER_BOUND"
        elif bar.open > buy_high and bar.low <= buy_high:
            entry = buy_high
            method = "FIRST_TOUCH_UPPER_BOUND"
        else:
            raise PerformanceError("OHLC path cannot resolve a deterministic first touch")

        return ActivationResult(True, bar.timestamp, round(entry, 6), method)

    return ActivationResult(False, None, None, "NO_POST_PUBLICATION_TRADE_IN_ZONE")


def calculate_return(
    performance_entry_price: float,
    exit_or_current_price: float,
    corporate_actions: Sequence[CorporateAction] = (),
) -> ReturnResult:
    if performance_entry_price <= 0 or exit_or_current_price <= 0:
        raise PerformanceError("Prices must be positive")

    factor = 1.0
    cash = 0.0
    for action in sorted(corporate_actions, key=lambda item: item.effective_at):
        if not action.resolved or action.action_type in {CorporateActionType.RIGHTS_ISSUE, CorporateActionType.OTHER}:
            raise PerformanceError(f"Unresolved corporate action: {action.action_id}")
        if action.price_factor <= 0 or action.cash_per_share < 0:
            raise PerformanceError(f"Invalid corporate action: {action.action_id}")
        factor *= action.price_factor
        cash += action.cash_per_share

    adjusted_entry = performance_entry_price * factor
    price_return = (exit_or_current_price / adjusted_entry - 1) * 100
    total_return = ((exit_or_current_price + cash) / adjusted_entry - 1) * 100
    return ReturnResult(
        price_return_pct=round(price_return, 2),
        total_return_pct=round(total_return, 2),
        absolute_change=round(exit_or_current_price - adjusted_entry, 6),
        adjusted_entry_price=round(adjusted_entry, 6),
        cash_distributions=round(cash, 6),
    )


def calculate_excess_return(stock_return_pct: float, benchmark_return_pct: float) -> float:
    return round(stock_return_pct - benchmark_return_pct, 2)
