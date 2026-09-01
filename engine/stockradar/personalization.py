from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable

from .models import Horizon
from .ticker_lookup import normalize_ticker


class AccountTier(str, Enum):
    PUBLIC = "PUBLIC"
    FREE = "FREE"
    TRIAL = "TRIAL"
    PAID = "PAID"


class EmailKind(str, Enum):
    TRANSACTIONAL = "TRANSACTIONAL"
    PRODUCT_DAILY = "PRODUCT_DAILY"
    PRODUCT_ALERT = "PRODUCT_ALERT"
    PRODUCT_WEEKLY = "PRODUCT_WEEKLY"
    MARKETING = "MARKETING"


WATCHLIST_LIMITS = {
    AccountTier.PUBLIC: 0,
    AccountTier.FREE: 3,
    AccountTier.TRIAL: 3,
    AccountTier.PAID: 20,
}


def can_receive_email(
    tier: AccountTier,
    kind: EmailKind,
    *,
    email_verified: bool,
    product_consent: bool = False,
    marketing_consent: bool = False,
) -> bool:
    if kind is EmailKind.TRANSACTIONAL:
        return True
    if not email_verified:
        return False
    if kind is EmailKind.MARKETING:
        return marketing_consent
    return tier in {AccountTier.TRIAL, AccountTier.PAID} and product_consent


def enforce_watchlist_limit(tier: AccountTier, existing_tickers: Iterable[str], new_ticker: str) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(normalize_ticker(item) for item in existing_tickers))
    ticker = normalize_ticker(new_ticker)
    if ticker in normalized:
        return normalized
    limit = WATCHLIST_LIMITS[tier]
    if len(normalized) >= limit:
        raise ValueError(f"WATCHLIST_LIMIT_REACHED:{limit}")
    return (*normalized, ticker)


@dataclass(frozen=True)
class UserPreferences:
    horizons: tuple[Horizon, ...]
    sectors: tuple[str, ...]
    tickers: tuple[str, ...]

    @classmethod
    def create(
        cls,
        horizons: Iterable[Horizon],
        sectors: Iterable[str],
        tickers: Iterable[str],
    ) -> "UserPreferences":
        horizon_values = tuple(dict.fromkeys(horizons))
        sector_values = tuple(dict.fromkeys(str(value).strip() for value in sectors if str(value).strip()))
        ticker_values = tuple(dict.fromkeys(normalize_ticker(value) for value in tickers))
        if not horizon_values:
            raise ValueError("At least one preferred horizon is required")
        if len(sector_values) > 3:
            raise ValueError("At most three preferred sectors are allowed during onboarding")
        if len(ticker_values) > 3:
            raise ValueError("At most three tickers are allowed during onboarding")
        return cls(horizon_values, sector_values, ticker_values)

    def prioritize(self, items: Iterable[dict[str, object]]) -> list[dict[str, object]]:
        horizons = {item.value for item in self.horizons}
        sectors = set(self.sectors)
        tickers = set(self.tickers)

        def score(item: dict[str, object]) -> tuple[int, str]:
            priority = 0
            priority += 4 if str(item.get("ticker", "")) in tickers else 0
            priority += 2 if str(item.get("horizon", "")) in horizons else 0
            priority += 1 if str(item.get("sector", "")) in sectors else 0
            return (-priority, str(item.get("ticker", "")))

        return sorted(items, key=score)
