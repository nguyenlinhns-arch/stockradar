from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import DataGrade, Horizon, RecommendationStatus, ReviewDecision


@dataclass(frozen=True)
class RecommendationGateInput:
    horizon: Horizon
    data_grade: DataGrade
    stale: bool
    horizon_score: float | None
    score_threshold: float
    score_coverage_pct: float
    minimum_coverage_pct: float
    liquidity_pass: bool
    event_risk_pass: bool
    extension_pass: bool
    market_pass: bool
    evidence_pass: bool
    horizon_consistent: bool
    unresolved_contradictions: int
    entry_valid: bool | None = None
    target_valid: bool | None = None
    stop_or_risk_valid: bool | None = None
    risk_reward: float | None = None
    minimum_risk_reward: float = 2.0


@dataclass(frozen=True)
class RecommendationGateResult:
    can_publish: bool
    public_state: RecommendationStatus
    failures: tuple[str, ...]


@dataclass(frozen=True)
class PositionAssessment:
    new_position_state: str
    new_position_note: str
    holding_state: str
    holding_note: str


def assess_new_and_holding_positions(
    *,
    price_extended: bool,
    thesis_intact: bool,
    holding_risk_triggered: bool,
) -> PositionAssessment:
    """Keep the new-buy question independent from the existing-holder question."""
    if not thesis_intact or holding_risk_triggered:
        return PositionAssessment(
            "KHÔNG PHÙ HỢP",
            "Không mở vị thế mới khi luận điểm hoặc điều kiện rủi ro không còn đạt.",
            "XEM XÉT GIẢM / THOÁT",
            "Đánh giá lại theo điều kiện vô hiệu; không suy diễn từ thứ hạng.",
        )
    if price_extended:
        return PositionAssessment(
            "KHÔNG MUA ĐUỔI",
            "Giá đã tăng quá vùng mua đã công bố.",
            "TIẾP TỤC THEO DÕI",
            "Không phù hợp mua mới không đồng nghĩa phải bán khi luận điểm còn nguyên.",
        )
    return PositionAssessment(
        "CHỜ CỔNG KHUYẾN NGHỊ",
        "Ranking không tự động tạo lệnh mua.",
        "TIẾP TỤC THEO DÕI",
        "Theo dõi mốc mục tiêu và điều kiện làm luận điểm xấu đi.",
    )


def review_is_due(review_due_at: str | None, *, now: datetime | None = None) -> bool:
    if not review_due_at:
        return True
    due = datetime.fromisoformat(review_due_at.replace("Z", "+00:00"))
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    current = now or datetime.now(timezone.utc)
    return current >= due


def recommendation_state_after_review(
    current: RecommendationStatus,
    decision: ReviewDecision,
) -> RecommendationStatus:
    if decision is ReviewDecision.CONTINUE:
        return current
    if decision is ReviewDecision.ADJUST:
        return RecommendationStatus.WATCH
    if decision is ReviewDecision.NO_LONGER_ELIGIBLE:
        return RecommendationStatus.INVALIDATED
    return RecommendationStatus.CLOSED


def empty_recommendation_publication() -> dict[str, object]:
    return {
        "published": False,
        "items": [],
        "message": "HÔM NAY KHÔNG CÓ KHUYẾN NGHỊ MỚI ĐẠT TIÊU CHUẨN.",
    }


def evaluate_recommendation_gate(value: RecommendationGateInput) -> RecommendationGateResult:
    failures: list[str] = []
    if value.data_grade is not DataGrade.DECISION_GRADE:
        failures.append("data_grade")
    if value.stale:
        failures.append("stale")
    if value.horizon_score is None or value.horizon_score < value.score_threshold:
        failures.append("horizon_score")
    if value.score_coverage_pct < value.minimum_coverage_pct:
        failures.append("score_coverage")

    checks = {
        "liquidity": value.liquidity_pass,
        "event_risk": value.event_risk_pass,
        "extension": value.extension_pass,
        "market": value.market_pass,
        "evidence": value.evidence_pass,
        "horizon": value.horizon_consistent,
    }
    failures.extend(name for name, passed in checks.items() if not passed)
    if value.unresolved_contradictions:
        failures.append("contradiction")

    if value.horizon in {Horizon.SHORT_TERM, Horizon.MEDIUM_TERM}:
        tactical_checks = {
            "entry": value.entry_valid is True,
            "target": value.target_valid is True,
            "stop_or_risk": value.stop_or_risk_valid is True,
        }
        failures.extend(name for name, passed in tactical_checks.items() if not passed)
        if value.risk_reward is None or value.risk_reward < value.minimum_risk_reward:
            failures.append("risk_reward")

    if not failures:
        return RecommendationGateResult(
            can_publish=True,
            public_state=RecommendationStatus.UNACTIVATED,
            failures=(),
        )

    watch_failures = {"data_grade", "stale", "market", "evidence", "contradiction", "horizon"}
    state = RecommendationStatus.WATCH if watch_failures.intersection(failures) else RecommendationStatus.WAIT_BUY
    return RecommendationGateResult(can_publish=False, public_state=state, failures=tuple(failures))
