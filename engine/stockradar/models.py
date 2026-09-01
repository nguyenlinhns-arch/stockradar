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


class Horizon(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    MEDIUM_TERM = "MEDIUM_TERM"
    LONG_TERM = "LONG_TERM"
    ACCUMULATION = "ACCUMULATION"


class RecommendationStatus(str, Enum):
    WATCH = "WATCH"
    WAIT_BUY = "WAIT_BUY"
    UNACTIVATED = "UNACTIVATED"
    ACTIVATED = "ACTIVATED"
    IN_BUY_ZONE = "IN_BUY_ZONE"
    ACTIVE = "ACTIVE"
    EXTENDED = "EXTENDED"
    INVALIDATED = "INVALIDATED"
    TARGET_REACHED = "TARGET_REACHED"
    STOP_REACHED = "STOP_REACHED"
    EXPIRED = "EXPIRED"
    CLOSED = "CLOSED"


class RecommendationMode(str, Enum):
    INTERNAL = "INTERNAL"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    COMPLIANCE_REVIEW = "COMPLIANCE_REVIEW"
    PRODUCTION_APPROVED = "PRODUCTION_APPROVED"


class TrackRecordMode(str, Enum):
    BACKTEST = "BACKTEST"
    SHADOW = "SHADOW"
    LIVE_PUBLISHED = "LIVE_PUBLISHED"


class ReviewStatus(str, Enum):
    PENDING = "PENDING"
    DUE = "DUE"
    COMPLETED = "COMPLETED"
    OVERDUE = "OVERDUE"


class ReviewDecision(str, Enum):
    CONTINUE = "CONTINUE"
    ADJUST = "ADJUST"
    NO_LONGER_ELIGIBLE = "NO_LONGER_ELIGIBLE"
    CLOSE = "CLOSE"


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


@dataclass(frozen=True)
class Recommendation:
    recommendation_id: str
    ticker: str
    company_name: str
    sector: str
    horizon: Horizon
    publication_date: str
    publication_time: str
    snapshot_id: str
    market_regime: MarketRegime
    stock_score: float
    score_coverage_pct: float
    rank: int
    recommendation_state: RecommendationStatus
    recommended_buy_low: float | None
    recommended_buy_high: float | None
    price_at_publication: float | None
    current_price: float | None
    target_price: float | None
    risk_level: str
    stop_loss: float | None
    upside_pct: float | None
    downside_pct: float | None
    risk_reward: float | None
    expiry_date: str | None
    thesis: tuple[str, ...]
    risks: tuple[str, ...]
    invalidation_conditions: tuple[str, ...]
    evidence: tuple[str, ...]
    data_grade: DataGrade
    status: str
    generated_at: str
    published_at: str
    system_version: str
    score_version: str
    publish_status: str
    record_mode: TrackRecordMode
    activation_timestamp: str | None = None
    performance_entry_price: float | None = None
    current_return_pct: float | None = None
    absolute_return: float | None = None
    close_price: float | None = None
    close_timestamp: str | None = None
    final_return_pct: float | None = None
    benchmark_return_pct: float | None = None
    sector_benchmark_return_pct: float | None = None
    excess_return_pct: float | None = None
    adjustment_basis: str = "UNADJUSTED"
    corporate_action_refs: tuple[str, ...] = field(default_factory=tuple)
    outcome: str | None = None
    closed_at: str | None = None
    close_reason: str | None = None
    review_due_at: str | None = None
    review_status: ReviewStatus = ReviewStatus.PENDING
    review_decision: ReviewDecision | None = None
    new_position_state: str = "NOT_ASSESSED"
    new_position_note: str = ""
    holding_state: str = "NOT_ASSESSED"
    holding_note: str = ""
    vnindex_at_activation: float | None = None
    vnindex_current_or_close: float | None = None
    is_mock: bool = False

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Recommendation":
        numeric_fields = {
            name: float(value[name]) if value.get(name) is not None else None
            for name in (
                "recommended_buy_low", "recommended_buy_high", "price_at_publication",
                "current_price", "target_price", "stop_loss", "upside_pct",
                "downside_pct", "risk_reward", "performance_entry_price",
                "current_return_pct", "absolute_return", "close_price",
                "final_return_pct", "benchmark_return_pct",
                "sector_benchmark_return_pct", "excess_return_pct",
                "vnindex_at_activation", "vnindex_current_or_close",
            )
        }
        if numeric_fields["price_at_publication"] is None and value.get("price_at_recommendation") is not None:
            numeric_fields["price_at_publication"] = float(value["price_at_recommendation"])
        return cls(
            recommendation_id=str(value["recommendation_id"]),
            ticker=str(value["ticker"]),
            company_name=str(value["company_name"]),
            sector=str(value["sector"]),
            horizon=Horizon(value["horizon"]),
            publication_date=str(value.get("publication_date", value.get("recommendation_date"))),
            publication_time=str(value.get("publication_time", value.get("recommendation_time"))),
            snapshot_id=str(value["snapshot_id"]),
            market_regime=MarketRegime(value["market_regime"]),
            stock_score=float(value["stock_score"]),
            score_coverage_pct=float(value.get("score_coverage_pct", 0)),
            rank=int(value["rank"]),
            recommendation_state=RecommendationStatus(value["recommendation_state"]),
            risk_level=str(value["risk_level"]),
            expiry_date=value.get("expiry_date"),
            thesis=tuple(str(item) for item in value.get("thesis", [])),
            risks=tuple(str(item) for item in value.get("risks", [])),
            invalidation_conditions=tuple(str(item) for item in value.get("invalidation_conditions", [])),
            evidence=tuple(str(item) for item in value.get("evidence", [])),
            data_grade=DataGrade(value["data_grade"]),
            status=str(value.get("status", "OPEN")),
            generated_at=str(value.get("generated_at", value.get("published_at", ""))),
            published_at=str(value.get("published_at", "")),
            system_version=str(value.get("system_version", "V2-DEMO")),
            score_version=str(value.get("score_version", "V2-DEMO")),
            publish_status=str(value.get("publish_status", "DEMO_ONLY")),
            record_mode=TrackRecordMode(value.get("record_mode", "SHADOW")),
            activation_timestamp=value.get("activation_timestamp"),
            close_timestamp=value.get("close_timestamp"),
            adjustment_basis=str(value.get("adjustment_basis", "UNADJUSTED")),
            corporate_action_refs=tuple(str(item) for item in value.get("corporate_action_refs", [])),
            outcome=value.get("outcome"),
            closed_at=value.get("closed_at"),
            close_reason=value.get("close_reason"),
            review_due_at=value.get("review_due_at", value.get("review_due_date")),
            review_status=ReviewStatus(value.get("review_status", "PENDING")),
            review_decision=(
                ReviewDecision(value["review_decision"])
                if value.get("review_decision") else None
            ),
            new_position_state=str(value.get("new_position_state", "NOT_ASSESSED")),
            new_position_note=str(value.get("new_position_note", "")),
            holding_state=str(value.get("holding_state", "NOT_ASSESSED")),
            holding_note=str(value.get("holding_note", "")),
            is_mock=bool(value.get("is_mock", False)),
            **numeric_fields,
        )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["horizon"] = self.horizon.value
        value["market_regime"] = self.market_regime.value
        value["recommendation_state"] = self.recommendation_state.value
        value["data_grade"] = self.data_grade.value
        value["record_mode"] = self.record_mode.value
        value["review_status"] = self.review_status.value
        value["review_decision"] = self.review_decision.value if self.review_decision else None
        return value

    @property
    def is_activated(self) -> bool:
        return self.activation_timestamp is not None and self.performance_entry_price is not None

    @property
    def is_closed(self) -> bool:
        return self.close_timestamp is not None and self.close_price is not None
