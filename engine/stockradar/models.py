from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class DataGrade(str, Enum):
    DECISION_GRADE = "DECISION_GRADE"
    RESEARCH_GRADE = "RESEARCH_GRADE"
    INSUFFICIENT = "INSUFFICIENT"
    STALE = "STALE"
    MOCK = "MOCK"


class MarketRegime(str, Enum):
    GREEN = "GREEN"
    YELLOW = "YELLOW"
    RED = "RED"
    UNKNOWN = "UNKNOWN"


class SetupState(str, Enum):
    WATCH = "WATCH"
    NEAR_TRIGGER = "NEAR_TRIGGER"
    READY = "READY"
    TRIGGERED = "TRIGGERED"
    INVALIDATED = "INVALIDATED"
    EXTENDED = "EXTENDED"
    EXPIRED = "EXPIRED"


@dataclass(frozen=True)
class Exclusion:
    ticker: str
    reason: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Exclusion":
        return cls(ticker=str(value["ticker"]), reason=str(value["reason"]))


@dataclass(frozen=True)
class UniverseSnapshot:
    snapshot_id: str
    as_of: str
    source_timestamp: str
    exchange: str
    expected_total: int
    scanned_count: int
    valid_count: int
    excluded_count: int
    stale_count: int
    missing_count: int
    data_grade: DataGrade
    same_snapshot: bool
    adjusted_basis_consistent: bool
    corporate_action_checked: bool
    source: str
    exclusion_log: tuple[Exclusion, ...] = field(default_factory=tuple)
    correction_of: str | None = None

    @property
    def universe_coverage_pct(self) -> float:
        if self.expected_total <= 0:
            return 0.0
        return round(self.scanned_count / self.expected_total * 100, 2)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "UniverseSnapshot":
        return cls(
            snapshot_id=str(value["snapshot_id"]),
            as_of=str(value["as_of"]),
            source_timestamp=str(value["source_timestamp"]),
            exchange=str(value.get("exchange", "HOSE")),
            expected_total=int(value["expected_total"]),
            scanned_count=int(value["scanned_count"]),
            valid_count=int(value["valid_count"]),
            excluded_count=int(value["excluded_count"]),
            stale_count=int(value.get("stale_count", 0)),
            missing_count=int(value.get("missing_count", 0)),
            data_grade=DataGrade(value["data_grade"]),
            same_snapshot=bool(value.get("same_snapshot", False)),
            adjusted_basis_consistent=bool(value.get("adjusted_basis_consistent", False)),
            corporate_action_checked=bool(value.get("corporate_action_checked", False)),
            source=str(value.get("source", "UNKNOWN")),
            exclusion_log=tuple(Exclusion.from_dict(item) for item in value.get("exclusion_log", [])),
            correction_of=value.get("correction_of"),
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["data_grade"] = self.data_grade.value
        value["universe_coverage_pct"] = self.universe_coverage_pct
        return value


@dataclass(frozen=True)
class Candidate:
    ticker: str
    score: float
    score_coverage_pct: float
    setup: str
    state: SetupState
    previous_state: SetupState | None
    market_regime: MarketRegime
    current_price: float | None
    pivot: float | None
    distance_to_pivot_pct: float | None
    extension_pct: float | None
    liquidity_pass: bool
    event_risk_pass: bool
    reason: str
    evidence: tuple[str, ...] = field(default_factory=tuple)
    is_mock: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Candidate":
        previous = value.get("previous_state")
        return cls(
            ticker=str(value["ticker"]),
            score=float(value["score"]),
            score_coverage_pct=float(value.get("score_coverage_pct", 100)),
            setup=str(value["setup"]),
            state=SetupState(value["state"]),
            previous_state=SetupState(previous) if previous else None,
            market_regime=MarketRegime(value.get("market_regime", "UNKNOWN")),
            current_price=float(value["current_price"]) if value.get("current_price") is not None else None,
            pivot=float(value["pivot"]) if value.get("pivot") is not None else None,
            distance_to_pivot_pct=(
                float(value["distance_to_pivot_pct"])
                if value.get("distance_to_pivot_pct") is not None
                else None
            ),
            extension_pct=float(value["extension_pct"]) if value.get("extension_pct") is not None else None,
            liquidity_pass=bool(value.get("liquidity_pass", False)),
            event_risk_pass=bool(value.get("event_risk_pass", False)),
            reason=str(value.get("reason", "")),
            evidence=tuple(str(item) for item in value.get("evidence", [])),
            is_mock=bool(value.get("is_mock", False)),
        )

    @property
    def state_change(self) -> str:
        if self.previous_state is None or self.previous_state == self.state:
            return "UNCHANGED"
        return f"{self.previous_state.value}→{self.state.value}"

    def to_dict(self, rank: int | None = None) -> dict[str, Any]:
        value = asdict(self)
        value["state"] = self.state.value
        value["previous_state"] = self.previous_state.value if self.previous_state else None
        value["market_regime"] = self.market_regime.value
        value["state_change"] = self.state_change
        if rank is not None:
            value["rank"] = rank
        return value

