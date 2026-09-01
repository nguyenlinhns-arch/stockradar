from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .models import Horizon


BUCKET_WEIGHTS: dict[str, float] = {
    "trend": 20,
    "vpa": 15,
    "sepa_canslim": 20,
    "relative_strength": 10,
    "fundamental": 15,
    "valuation": 10,
    "catalyst": 5,
    "risk_liquidity": 5,
}

HORIZON_BUCKET_WEIGHTS: dict[Horizon, dict[str, float]] = {
    Horizon.SHORT_TERM: dict(BUCKET_WEIGHTS),
    Horizon.MEDIUM_TERM: {
        "trend": 15, "vpa": 10, "sepa_canslim": 15, "relative_strength": 10,
        "fundamental": 20, "valuation": 10, "catalyst": 10, "risk_liquidity": 10,
    },
    Horizon.LONG_TERM: {
        "trend": 5, "vpa": 5, "sepa_canslim": 10, "relative_strength": 5,
        "fundamental": 30, "valuation": 20, "catalyst": 10, "risk_liquidity": 15,
    },
    Horizon.ACCUMULATION: {
        "trend": 5, "vpa": 0, "sepa_canslim": 5, "relative_strength": 0,
        "fundamental": 35, "valuation": 25, "catalyst": 5, "risk_liquidity": 25,
    },
}


class ScoringError(ValueError):
    pass


class DoubleCountError(ScoringError):
    pass


@dataclass(frozen=True)
class ScoreResult:
    confirmed_points: float
    score: float | None
    coverage_pct: float
    range_low: float
    range_high: float
    missing_buckets: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "confirmed_points": self.confirmed_points,
            "score": self.score,
            "coverage_pct": self.coverage_pct,
            "range": [self.range_low, self.range_high],
            "missing_buckets": list(self.missing_buckets),
            "score_is_probability": False,
        }


def calculate_score(
    bucket_scores: Mapping[str, float | None],
    evidence_ids: Mapping[str, Sequence[str]] | None = None,
) -> ScoreResult:
    return _calculate_score(bucket_scores, evidence_ids, BUCKET_WEIGHTS)


def calculate_horizon_score(
    horizon: Horizon,
    bucket_scores: Mapping[str, float | None],
    evidence_ids: Mapping[str, Sequence[str]] | None = None,
) -> ScoreResult:
    return _calculate_score(bucket_scores, evidence_ids, HORIZON_BUCKET_WEIGHTS[horizon])


def _calculate_score(
    bucket_scores: Mapping[str, float | None],
    evidence_ids: Mapping[str, Sequence[str]] | None,
    weights: Mapping[str, float],
) -> ScoreResult:
    unknown = set(bucket_scores) - set(weights)
    if unknown:
        raise ScoringError(f"Unknown score buckets: {sorted(unknown)}")

    evidence_ids = evidence_ids or {}
    owners: dict[str, str] = {}
    for bucket, ids in evidence_ids.items():
        if bucket not in weights:
            raise ScoringError(f"Unknown evidence bucket: {bucket}")
        for evidence_id in ids:
            previous = owners.get(evidence_id)
            if previous is not None and previous != bucket:
                raise DoubleCountError(
                    f"Evidence '{evidence_id}' is used by both '{previous}' and '{bucket}'"
                )
            owners[evidence_id] = bucket

    confirmed = 0.0
    covered_weight = 0.0
    missing: list[str] = []
    for bucket, maximum in weights.items():
        value = bucket_scores.get(bucket)
        if value is None:
            missing.append(bucket)
            continue
        numeric = float(value)
        if numeric < 0 or numeric > maximum:
            raise ScoringError(f"Bucket '{bucket}' must be between 0 and {maximum}")
        confirmed += numeric
        covered_weight += maximum

    confirmed = round(confirmed, 2)
    coverage_pct = round(covered_weight, 2)
    missing_capacity = sum(weights[name] for name in missing)
    exact_score = confirmed if not missing else None
    return ScoreResult(
        confirmed_points=confirmed,
        score=exact_score,
        coverage_pct=coverage_pct,
        range_low=confirmed,
        range_high=round(confirmed + missing_capacity, 2),
        missing_buckets=tuple(missing),
    )
