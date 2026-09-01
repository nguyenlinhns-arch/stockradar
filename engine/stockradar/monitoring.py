from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .ticker_lookup import normalize_ticker


@dataclass(frozen=True)
class MonitoringReason:
    recommendation: bool = False
    near_trigger: bool = False
    trial_subscribers: int = 0
    paid_subscribers: int = 0

    @property
    def subscriber_count(self) -> int:
        return self.trial_subscribers + self.paid_subscribers

    @property
    def priority(self) -> int:
        return (
            (100 if self.recommendation else 0)
            + (50 if self.near_trigger else 0)
            + min(self.subscriber_count, 49)
        )


def deduplicate_subscribers(rows: Iterable[tuple[str, str]]) -> dict[str, set[str]]:
    """Return one monitoring key per ticker and the unique subscribers to fan out to."""
    result: dict[str, set[str]] = {}
    for ticker, user_id in rows:
        result.setdefault(normalize_ticker(ticker), set()).add(str(user_id))
    return result


def build_active_intraday_universe(
    active_recommendations: Iterable[str],
    near_trigger: Iterable[str],
    trial_watchlists: Iterable[str],
    paid_watchlists: Iterable[str],
) -> dict[str, MonitoringReason]:
    reasons: dict[str, dict[str, int | bool]] = {}

    def row(ticker: str) -> dict[str, int | bool]:
        return reasons.setdefault(
            normalize_ticker(ticker),
            {"recommendation": False, "near_trigger": False, "trial_subscribers": 0, "paid_subscribers": 0},
        )

    for ticker in active_recommendations:
        row(ticker)["recommendation"] = True
    for ticker in near_trigger:
        row(ticker)["near_trigger"] = True
    for ticker in trial_watchlists:
        current = row(ticker)
        current["trial_subscribers"] = int(current["trial_subscribers"]) + 1
    for ticker in paid_watchlists:
        current = row(ticker)
        current["paid_subscribers"] = int(current["paid_subscribers"]) + 1

    return {ticker: MonitoringReason(**value) for ticker, value in reasons.items()}
