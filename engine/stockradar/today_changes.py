from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


SIGNIFICANT_EVENT_TYPES = {
    "TOP_ENTERED", "TOP_EXITED", "SCORE_CHANGED", "STATE_CHANGED",
    "PUBLISHED", "INVALIDATED", "ACTIVATED", "EXTENDED",
    "TARGET_REACHED", "STOP_REACHED", "MARKET_REGIME_CHANGED", "CLOSED",
}


@dataclass(frozen=True)
class ChangeEvent:
    event_id: str
    ticker: str | None
    event_type: str
    occurred_at: str
    title: str
    summary: str
    importance: int
    previous_value: str | None = None
    new_value: str | None = None


def today_changes(events: Iterable[ChangeEvent], limit: int = 12) -> list[ChangeEvent]:
    meaningful = [
        event for event in events
        if event.event_type in SIGNIFICANT_EVENT_TYPES and event.importance >= 2
    ]
    return sorted(meaningful, key=lambda event: (event.occurred_at, event.importance), reverse=True)[:limit]
