from __future__ import annotations

import re
from typing import Iterable


CALCULATION_ORIGIN = "STOCKRADAR_ENGINE"
CALCULATION_POLICY_VERSION = "1.0"
EXTERNAL_INPUT_ROLE = "RAW_INPUT_ONLY"

# These fields are outputs of analysis/model logic and may never be imported from
# an external market-data provider into the production decision pipeline.
DERIVED_FIELD_NAMES = {
    "score", "stockradar_score", "rank", "global_rank", "sector_rank", "rating",
    "recommendation", "signal", "setup", "stage", "trend_template", "market_regime",
    "relative_strength", "rs", "rvol", "same_time_rvol", "volume_ratio",
    "pivot", "distance_to_pivot_pct", "extension_pct", "pocket_pivot",
    "early_breakout", "confirmed_breakout", "breakout", "retest", "vcp", "vpa",
    "accumulation", "distribution", "absorption", "shakeout", "selling_climax",
    "tenkan", "kijun", "span_a", "span_b", "chikou", "ichimoku",
    "bollinger_upper", "bollinger_middle", "bollinger_lower", "bollinger_width",
    "pe", "p_e", "forward_pe", "forward_p_e", "pb", "p_b", "peg",
    "ev_ebitda", "roe", "roa", "roic", "gross_margin", "operating_margin",
    "net_margin", "eps", "eps_growth", "revenue_growth", "profit_growth",
    "fcf", "free_cash_flow", "owner_earnings", "payback", "payback_time",
    "fair_value", "sticker_price", "margin_of_safety", "mos", "upside",
    "upside_pct", "downside", "downside_pct", "risk_reward", "rr",
    "buy_zone", "buy_zone_low", "buy_zone_high", "stop", "stop_loss",
    "target", "target_price", "target_near", "target_3_6m", "target_12m",
    "probability", "win_probability", "expected_return", "expected_return_pct",
    "adjusted_close", "adj_close", "adjusted_open", "adjusted_high", "adjusted_low",
}

_DERIVED_PATTERNS = (
    re.compile(r"^(?:sma|ema|ma)_?\d+$"),
    re.compile(r"^(?:rsi|macd)(?:_.*)?$"),
    re.compile(r"^(?:bb|bollinger)(?:_.*)?$"),
    re.compile(r"^(?:ichimoku)(?:_.*)?$"),
)


class ExternalDerivedDataError(ValueError):
    pass


def normalize_field_name(value: object) -> str:
    text = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    return re.sub(r"_+", "_", text)


def is_derived_field(field_name: object) -> bool:
    normalized = normalize_field_name(field_name)
    if normalized in DERIVED_FIELD_NAMES:
        return True
    return any(pattern.match(normalized) for pattern in _DERIVED_PATTERNS)


def validate_external_raw_columns(dataset_name: str, columns: Iterable[object]) -> tuple[str, ...]:
    normalized = tuple(normalize_field_name(column) for column in columns)
    prohibited = tuple(column for column in normalized if is_derived_field(column))
    if prohibited:
        fields = ", ".join(sorted(set(prohibited)))
        raise ExternalDerivedDataError(
            f"external dataset {dataset_name!r} contains StockRadar-derived field(s): {fields}; "
            "external providers may supply raw inputs only"
        )
    return normalized


def computation_provenance() -> dict[str, object]:
    return {
        "calculation_origin": CALCULATION_ORIGIN,
        "calculation_policy_version": CALCULATION_POLICY_VERSION,
        "external_input_role": EXTERNAL_INPUT_ROLE,
        "external_scores_accepted": False,
        "method_stack": [
            "4M_PAYBACK",
            "CANSLIM",
            "VALUATION",
            "SEPA_VCP_STAGE",
            "VPA",
            "POCKET_PIVOT_EARLY_MOMENTUM",
            "ICHIMOKU_BOLLINGER_TRENDLINE",
            "RISK_REWARD",
        ],
    }
