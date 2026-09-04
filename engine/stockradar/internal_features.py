from __future__ import annotations

from dataclasses import asdict, dataclass
from statistics import fmean, pstdev
from typing import Iterable, Sequence

from .models import MarketRegime


class InternalFeatureError(ValueError):
    pass


@dataclass(frozen=True)
class RawBar:
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if not self.timestamp:
            raise InternalFeatureError("bar timestamp is required")
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise InternalFeatureError("OHLC values must be positive")
        if self.high < max(self.open, self.close, self.low):
            raise InternalFeatureError("high is inconsistent with OHLC")
        if self.low > min(self.open, self.close, self.high):
            raise InternalFeatureError("low is inconsistent with OHLC")
        if self.volume < 0:
            raise InternalFeatureError("volume cannot be negative")


@dataclass(frozen=True)
class RawFinancialPeriod:
    period_end: str
    period_type: str
    revenue: float
    net_income: float
    total_assets: float
    equity: float
    total_debt: float
    cash: float
    operating_cash_flow: float
    capex: float
    shares_outstanding: float
    operating_profit: float | None = None
    depreciation_amortization: float | None = None

    def __post_init__(self) -> None:
        kind = self.period_type.strip().upper()
        if kind not in {"QUARTER", "ANNUAL"}:
            raise InternalFeatureError("period_type must be QUARTER or ANNUAL")
        if not self.period_end:
            raise InternalFeatureError("period_end is required")
        if self.total_assets <= 0 or self.equity <= 0 or self.shares_outstanding <= 0:
            raise InternalFeatureError("assets, equity and shares_outstanding must be positive")
        if self.total_debt < 0 or self.cash < 0:
            raise InternalFeatureError("debt and cash cannot be negative")


@dataclass(frozen=True)
class StockRadarResearchAssessment:
    meaning_score: float
    moat_score: float
    management_score: float
    catalyst_score: float
    event_risk_pass: bool = True

    def __post_init__(self) -> None:
        for name in ("meaning_score", "moat_score", "management_score", "catalyst_score"):
            value = float(getattr(self, name))
            if value < 0 or value > 5:
                raise InternalFeatureError(f"{name} must be between 0 and 5")


@dataclass(frozen=True)
class InternalValuationAssumptions:
    maintenance_capex: float
    bear_growth_rate: float
    base_growth_rate: float
    bull_growth_rate: float
    discount_rate: float
    terminal_growth_rate: float
    horizon_years: int = 5

    def __post_init__(self) -> None:
        if self.maintenance_capex < 0:
            raise InternalFeatureError("maintenance_capex cannot be negative")
        if self.horizon_years <= 0 or self.horizon_years > 15:
            raise InternalFeatureError("horizon_years must be between 1 and 15")
        if self.discount_rate <= self.terminal_growth_rate:
            raise InternalFeatureError("discount_rate must exceed terminal_growth_rate")
        for name in ("bear_growth_rate", "base_growth_rate", "bull_growth_rate"):
            value = float(getattr(self, name))
            if value <= -1 or value > 1:
                raise InternalFeatureError(f"{name} is outside supported range")


@dataclass(frozen=True)
class TechnicalFeatures:
    close: float
    ma10: float
    ma50: float
    ma150: float
    ma200: float
    ma200_20d_ago: float
    high_52w: float
    low_52w: float
    avg_volume20: float
    max_down_volume10: float
    up_down_volume_ratio20: float | None
    last_change_pct: float
    volume_ratio20: float
    pivot20: float
    distance_to_pivot_pct: float
    extension_pct: float
    bollinger_middle: float
    bollinger_upper: float
    bollinger_lower: float
    bollinger_width_pct: float
    tenkan: float
    kijun: float
    span_a: float
    span_b: float
    chikou_vs_26d_pct: float
    atr20_pct: float
    trend_template_pass: bool
    stage: str
    vcp_proxy: bool
    volume_dry_up: bool
    demand_bar: bool
    pocket_pivot: bool
    early_breakout: bool
    confirmed_breakout: bool
    relative_strength_50_pct: float | None
    relative_strength_200_pct: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class FundamentalFeatures:
    quarterly_revenue_growth_yoy_pct: float
    quarterly_net_income_growth_yoy_pct: float
    annual_revenue_growth_pct: float
    annual_net_income_growth_pct: float
    roe_pct: float
    net_margin_pct: float
    debt_to_equity: float
    cfo_to_net_income: float | None
    free_cash_flow: float
    eps: float
    pe: float | None
    pb: float
    peg: float | None
    ev_to_ebitda: float | None
    fcf_yield_pct: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ValuationFeatures:
    normalized_owner_earnings: float
    bear_fair_value: float
    base_fair_value: float
    bull_fair_value: float
    margin_of_safety_pct: float
    upside_to_base_pct: float
    downside_to_bear_pct: float
    payback_years: float | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _mean(values: Sequence[float], window: int) -> float:
    if len(values) < window:
        raise InternalFeatureError(f"need at least {window} observations")
    return float(fmean(values[-window:]))


def _window_mid(highs: Sequence[float], lows: Sequence[float], window: int) -> float:
    if len(highs) < window or len(lows) < window:
        raise InternalFeatureError(f"need at least {window} observations")
    return (max(highs[-window:]) + min(lows[-window:])) / 2


def _pct_change(current: float, previous: float) -> float:
    if previous == 0:
        raise InternalFeatureError("cannot calculate percentage change from zero")
    return (current / previous - 1) * 100


def _validate_bars(bars: Sequence[RawBar], minimum: int) -> None:
    if len(bars) < minimum:
        raise InternalFeatureError(f"need at least {minimum} OHLCV bars")
    timestamps = [bar.timestamp for bar in bars]
    if len(set(timestamps)) != len(timestamps):
        raise InternalFeatureError("duplicate OHLCV timestamp")
    if timestamps != sorted(timestamps):
        raise InternalFeatureError("OHLCV bars must be chronological")


def _return_pct(values: Sequence[float], lookback: int) -> float:
    if len(values) <= lookback:
        raise InternalFeatureError(f"need more than {lookback} closes")
    return _pct_change(values[-1], values[-1 - lookback])


def compute_market_regime(benchmark_bars: Sequence[RawBar]) -> MarketRegime:
    _validate_bars(benchmark_bars, 220)
    closes = [bar.close for bar in benchmark_bars]
    ma50 = _mean(closes, 50)
    ma200 = _mean(closes, 200)
    ma200_20d_ago = float(fmean(closes[-220:-20]))
    close = closes[-1]
    if close > ma50 > ma200 and ma200 > ma200_20d_ago:
        return MarketRegime.GREEN
    if close > ma200:
        return MarketRegime.YELLOW
    return MarketRegime.RED


def same_time_rvol(current_cumulative_volume: float, historical_same_time_volumes: Sequence[float]) -> float:
    if current_cumulative_volume < 0:
        raise InternalFeatureError("current cumulative volume cannot be negative")
    history = [float(value) for value in historical_same_time_volumes if float(value) >= 0]
    if len(history) < 5:
        raise InternalFeatureError("same-time RVOL needs at least 5 historical observations")
    baseline = fmean(history)
    if baseline <= 0:
        raise InternalFeatureError("same-time RVOL baseline must be positive")
    return round(current_cumulative_volume / baseline, 4)


def compute_technical_features(
    bars: Sequence[RawBar],
    *,
    benchmark_bars: Sequence[RawBar] | None = None,
) -> TechnicalFeatures:
    _validate_bars(bars, 252)
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    volumes = [bar.volume for bar in bars]

    close = closes[-1]
    ma10 = _mean(closes, 10)
    ma50 = _mean(closes, 50)
    ma150 = _mean(closes, 150)
    ma200 = _mean(closes, 200)
    ma200_20d_ago = float(fmean(closes[-220:-20]))
    high_52w = max(highs[-252:])
    low_52w = min(lows[-252:])
    avg_volume20 = _mean(volumes[:-1], 20)
    volume_ratio20 = volumes[-1] / avg_volume20 if avg_volume20 > 0 else 0.0

    down_volumes: list[float] = []
    for index in range(max(1, len(bars) - 10), len(bars)):
        if closes[index] < closes[index - 1]:
            down_volumes.append(volumes[index])
    max_down_volume10 = max(down_volumes, default=0.0)

    up_volume = 0.0
    down_volume = 0.0
    start = max(1, len(bars) - 20)
    for index in range(start, len(bars)):
        if closes[index] > closes[index - 1]:
            up_volume += volumes[index]
        elif closes[index] < closes[index - 1]:
            down_volume += volumes[index]
    up_down_volume_ratio20 = up_volume / down_volume if down_volume > 0 else None

    last_change_pct = _pct_change(closes[-1], closes[-2])
    pivot20 = max(highs[-21:-1])
    distance_to_pivot_pct = (pivot20 - close) / pivot20 * 100
    extension_pct = max(0.0, (close - pivot20) / pivot20 * 100)

    bollinger_middle = _mean(closes, 20)
    bollinger_std = pstdev(closes[-20:])
    bollinger_upper = bollinger_middle + 2 * bollinger_std
    bollinger_lower = bollinger_middle - 2 * bollinger_std
    bollinger_width_pct = (bollinger_upper - bollinger_lower) / bollinger_middle * 100

    tenkan = _window_mid(highs, lows, 9)
    kijun = _window_mid(highs, lows, 26)
    span_a = (tenkan + kijun) / 2
    span_b = _window_mid(highs, lows, 52)
    chikou_vs_26d_pct = _pct_change(close, closes[-27])

    true_ranges: list[float] = []
    for index in range(len(bars) - 20, len(bars)):
        previous_close = closes[index - 1]
        true_ranges.append(max(highs[index] - lows[index], abs(highs[index] - previous_close), abs(lows[index] - previous_close)))
    atr20_pct = fmean(true_ranges) / close * 100

    trend_template_pass = (
        close > ma50 > ma150 > ma200
        and ma200 > ma200_20d_ago
        and close >= low_52w * 1.30
        and close >= high_52w * 0.75
    )
    if trend_template_pass:
        stage = "STAGE_2"
    elif close < ma200 and ma50 < ma150:
        stage = "STAGE_4"
    elif close >= ma200 and (ma50 < ma150 or ma150 <= ma200):
        stage = "STAGE_3"
    else:
        stage = "STAGE_1"

    ranges = [(bar.high - bar.low) / bar.close for bar in bars]
    recent_range = fmean(ranges[-5:])
    prior_range = fmean(ranges[-20:-5])
    recent_volume = fmean(volumes[-5:])
    prior_volume = fmean(volumes[-20:-5])
    vcp_proxy = recent_range <= prior_range * 0.75 and recent_volume <= prior_volume * 0.80
    volume_dry_up = volumes[-1] <= avg_volume20 * 0.60
    demand_bar = last_change_pct >= 2.0 and volume_ratio20 >= 1.20
    pocket_pivot = (
        last_change_pct >= 2.0
        and volumes[-1] > max_down_volume10
        and close >= ma10
        and (close / ma10 - 1) * 100 <= 5.0
    )
    confirmed_breakout = close > pivot20 and volume_ratio20 >= 1.40
    early_breakout = close > pivot20 and volumes[-1] > max_down_volume10 and not confirmed_breakout

    rs50 = None
    rs200 = None
    if benchmark_bars is not None:
        _validate_bars(benchmark_bars, 252)
        benchmark_closes = [bar.close for bar in benchmark_bars]
        rs50 = _return_pct(closes, 50) - _return_pct(benchmark_closes, 50)
        rs200 = _return_pct(closes, 200) - _return_pct(benchmark_closes, 200)

    return TechnicalFeatures(
        close=round(close, 6), ma10=round(ma10, 6), ma50=round(ma50, 6), ma150=round(ma150, 6),
        ma200=round(ma200, 6), ma200_20d_ago=round(ma200_20d_ago, 6), high_52w=round(high_52w, 6),
        low_52w=round(low_52w, 6), avg_volume20=round(avg_volume20, 2), max_down_volume10=round(max_down_volume10, 2),
        up_down_volume_ratio20=round(up_down_volume_ratio20, 4) if up_down_volume_ratio20 is not None else None,
        last_change_pct=round(last_change_pct, 4), volume_ratio20=round(volume_ratio20, 4), pivot20=round(pivot20, 6),
        distance_to_pivot_pct=round(distance_to_pivot_pct, 4), extension_pct=round(extension_pct, 4),
        bollinger_middle=round(bollinger_middle, 6), bollinger_upper=round(bollinger_upper, 6),
        bollinger_lower=round(bollinger_lower, 6), bollinger_width_pct=round(bollinger_width_pct, 4),
        tenkan=round(tenkan, 6), kijun=round(kijun, 6), span_a=round(span_a, 6), span_b=round(span_b, 6),
        chikou_vs_26d_pct=round(chikou_vs_26d_pct, 4), atr20_pct=round(atr20_pct, 4),
        trend_template_pass=trend_template_pass, stage=stage, vcp_proxy=vcp_proxy, volume_dry_up=volume_dry_up,
        demand_bar=demand_bar, pocket_pivot=pocket_pivot, early_breakout=early_breakout,
        confirmed_breakout=confirmed_breakout,
        relative_strength_50_pct=round(rs50, 4) if rs50 is not None else None,
        relative_strength_200_pct=round(rs200, 4) if rs200 is not None else None,
    )


def _growth_pct(current: float, previous: float) -> float:
    if previous == 0:
        raise InternalFeatureError("growth comparison base cannot be zero")
    return (current / previous - 1) * 100


def compute_fundamental_features(
    periods: Iterable[RawFinancialPeriod],
    *,
    current_price: float,
) -> FundamentalFeatures:
    if current_price <= 0:
        raise InternalFeatureError("current_price must be positive")
    rows = sorted(periods, key=lambda item: item.period_end)
    annual = [row for row in rows if row.period_type.strip().upper() == "ANNUAL"]
    quarters = [row for row in rows if row.period_type.strip().upper() == "QUARTER"]
    if len(annual) < 2:
        raise InternalFeatureError("need at least 2 annual financial periods")
    if len(quarters) < 5:
        raise InternalFeatureError("need at least 5 quarterly financial periods")

    latest_a, previous_a = annual[-1], annual[-2]
    latest_q, yoy_q = quarters[-1], quarters[-5]
    q_revenue_growth = _growth_pct(latest_q.revenue, yoy_q.revenue)
    q_income_growth = _growth_pct(latest_q.net_income, yoy_q.net_income)
    annual_revenue_growth = _growth_pct(latest_a.revenue, previous_a.revenue)
    annual_income_growth = _growth_pct(latest_a.net_income, previous_a.net_income)

    average_equity = (latest_a.equity + previous_a.equity) / 2
    roe_pct = latest_a.net_income / average_equity * 100
    net_margin_pct = latest_a.net_income / latest_a.revenue * 100 if latest_a.revenue else 0.0
    debt_to_equity = latest_a.total_debt / latest_a.equity
    cfo_to_net_income = latest_a.operating_cash_flow / latest_a.net_income if latest_a.net_income else None
    free_cash_flow = latest_a.operating_cash_flow - abs(latest_a.capex)
    eps = latest_a.net_income / latest_a.shares_outstanding
    pe = current_price / eps if eps > 0 else None
    market_cap = current_price * latest_a.shares_outstanding
    pb = market_cap / latest_a.equity
    ebitda = None
    if latest_a.operating_profit is not None and latest_a.depreciation_amortization is not None:
        ebitda = latest_a.operating_profit + latest_a.depreciation_amortization
    enterprise_value = market_cap + latest_a.total_debt - latest_a.cash
    ev_to_ebitda = enterprise_value / ebitda if ebitda and ebitda > 0 else None
    peg = pe / annual_income_growth if pe is not None and annual_income_growth > 0 else None
    fcf_yield_pct = free_cash_flow / market_cap * 100 if market_cap > 0 else 0.0

    return FundamentalFeatures(
        quarterly_revenue_growth_yoy_pct=round(q_revenue_growth, 4),
        quarterly_net_income_growth_yoy_pct=round(q_income_growth, 4),
        annual_revenue_growth_pct=round(annual_revenue_growth, 4),
        annual_net_income_growth_pct=round(annual_income_growth, 4),
        roe_pct=round(roe_pct, 4), net_margin_pct=round(net_margin_pct, 4),
        debt_to_equity=round(debt_to_equity, 4),
        cfo_to_net_income=round(cfo_to_net_income, 4) if cfo_to_net_income is not None else None,
        free_cash_flow=round(free_cash_flow, 4), eps=round(eps, 6), pe=round(pe, 4) if pe is not None else None,
        pb=round(pb, 4), peg=round(peg, 4) if peg is not None else None,
        ev_to_ebitda=round(ev_to_ebitda, 4) if ev_to_ebitda is not None else None,
        fcf_yield_pct=round(fcf_yield_pct, 4),
    )


def _dcf_per_share(
    owner_earnings: float,
    shares: float,
    *,
    growth_rate: float,
    discount_rate: float,
    terminal_growth_rate: float,
    years: int,
) -> float:
    if shares <= 0 or owner_earnings <= 0:
        return 0.0
    cash_flow = owner_earnings
    present_value = 0.0
    for year in range(1, years + 1):
        cash_flow *= 1 + growth_rate
        present_value += cash_flow / ((1 + discount_rate) ** year)
    terminal = cash_flow * (1 + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
    present_value += terminal / ((1 + discount_rate) ** years)
    return present_value / shares


def _payback_years(price: float, owner_earnings_per_share: float, growth_rate: float, max_years: int = 30) -> float | None:
    if price <= 0 or owner_earnings_per_share <= 0:
        return None
    cumulative = 0.0
    annual = owner_earnings_per_share
    for year in range(1, max_years + 1):
        annual *= 1 + growth_rate
        previous = cumulative
        cumulative += annual
        if cumulative >= price:
            fraction = (price - previous) / annual
            return (year - 1) + max(0.0, min(1.0, fraction))
    return None


def compute_valuation_features(
    periods: Iterable[RawFinancialPeriod],
    *,
    current_price: float,
    assumptions: InternalValuationAssumptions,
) -> ValuationFeatures:
    annual = sorted(
        (row for row in periods if row.period_type.strip().upper() == "ANNUAL"),
        key=lambda item: item.period_end,
    )
    if not annual:
        raise InternalFeatureError("need an annual financial period for valuation")
    latest = annual[-1]
    owner_earnings = latest.operating_cash_flow - assumptions.maintenance_capex
    if owner_earnings <= 0:
        raise InternalFeatureError("normalized owner earnings must be positive")

    common = {
        "owner_earnings": owner_earnings,
        "shares": latest.shares_outstanding,
        "discount_rate": assumptions.discount_rate,
        "terminal_growth_rate": assumptions.terminal_growth_rate,
        "years": assumptions.horizon_years,
    }
    bear = _dcf_per_share(growth_rate=assumptions.bear_growth_rate, **common)
    base = _dcf_per_share(growth_rate=assumptions.base_growth_rate, **common)
    bull = _dcf_per_share(growth_rate=assumptions.bull_growth_rate, **common)
    mos = (base - current_price) / base * 100 if base > 0 else -100.0
    upside = (base / current_price - 1) * 100
    downside_bear = (bear / current_price - 1) * 100
    payback = _payback_years(current_price, owner_earnings / latest.shares_outstanding, assumptions.base_growth_rate)
    return ValuationFeatures(
        normalized_owner_earnings=round(owner_earnings, 4), bear_fair_value=round(bear, 4),
        base_fair_value=round(base, 4), bull_fair_value=round(bull, 4), margin_of_safety_pct=round(mos, 4),
        upside_to_base_pct=round(upside, 4), downside_to_bear_pct=round(downside_bear, 4),
        payback_years=round(payback, 4) if payback is not None else None,
    )
