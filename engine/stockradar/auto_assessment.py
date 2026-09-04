from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from statistics import fmean, median, pstdev
from typing import Iterable, Sequence

from .internal_features import (
    FundamentalFeatures,
    InternalFeatureError,
    InternalValuationAssumptions,
    RawFinancialPeriod,
    StockRadarResearchAssessment,
    TechnicalFeatures,
    ValuationFeatures,
)


AUTO_ASSESSMENT_VERSION = "STOCKRADAR_AUTO_RESEARCH_V1"


class BusinessModel(str, Enum):
    CORPORATE = "CORPORATE"
    BANK = "BANK"
    SECURITIES = "SECURITIES"
    INSURANCE = "INSURANCE"
    FINANCIAL = "FINANCIAL"

    @property
    def is_financial(self) -> bool:
        return self is not BusinessModel.CORPORATE


def classify_business_model(sector: str, company_name: str = "") -> BusinessModel:
    text = f"{sector} {company_name}".strip().lower()
    if any(token in text for token in ("ngân hàng", "ngan hang", "bank")):
        return BusinessModel.BANK
    if any(token in text for token in ("chứng khoán", "chung khoan", "securities", "broker")):
        return BusinessModel.SECURITIES
    if any(token in text for token in ("bảo hiểm", "bao hiem", "insurance")):
        return BusinessModel.INSURANCE
    if any(token in text for token in ("tài chính", "tai chinh", "financial", "finance")):
        return BusinessModel.FINANCIAL
    return BusinessModel.CORPORATE


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _growth(current: float, previous: float) -> float | None:
    if previous == 0:
        return None
    return current / previous - 1.0


def _annual(periods: Iterable[RawFinancialPeriod]) -> list[RawFinancialPeriod]:
    return sorted(
        (row for row in periods if row.period_type.strip().upper() == "ANNUAL"),
        key=lambda row: row.period_end,
    )


def _quarters(periods: Iterable[RawFinancialPeriod]) -> list[RawFinancialPeriod]:
    return sorted(
        (row for row in periods if row.period_type.strip().upper() == "QUARTER"),
        key=lambda row: row.period_end,
    )


def _recent_growth(values: Sequence[float]) -> list[float]:
    growth: list[float] = []
    for previous, current in zip(values, values[1:]):
        rate = _growth(current, previous)
        if rate is not None:
            growth.append(_clamp(rate, -0.50, 0.60))
    return growth


def _score_roes(rows: Sequence[RawFinancialPeriod]) -> tuple[list[float], list[float]]:
    roes: list[float] = []
    margins: list[float] = []
    for index, row in enumerate(rows):
        previous_equity = rows[index - 1].equity if index > 0 else row.equity
        average_equity = (previous_equity + row.equity) / 2
        if average_equity > 0:
            roes.append(row.net_income / average_equity * 100)
        if row.revenue:
            margins.append(row.net_income / row.revenue * 100)
    return roes, margins


def derive_research_assessment(
    periods: Iterable[RawFinancialPeriod],
    *,
    business_model: BusinessModel | str = BusinessModel.CORPORATE,
    technical: TechnicalFeatures | None = None,
    event_risk_pass: bool = True,
) -> StockRadarResearchAssessment:
    """Derive the first-pass 4M/CANSLIM research inputs from StockRadar-owned rules.

    This is deliberately a quantitative ownership-quality screen, not a claim that
    qualitative moat/management work is complete. Deep reports may add issuer filing
    evidence later, but no provider score enters these values.
    """

    model = BusinessModel(str(business_model)) if not isinstance(business_model, BusinessModel) else business_model
    rows = tuple(periods)
    annual = _annual(rows)
    quarters = _quarters(rows)
    if len(annual) < 2:
        raise InternalFeatureError("auto research needs at least 2 annual periods")
    latest = annual[-1]
    recent_annual = annual[-5:]
    roes, margins = _score_roes(recent_annual)

    meaning = 0.0
    if latest.revenue > 0:
        meaning += 1.0
    if latest.net_income > 0:
        meaning += 1.5
    if latest.equity > 0 and latest.total_assets > 0:
        meaning += 1.0
    if len(annual) >= 4:
        meaning += 0.75
    revenue_growth = _recent_growth([row.revenue for row in recent_annual])
    if revenue_growth and median(revenue_growth) >= 0:
        meaning += 0.75

    moat = 0.0
    avg_roe = fmean(roes) if roes else 0.0
    if avg_roe >= 18:
        moat += 2.0
    elif avg_roe >= 12:
        moat += 1.5
    elif avg_roe >= 8:
        moat += 1.0
    if roes and len(roes) >= 3 and pstdev(roes) <= 6:
        moat += 1.0
    if margins and fmean(margins) > 0:
        moat += 0.75
    if margins and len(margins) >= 3 and pstdev(margins) <= max(4.0, abs(fmean(margins)) * 0.35):
        moat += 0.75
    income_growth = _recent_growth([row.net_income for row in recent_annual])
    if income_growth and sum(rate > 0 for rate in income_growth) >= max(1, len(income_growth) - 1):
        moat += 0.5

    management = 0.0
    if model.is_financial:
        if latest.net_income > 0:
            management += 1.25
        if len(annual) >= 2 and latest.equity >= annual[-2].equity:
            management += 1.0
        if avg_roe >= 12:
            management += 1.25
        elif avg_roe >= 8:
            management += 0.75
        dilution = latest.shares_outstanding / annual[-2].shares_outstanding - 1 if annual[-2].shares_outstanding > 0 else 1.0
        if dilution <= 0.05:
            management += 1.0
        elif dilution <= 0.10:
            management += 0.5
        if income_growth and median(income_growth) >= 0:
            management += 0.5
    else:
        cfo_ratio = latest.operating_cash_flow / latest.net_income if latest.net_income else 0.0
        if cfo_ratio >= 1.0:
            management += 1.5
        elif cfo_ratio >= 0.7:
            management += 1.0
        leverage = latest.total_debt / latest.equity if latest.equity else float("inf")
        if leverage <= 1.0:
            management += 1.25
        elif leverage <= 2.0:
            management += 0.75
        if len(annual) >= 2:
            prior_leverage = annual[-2].total_debt / annual[-2].equity if annual[-2].equity else float("inf")
            if leverage <= prior_leverage * 1.10:
                management += 0.75
            dilution = latest.shares_outstanding / annual[-2].shares_outstanding - 1 if annual[-2].shares_outstanding > 0 else 1.0
            if dilution <= 0.05:
                management += 0.75
        if latest.operating_cash_flow - abs(latest.capex) > 0:
            management += 0.75

    catalyst = 0.0
    if len(quarters) >= 5:
        latest_q, yoy_q = quarters[-1], quarters[-5]
        q_income = _growth(latest_q.net_income, yoy_q.net_income)
        q_revenue = _growth(latest_q.revenue, yoy_q.revenue)
        if q_income is not None:
            if q_income >= 0.25:
                catalyst += 2.0
            elif q_income >= 0.15:
                catalyst += 1.25
            elif q_income >= 0.05:
                catalyst += 0.5
        if q_revenue is not None:
            if q_revenue >= 0.15:
                catalyst += 1.25
            elif q_revenue >= 0.08:
                catalyst += 0.75
    if technical is not None:
        if technical.confirmed_breakout:
            catalyst += 1.5
        elif technical.pocket_pivot or technical.early_breakout:
            catalyst += 1.0
        elif technical.demand_bar:
            catalyst += 0.5
        if technical.relative_strength_50_pct is not None and technical.relative_strength_50_pct >= 5:
            catalyst += 0.5

    return StockRadarResearchAssessment(
        meaning_score=round(_clamp(meaning, 0, 5), 4),
        moat_score=round(_clamp(moat, 0, 5), 4),
        management_score=round(_clamp(management, 0, 5), 4),
        catalyst_score=round(_clamp(catalyst, 0, 5), 4),
        event_risk_pass=bool(event_risk_pass),
    )


def derive_valuation_assumptions(
    periods: Iterable[RawFinancialPeriod],
    *,
    business_model: BusinessModel | str = BusinessModel.CORPORATE,
) -> InternalValuationAssumptions:
    model = BusinessModel(str(business_model)) if not isinstance(business_model, BusinessModel) else business_model
    annual = _annual(tuple(periods))
    if len(annual) < 2:
        raise InternalFeatureError("auto valuation assumptions need at least 2 annual periods")
    recent = annual[-5:]
    income_growth = _recent_growth([row.net_income for row in recent])
    revenue_growth = _recent_growth([row.revenue for row in recent])
    blended = []
    if income_growth:
        blended.append(median(income_growth))
    if revenue_growth:
        blended.append(median(revenue_growth))
    observed = fmean(blended) if blended else 0.05

    if model.is_financial:
        base = _clamp(observed, 0.03, 0.15)
        discount = 0.13
        terminal = 0.04
        maintenance_capex = 0.0
    else:
        base = _clamp(observed, 0.02, 0.18)
        discount = 0.12
        terminal = 0.04
        recent_capex = [abs(row.capex) for row in recent[-3:] if row.capex is not None]
        maintenance_capex = median(recent_capex) if recent_capex else abs(annual[-1].capex)

    return InternalValuationAssumptions(
        maintenance_capex=round(float(maintenance_capex), 4),
        bear_growth_rate=round(_clamp(base - 0.08, -0.05, 0.08), 6),
        base_growth_rate=round(base, 6),
        bull_growth_rate=round(_clamp(base + 0.06, 0.06, 0.25), 6),
        discount_rate=discount,
        terminal_growth_rate=terminal,
        horizon_years=5,
    )


def compute_financial_fundamental_features(
    periods: Iterable[RawFinancialPeriod],
    *,
    current_price: float,
) -> FundamentalFeatures:
    rows = tuple(periods)
    annual = _annual(rows)
    quarters = _quarters(rows)
    if len(annual) < 2 or len(quarters) < 5:
        raise InternalFeatureError("financial model needs at least 2 annual and 5 quarterly periods")
    latest_a, previous_a = annual[-1], annual[-2]
    latest_q, yoy_q = quarters[-1], quarters[-5]

    q_revenue = (_growth(latest_q.revenue, yoy_q.revenue) or 0.0) * 100
    q_income = (_growth(latest_q.net_income, yoy_q.net_income) or 0.0) * 100
    annual_revenue = (_growth(latest_a.revenue, previous_a.revenue) or 0.0) * 100
    annual_income = (_growth(latest_a.net_income, previous_a.net_income) or 0.0) * 100
    average_equity = (latest_a.equity + previous_a.equity) / 2
    roe = latest_a.net_income / average_equity * 100 if average_equity > 0 else 0.0
    margin = latest_a.net_income / latest_a.revenue * 100 if latest_a.revenue else 0.0
    leverage = latest_a.total_debt / latest_a.equity if latest_a.equity else 0.0
    eps = latest_a.net_income / latest_a.shares_outstanding
    market_cap = current_price * latest_a.shares_outstanding
    pe = current_price / eps if eps > 0 else None
    pb = market_cap / latest_a.equity if latest_a.equity > 0 else 0.0
    peg = pe / annual_income if pe is not None and annual_income > 0 else None
    earnings_yield = latest_a.net_income / market_cap * 100 if market_cap > 0 else 0.0

    return FundamentalFeatures(
        quarterly_revenue_growth_yoy_pct=round(q_revenue, 4),
        quarterly_net_income_growth_yoy_pct=round(q_income, 4),
        annual_revenue_growth_pct=round(annual_revenue, 4),
        annual_net_income_growth_pct=round(annual_income, 4),
        roe_pct=round(roe, 4),
        net_margin_pct=round(margin, 4),
        debt_to_equity=round(leverage, 4),
        cfo_to_net_income=None,
        free_cash_flow=0.0,
        eps=round(eps, 6),
        pe=round(pe, 4) if pe is not None else None,
        pb=round(pb, 4),
        peg=round(peg, 4) if peg is not None else None,
        ev_to_ebitda=None,
        fcf_yield_pct=round(earnings_yield, 4),
    )


def _justified_pb(roe: float, growth: float, cost_of_equity: float) -> float:
    if cost_of_equity <= growth:
        return 0.0
    raw = (roe - growth) / (cost_of_equity - growth)
    return _clamp(raw, 0.35, 4.0)


def _payback(price: float, eps: float, growth: float, max_years: int = 30) -> float | None:
    if price <= 0 or eps <= 0:
        return None
    cumulative = 0.0
    annual = eps
    for year in range(1, max_years + 1):
        annual *= 1 + growth
        previous = cumulative
        cumulative += annual
        if cumulative >= price:
            fraction = (price - previous) / annual
            return (year - 1) + _clamp(fraction, 0.0, 1.0)
    return None


def compute_financial_valuation_features(
    periods: Iterable[RawFinancialPeriod],
    *,
    current_price: float,
    assumptions: InternalValuationAssumptions,
) -> ValuationFeatures:
    annual = _annual(tuple(periods))
    if len(annual) < 2:
        raise InternalFeatureError("financial valuation needs at least 2 annual periods")
    latest, previous = annual[-1], annual[-2]
    average_equity = (latest.equity + previous.equity) / 2
    roe = latest.net_income / average_equity if average_equity > 0 else 0.0
    bvps = latest.equity / latest.shares_outstanding
    eps = latest.net_income / latest.shares_outstanding

    bear_roe = max(0.03, roe * 0.75)
    base_roe = max(0.04, roe)
    bull_roe = min(0.35, max(base_roe, roe * 1.10))
    bear_g = _clamp(assumptions.bear_growth_rate, 0.0, 0.05)
    base_g = _clamp(assumptions.base_growth_rate, 0.01, 0.08)
    bull_g = _clamp(assumptions.bull_growth_rate, 0.02, 0.10)

    bear = bvps * _justified_pb(bear_roe, bear_g, assumptions.discount_rate + 0.02)
    base = bvps * _justified_pb(base_roe, base_g, assumptions.discount_rate)
    bull = bvps * _justified_pb(bull_roe, bull_g, max(bull_g + 0.02, assumptions.discount_rate - 0.01))
    fair_values = sorted((bear, base, bull))
    bear, base, bull = fair_values[0], fair_values[1], fair_values[2]
    mos = (base - current_price) / base * 100 if base > 0 else -100.0
    upside = (base / current_price - 1) * 100
    downside = (bear / current_price - 1) * 100
    payback = _payback(current_price, eps, assumptions.base_growth_rate)
    return ValuationFeatures(
        normalized_owner_earnings=round(latest.net_income, 4),
        bear_fair_value=round(bear, 4),
        base_fair_value=round(base, 4),
        bull_fair_value=round(bull, 4),
        margin_of_safety_pct=round(mos, 4),
        upside_to_base_pct=round(upside, 4),
        downside_to_bear_pct=round(downside, 4),
        payback_years=round(payback, 4) if payback is not None else None,
    )


def assessment_provenance(model: BusinessModel) -> dict[str, object]:
    return {
        "auto_assessment_version": AUTO_ASSESSMENT_VERSION,
        "business_model": model.value,
        "research_origin": "STOCKRADAR_ENGINE",
        "valuation_assumption_origin": "STOCKRADAR_ENGINE",
        "external_research_scores_accepted": False,
    }
