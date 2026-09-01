from __future__ import annotations


ALLOWED_INTRADAY_METHODS = {"same_time_rvol", "projected_full_session"}


def validate_intraday_volume_method(method: str, methodology_note: str | None = None) -> None:
    if method not in ALLOWED_INTRADAY_METHODS:
        raise ValueError("Partial-session volume cannot be compared naively with full-day average")
    if method == "projected_full_session" and not (methodology_note or "").strip():
        raise ValueError("Projected full-session volume requires a documented method")

