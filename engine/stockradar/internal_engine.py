from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

from .auto_assessment import (
    BusinessModel,
    assessment_provenance,
    classify_business_model,
    compute_financial_fundamental_features,
    compute_financial_valuation_features,
    derive_research_assessment,
    derive_valuation_assumptions,
)
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
from .ticker_symbol import is_valid_hose_ticker


INTERNAL_ENGINE_VERSION = "STOCKRADAR_INTERNAL_V2.1"


@dataclass(frozen=True)
class InternalStockComputation:
    ticker: str
    sector: str
    business_model: str
    candidate: Candidate
    technical: TechnicalFeatures
    fundamental: FundamentalFeatures
    valuation: ValuationFeatures
    research: StockRadarResearchAssessment
    valuation_assumptions: InternalValuationAssumptions
    bucket_scores: Mapping[str, float]
    computation: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "sector": self.sector,
            "business_model": self.business_model,
            "candidate": self.candidate.to_dict(),
            "technical": self.technical.to_dict(),
            "fundamental": self.fundamental.to_dict(),
            "valuation": self.valuation.to_dict(),
            "research": asdict(self.research),
            "valuation_assumptions": asdict(self.valuation_assumptions),
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
    return _clamp((excess_return_pct + 5.0) / 15.0 * 5.0, 0.0, 5.0)


def _relative_strength_score(features: TechnicalFeatures) -> float:
    if features.relative_strength_50_pct is None or features.relative_strength_200_pct is None:
        return 0.0
    return round(
        _rs_component(features.relative_strength_50_pct)
        + _rs_component(features.relative_strength_200_pct),
        4,
    )


def _research_points(research: StockRadarResearchAssessment) -> float:
    return (
        research.meaning_score * 0.6
        + research.moat_score * 0.6
        + research.management_score * 0.6
    )


def _fundamental_score(
    features: FundamentalFeatures,
    research: StockRadarResearchAssessment,
    business_model: BusinessModel,
) -> float:
    score = _research_points(research)
    if features.roe_pct >= 15:
        score += 2.0
    elif features.roe_pct >= 10:
        score += 1.0

    if business_model.is_financial:
        if features.annual_net_income_growth_pct >= 10:
            score += 1.5
        elif features.annual_net_income_growth_pct >= 0:
            score += 0.75
        if features.quarterly_net_income_growth_yoy_pct >= 10:
            score += 1.5
        elif features.quarterly_net_income_growth_yoy_pct >= 0:
            score += 0.75
        if features.net_margin_pct > 0:
            score += 1.0
    else:
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


def _valuation_score(
    fundamental: FundamentalFeatures,
    valuation: ValuationFeatures,
    business_model: BusinessModel,
) -> float:
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

    if business_model.is_financial:
        if 0 < fundamental.pb <= 1.5:
            score += 2.0
        elif 0 < fundamental.pb <= 2.5:
            score += 1.0
    else:
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
    business_model: BusinessModel | str = BusinessModel.CORPORATE,
) -> dict[str, float]:
    model = business_model if isinstance(business_model, BusinessModel) else BusinessModel(str(business_model))
    return {
        "trend": _trend_score(technical),
        "vpa": _vpa_score(technical),
        "sepa_canslim": _sepa_canslim_score(technical, fundamental),
        "relative_strength": _relative_strength_score(technical),
        "fundamental": _fundamental_score(fundamental, research, model),
        "valuation": _valuation_score(fundamental, valuation, model),
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
    research: StockRadarResearchAssessment | None = None,
    valuation_assumptions: InternalValuationAssumptions | None = None,
    business_model: BusinessModel | str | None = None,
    company_name: str = "",
    event_risk_pass: bool = True,
    previous_state: SetupState | None = None,
) -> InternalStockComputation:
    normalized_ticker = ticker.strip().upper()
    if not is_valid_hose_ticker(normalized_ticker):
        raise ValueError("ticker must be a 3-character HOSE symbol")
    if not sector.strip():
        raise ValueError("sector is required")

    model = (
        business_model
        if isinstance(business_model, BusinessModel)
        else BusinessModel(str(business_model)) if business_model is not None
        else classify_business_model(sector, company_name)
    )
    periods = tuple(financial_periods)
    technical = compute_technical_features(bars, benchmark_bars=benchmark_bars)
    if model.is_financial:
        fundamental = compute_financial_fundamental_features(periods, current_price=technical.close)
    else:
        fundamental = compute_fundamental_features(periods, current_price=technical.close)

    resolved_research = research or derive_research_assessment(
        periods,
        business_model=model,
        technical=technical,
        event_risk_pass=event_risk_pass,
    )
    resolved_assumptions = valuation_assumptions or derive_valuation_assumptions(periods, business_model=model)
    if model.is_financial:
        valuation = compute_financial_valuation_features(
            periods,
            current_price=technical.close,
            assumptions=resolved_assumptions,
        )
    else:
        valuation = compute_valuation_features(
            periods,
            current_price=technical.close,
            assumptions=resolved_assumptions,
        )

    market_regime = compute_market_regime(benchmark_bars)
    buckets = score_buckets(technical, fundamental, valuation, resolved_research, model)
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
        f"business_model={model.value}",
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
        event_risk_pass=resolved_research.event_risk_pass,
        reason=f"StockRadar internal score {score.score:.2f}/100 · {setup}",
        evidence=evidence,
        is_mock=False,
    )
    provenance = {
        **computation_provenance(),
        **assessment_provenance(model),
        "engine_version": INTERNAL_ENGINE_VERSION,
    }
    return InternalStockComputation(
        ticker=normalized_ticker,
        sector=sector.strip(),
        business_model=model.value,
        candidate=candidate,
        technical=technical,
        fundamental=fundamental,
        valuation=valuation,
        research=resolved_research,
        valuation_assumptions=resolved_assumptions,
        bucket_scores=buckets,
        computation=provenance,
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
        if row.computation.get("research_origin") != "STOCKRADAR_ENGINE":
            raise ValueError("Top HOSE research assessment must be StockRadar-computed")
        if row.computation.get("valuation_assumption_origin") != "STOCKRADAR_ENGINE":
            raise ValueError("Top HOSE valuation assumptions must be StockRadar-computed")
    return build_top_hose(
        snapshot,
        [row.candidate for row in rows],
        {row.ticker: row.sector for row in rows},
        strongest_limit=strongest_limit,
        per_sector_limit=per_sector_limit,
    )
