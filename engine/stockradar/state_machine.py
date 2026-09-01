from __future__ import annotations

from dataclasses import dataclass

from .models import SetupState


ALLOWED_TRANSITIONS: dict[SetupState, frozenset[SetupState]] = {
    SetupState.WATCH: frozenset(
        {SetupState.WATCH, SetupState.NEAR_TRIGGER, SetupState.INVALIDATED, SetupState.EXPIRED}
    ),
    SetupState.NEAR_TRIGGER: frozenset(
        {
            SetupState.WATCH,
            SetupState.NEAR_TRIGGER,
            SetupState.READY,
            SetupState.INVALIDATED,
            SetupState.EXTENDED,
            SetupState.EXPIRED,
        }
    ),
    SetupState.READY: frozenset(
        {
            SetupState.NEAR_TRIGGER,
            SetupState.READY,
            SetupState.TRIGGERED,
            SetupState.INVALIDATED,
            SetupState.EXTENDED,
            SetupState.EXPIRED,
        }
    ),
    SetupState.TRIGGERED: frozenset(
        {
            SetupState.TRIGGERED,
            SetupState.INVALIDATED,
            SetupState.EXTENDED,
            SetupState.EXPIRED,
        }
    ),
    SetupState.INVALIDATED: frozenset({SetupState.INVALIDATED, SetupState.EXPIRED}),
    SetupState.EXTENDED: frozenset(
        {SetupState.EXTENDED, SetupState.READY, SetupState.INVALIDATED, SetupState.EXPIRED}
    ),
    SetupState.EXPIRED: frozenset({SetupState.EXPIRED}),
}


@dataclass(frozen=True)
class SetupFacts:
    invalidated: bool = False
    expired: bool = False
    extension_pct: float | None = None
    extension_limit_pct: float = 5.0
    trigger_confirmed: bool = False
    trigger_ready: bool = False
    distance_to_trigger_pct: float | None = None
    near_trigger_limit_pct: float = 3.0


def validate_transition(previous: SetupState, current: SetupState) -> None:
    if current not in ALLOWED_TRANSITIONS[previous]:
        raise ValueError(f"Invalid setup-state transition: {previous.value}→{current.value}")


def derive_state(facts: SetupFacts) -> SetupState:
    if facts.invalidated:
        return SetupState.INVALIDATED
    if facts.expired:
        return SetupState.EXPIRED
    if facts.extension_pct is not None and facts.extension_pct > facts.extension_limit_pct:
        return SetupState.EXTENDED
    if facts.trigger_confirmed:
        return SetupState.TRIGGERED
    if facts.trigger_ready:
        return SetupState.READY
    if (
        facts.distance_to_trigger_pct is not None
        and 0 <= facts.distance_to_trigger_pct <= facts.near_trigger_limit_pct
    ):
        return SetupState.NEAR_TRIGGER
    return SetupState.WATCH

