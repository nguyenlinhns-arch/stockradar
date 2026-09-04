from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

from .input_policy import computation_provenance
from .internal_features import (
    FundamentalFeatures,
    InternalValuationAssumptions,
    RawBar,
    RawFinancialPeriod,
    StockRadarResearchAssessment,
    TechnicalFeatures,
    ValuationFeatures,
    compute_fundamental_features,
    compute_market_regime,
    compute_technical_features,
    compute_valuation_features,
)
from .models import Candidate, SetupState, UniverseSnapshot
from .ranking import build_top_hose
from .scoring import calculate_score
from .state_machine import SetupFacts, derive_state


INTERNAL_ENGINE_VERSION = "STOCKRADAR_INTERNAL_V2"


@dataclass(frozen=True)
class InternalStockComputation:
    ticker: str
    sector: str
    candidate: Candidate
    technical: TechnicalFeatures
    fundamental: FundamentalFeatures
    valuation: ValuationFeatures
    bucket_scores: Mapping[str, float]
    computation: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "sector": self.sector,
            "candidate": self.candidate.to_dict(),
            "technical": self.technical.to_dict(),
            "fundamental": self.fundamental.to_dict(),
            "valuation": self.valuation.to_dict(),
            "bucket_scores": dict(self.bucket_scores),
            "computation": dict(self.computation),
            "engine_version": INTERNAL_ENGINE_VERSION,
        }


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _trend_score(features: TechnicalFeatures) -> float:
    checks = (
        features.close > features.ma50,
        features.ma50 > features.ma150,
        features.ma150 > features.ma200,
        features.ma200 > features.ma200_20d_ago,
        features.close >= features.low_52w * 1.30,
        features.close >= features.high_52w * 0.75,
    )
    return round(sum(checks) / len(checks) * 20, 4)


def _vpa_score(features: TechnicalFeatures) -> float:
    score = 0.0
    if features.pocket_pivot:
        score += 5.0
    if features.demand_bar:
        score += 4.0
    if features.up_down_volume_ratio20 is not None:
        if features.up_down_volume_ratio20 >= 1.5:
            score += 3.0
        elif features.up_down_volume_ratio20 >= 1.2:
            score += 2.0
        elif features.up_down_volume_ratio20 >= 1.0:
            score += 1.0
    if features.volume_dry_up and abs(features.distance_to_pivot_pct) <= 5:
        score += 3.0
    return round(_clamp(score, 0, 15), 4)


def _sepa_canslim_score(technical: TechnicalFeatures, fundamental: FundamentalFeatures) -> float:
    score = 0.0
    if technical.trend_template_pass:
        score += 4.0
    if technical.stage == "STAGE_2":
        score += 2.0
    if technical.vcp_proxy:
        score += 2.0
    if technical.confirmed_breakout or technical.early_breakout or technical.pocket_pivot or abs(technical.distance_to_pivot_pct) <= 3:
        score += 2.0

    if fundamental.quarterly_net_income_growth_yoy_pct >= 25:
        score += 4.0
    elif fundamental.quarterly_net_income_growth_yoy_pct >= 15:
        score += 2.0
    if fundamental.quarterly_revenue_growth_yoy_pct >= 15:
        score += 2.0
    elif fundamental.quarterly_revenue_growth_yoy_pct >= 8:
        score += 1.0
    if fundamental.annual_net_income_growth_pct >= 15:
        score += 2.0
    elif fundamental.annual_net_income_growth_pct >= 8:
        score += 1.0
    if fundamental.roe_pct >= 15:
        score += 2.0
    elif fundamental.roe_pct >= 10:
        score += 1.0
    return round(_clamp(score, 0, 20), 4)


def _rs_component(excess_return_pct: float) -> float:
    # Full 5 points at +10% excess return; zero at -5% or worse.
    return _clamp((excess_return_pct + 5.0) / 15.0 * 5.0, 0.0, 5.0)


def _relative_strength_score(features: TechnicalFeatures) -> float:
    if features.relative_strength_50_pct is None or features.relative_strength_200_pct is None:
        return 0.0
    return round(
        _rs_component(features.relative_strength_50_pct)
        + _rs_component(features.relative_strength_200_pct),
        4,
    )


def _fundamental_score(features: FundamentalFeatures, research: StockRadarResearchAssessment) -> float:
    # Meaning/Moat/Management are StockRadar research inputs, each max 3 points.
    score = (
        research.meaning_score * 0.6
        + research.moat_score * 0.6
        + research.management_score * 0.6
    )
    if features.roe_pct >= 15:
        score += 2.0
    elif features.roe_pct >= 10:
        score += 1.0
    if features.cfo_to_net_income is not None:
        if features.cfo_to_net_income >= 1.0:
            score += 2.0
        elif features.cfo_to_net_income >= 0.7:
            score += 1.0
    if features.debt_to_equity <= 1.0:
        score += 2.0
    elif features.debt_to_equity <= 2.0:
        score += 1.0
    return round(_clamp(score, 0, 15), 4)


def _valuation_score(fundamental: FundamentalFeatures, valuation: ValuationFeatures) -> float:
    score = 0.0
    if valuation.margin_of_safety_pct >= 20:
        score += 4.0
    elif valuation.margin_of_safety_pct >= 10:
        score += 3.0
    elif valuation.margin_of_safety_pct >= 0:
        score += 2.0

    if valuation.payback_years is not None:
        if valuation.payback_years <= 8:
            score += 2.0
        elif valuation.payback_years <= 10:
            score += 1.0

    if fundamental.peg is not None and 0 < fundamental.peg <= 1.5:
        score += 1.0
    if fundamental.pe is not None and 0 < fundamental.pe <= 30:
        score += 1.0
    if fundamental.ev_to_ebitda is not None and 0 < fundamental.ev_to_ebitda <= 15:
        score += 1.0
    if fundamental.fcf_yield_pct > 0:
        score += 1.0
    return round(_clamp(score, 0, 10), 4)


def _risk_liquidity_score(features: TechnicalFeatures, research: StockRadarResearchAssessment) -> float:
    score = 0.0
    if features.avg_volume20 >= 500_000:
        score += 2.0
    if features.atr20_pct <= 4.0:
        score += 1.0
    if features.extension_pct <= 5.0:
        score += 1.0
    if research.event_risk_pass:
        score += 1.0
    return round(_clamp(score, 0, 5), 4)


def score_buckets(
    technical: TechnicalFeatures,
    fundamental: FundamentalFeatures,
    valuation: ValuationFeatures,
    research: StockRadarResearchAssessment,
) -> dict[str, float]:
    return {
        "trend": _trend_score(technical),
        "vpa": _vpa_score(technical),
        "sepa_canslim": _sepa_canslim_score(technical, fundamental),
        "relative_strength": _relative_strength_score(technical),
        "fundamental": _fundamental_score(fundamental, research),
        "valuation": _valuation_score(fundamental, valuation),
        "catalyst": round(float(research.catalyst_score), 4),
        "risk_liquidity": _risk_liquidity_score(technical, research),
    }


def _setup_name(features: TechnicalFeatures) -> str:
    if features.confirmed_breakout:
        return "CONFIRMED_BREAKOUT"
    if features.pocket_pivot:
        return "POCKET_PIVOT"
    if features.early_breakout:
        return "EARLY_BREAKOUT"
    if features.vcp_proxy and 0 <= features.distance_to_pivot_pct <= 3:
        return "VCP_NEAR_PIVOT"
    if features.trend_template_pass:
        return "TREND_TEMPLATE"
    return "WATCH"


def compute_stock(
    *,
    ticker: str,
    sector: str,
    bars: Sequence[RawBar],
    benchmark_bars: Sequence[RawBar],
    financial_periods: Iterable[RawFinancialPeriod],
    research: StockRadarResearchAssessment,
    valuation_assumptions: InternalValuationAssumptions,
    previous_state: SetupState | None = None,
) -> InternalStockComputation:
    normalized_ticker = ticker.strip().upper()
    if len(normalized_ticker) != 3 or not normalized_ticker.isalpha() or not normalized_ticker.isascii():
        raise ValueError("ticker must be a 3-letter ASCII symbol")
    if not sector.strip():
        raise ValueError("sector is required")

    periods = tuple(financial_periods)
    technical = compute_technical_features(bars, benchmark_bars=benchmark_bars)
    fundamental = compute_fundamental_features(periods, current_price=technical.close)
    valuation = compute_valuation_features(periods, current_price=technical.close, assumptions=valuation_assumptions)
    market_regime = compute_market_regime(benchmark_bars)
    buckets = score_buckets(technical, fundamental, valuation, research)
    score = calculate_score(buckets)
    if score.score is None or score.coverage_pct != 100:
        raise ValueError("StockRadar internal score must have 100% coverage before ranking")

    state = derive_state(SetupFacts(
        extension_pct=technical.extension_pct,
        trigger_confirmed=technical.confirmed_breakout,
        trigger_ready=technical.pocket_pivot or technical.early_breakout,
        distance_to_trigger_pct=max(0.0, technical.distance_to_pivot_pct),
    ))
    setup = _setup_name(technical)
    evidence = (
        f"engine={INTERNAL_ENGINE_VERSION}",
        "calculation_origin=STOCKRADAR_ENGINE",
        f"stage={technical.stage}",
        f"trend_template={str(technical.trend_template_pass).lower()}",
        f"volume_ratio20={technical.volume_ratio20}",
        f"mos_pct={valuation.margin_of_safety_pct}",
        f"roe_pct={fundamental.roe_pct}",
    )
    candidate = Candidate(
        ticker=normalized_ticker,
        score=float(score.score),
        score_coverage_pct=score.coverage_pct,
        setup=setup,
        state=state,
        previous_state=previous_state,
        market_regime=market_regime,
        current_price=technical.close,
        pivot=technical.pivot20,
        distance_to_pivot_pct=technical.distance_to_pivot_pct,
        extension_pct=technical.extension_pct,
        liquidity_pass=technical.avg_volume20 >= 500_000,
        event_risk_pass=research.event_risk_pass,
        reason=f"StockRadar internal score {score.score:.2f}/100 · {setup}",
        evidence=evidence,
        is_mock=False,
    )
    return InternalStockComputation(
        ticker=normalized_ticker,
        sector=sector.strip(),
        candidate=candidate,
        technical=technical,
        fundamental=fundamental,
        valuation=valuation,
        bucket_scores=buckets,
        computation={**computation_provenance(), "engine_version": INTERNAL_ENGINE_VERSION},
    )


def build_top_hose_from_internal(
    snapshot: UniverseSnapshot,
    computations: Iterable[InternalStockComputation],
    *,
    strongest_limit: int = 30,
    per_sector_limit: int = 3,
) -> dict[str, object]:
    rows = list(computations)
    for row in rows:
        if row.computation.get("calculation_origin") != "STOCKRADAR_ENGINE":
            raise ValueError("Top HOSE accepts StockRadar internal computations only")
        if row.computation.get("external_scores_accepted") is not False:
            raise ValueError("Top HOSE cannot accept external scores")
    return build_top_hose(
        snapshot,
        [row.candidate for row in rows],
        {row.ticker: row.sector for row in rows},
        strongest_limit=strongest_limit,
        per_sector_limit=per_sector_limit,
    )
