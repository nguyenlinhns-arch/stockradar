from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Sequence
from datetime import datetime
from statistics import mean, median
from math import isfinite


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


def live_publication_summary(records: Sequence[dict], minimum_closed: int = 20) -> dict:
    """Describe the complete released cohort; never mix replay or email history with live results.

    Twenty closed observations is a display floor, not a claim of statistical significance.
    Portfolio drawdown needs a marked equity series; independent trade returns cannot supply it.
    """
    rows = [r for r in records if r.get('record_mode') == 'LIVE_PUBLISHED'
            and r.get('publish_status') == 'PUBLISHED' and r.get('data_grade') == 'DECISION_GRADE'
            and r.get('is_mock') is False and r.get('published_at') and r.get('snapshot_id')]
    ids = [r.get('recommendation_id') for r in rows]
    if any(not value for value in ids) or len(set(ids)) != len(ids):
        raise PerformanceError('Live performance requires unique recommendation IDs')
    closed = [r for r in rows if r.get('activation_timestamp') and r.get('close_timestamp')
              and r.get('close_price') is not None and r.get('final_return_pct') is not None]
    returns = [float(r['final_return_pct']) for r in closed]
    if not all(isfinite(value) for value in returns):
        raise PerformanceError('Non-finite realized return')
    gains = [v for v in returns if v > 0]
    losses = [v for v in returns if v < 0]
    holding = []
    for r in closed:
        start = datetime.fromisoformat(r['activation_timestamp'].replace('Z', '+00:00'))
        end = datetime.fromisoformat(r['close_timestamp'].replace('Z', '+00:00'))
        if start.tzinfo is None or end.tzinfo is None or end < start:
            raise PerformanceError('Invalid realized holding window')
        holding.append((end - start).total_seconds() / 86400)
    enough = len(closed) >= minimum_closed
    average = lambda values: round(mean(values), 4) if enough and values else None
    return {
        'record_mode': 'LIVE_PUBLISHED', 'total_published': len(rows), 'closed': len(closed),
        'unactivated': sum(not r.get('activation_timestamp') for r in rows),
        'open': sum(bool(r.get('activation_timestamp')) and not r.get('close_timestamp') for r in rows),
        'wins': len(gains), 'losses': len(losses), 'breakeven': returns.count(0),
        'sample_status': 'DESCRIPTIVE_ONLY' if enough else 'INSUFFICIENT_SAMPLE',
        'minimum_closed': minimum_closed, 'win_rate_denominator': len(closed),
        'win_rate_pct': round(len(gains) / len(closed) * 100, 2) if enough else None,
        'average_gain_pct': average(gains), 'average_loss_pct': average(losses),
        'expectancy_pct': average(returns),
        'payoff_ratio': round(mean(gains) / abs(mean(losses)), 4) if enough and gains and losses else None,
        'median_holding_days': round(median(holding), 2) if enough and holding else None,
        'average_excess_return_pct': average([float(r['excess_return_pct']) for r in closed if r.get('excess_return_pct') is not None]),
        'max_drawdown_pct': None, 'drawdown_status': 'EQUITY_CURVE_REQUIRED',
        'excluded_records': len(records) - len(rows),
    }
