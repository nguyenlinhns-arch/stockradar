from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalibrationEvidence:
    probability_pct: float
    sample_size: int
    method: str
    oos: bool
    same_setup: bool
    same_regime: bool
    same_horizon: bool
    same_universe: bool
    costs_included: bool


def publishable_probability(evidence: CalibrationEvidence | None) -> float | None:
    if evidence is None:
        return None
    if not (0 <= evidence.probability_pct <= 100) or evidence.sample_size <= 0 or not evidence.method.strip():
        return None
    gates = (
        evidence.oos,
        evidence.same_setup,
        evidence.same_regime,
        evidence.same_horizon,
        evidence.same_universe,
        evidence.costs_included,
    )
    return evidence.probability_pct if all(gates) else None

