from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from statistics import fmean
from typing import Any, Iterable, Mapping, Sequence

from .internal_engine import InternalStockComputation, build_top_hose_from_internal, compute_stock
from .internal_features import (
    InternalValuationAssumptions,
    RawBar,
    RawFinancialPeriod,
    StockRadarResearchAssessment,
)
from .models import UniverseSnapshot
from .production_bundle import build_manifest_from_descriptor, load_descriptor
from .production_data import ProductionDataGateResult, validate_production_manifest


RAW_PIPELINE_VERSION = "STOCKRADAR_RAW_PIPELINE_V1"
BENCHMARK_METHOD = "HOSE_EQUAL_WEIGHT_INTERNAL_V1"
INTERNAL_INPUT_ORIGIN = "STOCKRADAR_RESEARCH"


class RawPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class SecurityIdentity:
    ticker: str
    company_name: str
    sector: str
    exchange: str


@dataclass(frozen=True)
class RawPipelineResult:
    manifest: Mapping[str, Any]
    gate: ProductionDataGateResult
    snapshot: UniverseSnapshot
    benchmark_bars: tuple[RawBar, ...]
    computations: tuple[InternalStockComputation, ...]
    top_hose: Mapping[str, Any]

    def public_payload(self) -> dict[str, Any]:
        if not self.gate.passed or self.top_hose.get("ranking_valid") is not True:
            raise RawPipelineError("public Top HOSE output requires a passed production gate and valid ranking")
        payload = dict(self.top_hose)
        payload["pipeline_version"] = RAW_PIPELINE_VERSION
        payload["benchmark_method"] = BENCHMARK_METHOD
        payload["input_role"] = "RAW_INPUT_ONLY"
        payload["calculation_origin"] = "STOCKRADAR_ENGINE"
        payload["external_scores_accepted"] = False
        return payload

    def private_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "pipeline_version": RAW_PIPELINE_VERSION,
            "benchmark_method": BENCHMARK_METHOD,
            "snapshot": self.snapshot.to_dict(),
            "gate": self.gate.to_dict(),
            "items": [row.to_dict() for row in self.computations],
        }


def _read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise RawPipelineError(f"CSV header missing: {path.name}")
        fields = tuple(str(name).strip() for name in reader.fieldnames)
        return fields, [dict(row) for row in reader]


def _require_columns(fields: Sequence[str], required: Iterable[str], dataset: str) -> None:
    missing = [name for name in required if name not in fields]
    if missing:
        raise RawPipelineError(f"{dataset} missing required raw column(s): {', '.join(missing)}")


def _number(value: object, *, dataset: str, field: str, allow_blank: bool = False) -> float | None:
    text = str(value or "").strip().replace(",", "")
    if not text:
        if allow_blank:
            return None
        raise RawPipelineError(f"{dataset}.{field} cannot be blank")
    try:
        return float(text)
    except ValueError as error:
        raise RawPipelineError(f"{dataset}.{field} must be numeric: {text!r}") from error


def _ticker(value: object, dataset: str) -> str:
    ticker = str(value or "").strip().upper()
    if (
        len(ticker) != 3
        or not ticker.isascii()
        or not ticker.isalnum()
        or not any(ch.isalpha() for ch in ticker)
    ):
        raise RawPipelineError(f"invalid ticker in {dataset}: {ticker!r}")
    return ticker


def _resolve_dataset(bundle_dir: Path, descriptor: Mapping[str, Any], name: str) -> Path:
    datasets = descriptor.get("datasets")
    if not isinstance(datasets, Mapping):
        raise RawPipelineError("descriptor.datasets is required")
    spec = datasets.get(name)
    if not isinstance(spec, Mapping):
        raise RawPipelineError(f"descriptor dataset missing: {name}")
    relative = str(spec.get("path") or "").strip()
    if not relative:
        raise RawPipelineError(f"descriptor path missing: {name}")
    root = bundle_dir.resolve()
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as error:
        raise RawPipelineError(f"dataset path escapes bundle: {name}") from error
    if not target.is_file():
        raise RawPipelineError(f"dataset file missing: {name}")
    return target


def load_security_master(path: Path) -> dict[str, SecurityIdentity]:
    fields, rows = _read_csv(path)
    _require_columns(fields, ("ticker", "name", "exchange", "sector"), "security_master")
    result: dict[str, SecurityIdentity] = {}
    for row in rows:
        ticker = _ticker(row.get("ticker"), "security_master")
        if ticker in result:
            raise RawPipelineError(f"duplicate security_master ticker: {ticker}")
        exchange = str(row.get("exchange") or "").strip().upper()
        if exchange != "HOSE":
            raise RawPipelineError(f"non-HOSE ticker in security_master: {ticker}")
        sector = str(row.get("sector") or "").strip()
        if not sector:
            raise RawPipelineError(f"sector is required for {ticker}")
        result[ticker] = SecurityIdentity(
            ticker=ticker,
            company_name=str(row.get("name") or ticker).strip() or ticker,
            sector=sector,
            exchange=exchange,
        )
    if not result:
        raise RawPipelineError("security_master is empty")
    return result


def load_raw_ohlcv(path: Path) -> dict[str, list[RawBar]]:
    fields, rows = _read_csv(path)
    _require_columns(fields, ("ticker", "timestamp", "open", "high", "low", "close", "volume"), "ohlcv")
    grouped: dict[str, list[RawBar]] = {}
    for row in rows:
        ticker = _ticker(row.get("ticker"), "ohlcv")
        timestamp = str(row.get("timestamp") or "").strip()
        bar = RawBar(
            timestamp=timestamp,
            open=float(_number(row.get("open"), dataset="ohlcv", field="open")),
            high=float(_number(row.get("high"), dataset="ohlcv", field="high")),
            low=float(_number(row.get("low"), dataset="ohlcv", field="low")),
            close=float(_number(row.get("close"), dataset="ohlcv", field="close")),
            volume=float(_number(row.get("volume"), dataset="ohlcv", field="volume")),
        )
        grouped.setdefault(ticker, []).append(bar)
    for ticker, bars in grouped.items():
        bars.sort(key=lambda item: item.timestamp)
        timestamps = [bar.timestamp for bar in bars]
        if len(timestamps) != len(set(timestamps)):
            raise RawPipelineError(f"duplicate OHLCV timestamp for {ticker}")
    return grouped


def load_raw_financials(path: Path) -> dict[str, list[RawFinancialPeriod]]:
    fields, rows = _read_csv(path)
    required = (
        "ticker", "period_end", "period_type", "revenue", "net_income", "total_assets",
        "equity", "total_debt", "cash", "operating_cash_flow", "capex", "shares_outstanding",
    )
    _require_columns(fields, required, "fundamentals")
    grouped: dict[str, list[RawFinancialPeriod]] = {}
    for row in rows:
        ticker = _ticker(row.get("ticker"), "fundamentals")
        period = RawFinancialPeriod(
            period_end=str(row.get("period_end") or "").strip(),
            period_type=str(row.get("period_type") or "").strip(),
            revenue=float(_number(row.get("revenue"), dataset="fundamentals", field="revenue")),
            net_income=float(_number(row.get("net_income"), dataset="fundamentals", field="net_income")),
            total_assets=float(_number(row.get("total_assets"), dataset="fundamentals", field="total_assets")),
            equity=float(_number(row.get("equity"), dataset="fundamentals", field="equity")),
            total_debt=float(_number(row.get("total_debt"), dataset="fundamentals", field="total_debt")),
            cash=float(_number(row.get("cash"), dataset="fundamentals", field="cash")),
            operating_cash_flow=float(_number(row.get("operating_cash_flow"), dataset="fundamentals", field="operating_cash_flow")),
            capex=float(_number(row.get("capex"), dataset="fundamentals", field="capex")),
            shares_outstanding=float(_number(row.get("shares_outstanding"), dataset="fundamentals", field="shares_outstanding")),
            operating_profit=_number(row.get("operating_profit"), dataset="fundamentals", field="operating_profit", allow_blank=True),
            depreciation_amortization=_number(row.get("depreciation_amortization"), dataset="fundamentals", field="depreciation_amortization", allow_blank=True),
        )
        grouped.setdefault(ticker, []).append(period)
    return grouped


def _previous_close(bars: Sequence[RawBar], effective_date: str) -> float:
    previous = [bar.close for bar in bars if bar.timestamp < effective_date]
    if not previous:
        raise RawPipelineError(f"corporate action {effective_date} has no previous close")
    return previous[-1]


def _adjust_before(bars: Sequence[RawBar], effective_date: str, price_factor: float, volume_factor: float) -> list[RawBar]:
    if price_factor <= 0 or volume_factor <= 0:
        raise RawPipelineError("corporate action adjustment factors must be positive")
    adjusted: list[RawBar] = []
    for bar in bars:
        if bar.timestamp < effective_date:
            adjusted.append(RawBar(
                timestamp=bar.timestamp,
                open=bar.open * price_factor,
                high=bar.high * price_factor,
                low=bar.low * price_factor,
                close=bar.close * price_factor,
                volume=bar.volume * volume_factor,
            ))
        else:
            adjusted.append(bar)
    return adjusted


def apply_corporate_actions(
    bars_by_ticker: Mapping[str, Sequence[RawBar]],
    path: Path,
) -> dict[str, list[RawBar]]:
    fields, rows = _read_csv(path)
    if not rows:
        return {ticker: list(bars) for ticker, bars in bars_by_ticker.items()}
    _require_columns(fields, ("ticker", "effective_date", "event_type"), "corporate_actions")
    result = {ticker: list(bars) for ticker, bars in bars_by_ticker.items()}
    sorted_rows = sorted(rows, key=lambda row: (str(row.get("effective_date") or ""), str(row.get("ticker") or "")))
    for row in sorted_rows:
        ticker = _ticker(row.get("ticker"), "corporate_actions")
        if ticker not in result:
            continue
        effective_date = str(row.get("effective_date") or "").strip()
        event_type = str(row.get("event_type") or "").strip().upper()
        if not effective_date:
            raise RawPipelineError(f"corporate action effective_date missing for {ticker}")
        bars = result[ticker]
        previous_close = _previous_close(bars, effective_date)

        if event_type == "SHARE_CHANGE":
            old_shares = float(_number(row.get("old_shares"), dataset="corporate_actions", field="old_shares"))
            new_shares = float(_number(row.get("new_shares"), dataset="corporate_actions", field="new_shares"))
            if old_shares <= 0 or new_shares <= 0:
                raise RawPipelineError("SHARE_CHANGE ratios must be positive")
            price_factor = old_shares / new_shares
            volume_factor = new_shares / old_shares
        elif event_type == "CASH_DIVIDEND":
            cash_amount = float(_number(row.get("cash_amount_per_share"), dataset="corporate_actions", field="cash_amount_per_share"))
            if cash_amount < 0 or cash_amount >= previous_close:
                raise RawPipelineError("invalid CASH_DIVIDEND amount")
            price_factor = (previous_close - cash_amount) / previous_close
            volume_factor = 1.0
        elif event_type == "RIGHTS_ISSUE":
            rights_ratio = float(_number(row.get("new_shares_per_old_share"), dataset="corporate_actions", field="new_shares_per_old_share"))
            subscription_price = float(_number(row.get("subscription_price"), dataset="corporate_actions", field="subscription_price"))
            if rights_ratio < 0 or subscription_price < 0:
                raise RawPipelineError("invalid RIGHTS_ISSUE terms")
            terp = (previous_close + rights_ratio * subscription_price) / (1 + rights_ratio)
            price_factor = terp / previous_close
            volume_factor = 1 + rights_ratio
        else:
            raise RawPipelineError(f"unsupported corporate action type: {event_type or '<blank>'}")
        result[ticker] = _adjust_before(bars, effective_date, price_factor, volume_factor)
    return result


def _load_internal_json(path: Path, label: str) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise RawPipelineError(f"{label} must be a JSON object")
    if str(payload.get("calculation_origin") or "").strip() != INTERNAL_INPUT_ORIGIN:
        raise RawPipelineError(f"{label} calculation_origin must be {INTERNAL_INPUT_ORIGIN}")
    items = payload.get("items")
    if not isinstance(items, list):
        raise RawPipelineError(f"{label}.items must be a list")
    clean: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, Mapping):
            raise RawPipelineError(f"{label} item must be an object")
        clean.append(dict(item))
    return clean


def load_research_assessments(path: Path) -> dict[str, StockRadarResearchAssessment]:
    result: dict[str, StockRadarResearchAssessment] = {}
    for item in _load_internal_json(path, "research"):
        ticker = _ticker(item.get("ticker"), "research")
        if ticker in result:
            raise RawPipelineError(f"duplicate research ticker: {ticker}")
        result[ticker] = StockRadarResearchAssessment(
            meaning_score=float(_number(item.get("meaning_score"), dataset="research", field="meaning_score")),
            moat_score=float(_number(item.get("moat_score"), dataset="research", field="moat_score")),
            management_score=float(_number(item.get("management_score"), dataset="research", field="management_score")),
            catalyst_score=float(_number(item.get("catalyst_score"), dataset="research", field="catalyst_score")),
            event_risk_pass=bool(item.get("event_risk_pass", True)),
        )
    return result


def load_valuation_assumptions(path: Path) -> dict[str, InternalValuationAssumptions]:
    result: dict[str, InternalValuationAssumptions] = {}
    for item in _load_internal_json(path, "valuation"):
        ticker = _ticker(item.get("ticker"), "valuation")
        if ticker in result:
            raise RawPipelineError(f"duplicate valuation ticker: {ticker}")
        result[ticker] = InternalValuationAssumptions(
            maintenance_capex=float(_number(item.get("maintenance_capex"), dataset="valuation", field="maintenance_capex")),
            bear_growth_rate=float(_number(item.get("bear_growth_rate"), dataset="valuation", field="bear_growth_rate")),
            base_growth_rate=float(_number(item.get("base_growth_rate"), dataset="valuation", field="base_growth_rate")),
            bull_growth_rate=float(_number(item.get("bull_growth_rate"), dataset="valuation", field="bull_growth_rate")),
            discount_rate=float(_number(item.get("discount_rate"), dataset="valuation", field="discount_rate")),
            terminal_growth_rate=float(_number(item.get("terminal_growth_rate"), dataset="valuation", field="terminal_growth_rate")),
            horizon_years=int(float(_number(item.get("horizon_years", 5), dataset="valuation", field="horizon_years"))),
        )
    return result


def build_internal_equal_weight_benchmark(
    bars_by_ticker: Mapping[str, Sequence[RawBar]],
    tickers: Sequence[str],
    *,
    minimum_bars: int = 252,
) -> tuple[RawBar, ...]:
    if not tickers:
        raise RawPipelineError("benchmark requires at least one valid ticker")
    timestamp_sets = []
    maps: dict[str, dict[str, RawBar]] = {}
    for ticker in tickers:
        bars = bars_by_ticker.get(ticker)
        if not bars:
            raise RawPipelineError(f"missing OHLCV for benchmark ticker: {ticker}")
        mapping = {bar.timestamp: bar for bar in bars}
        maps[ticker] = mapping
        timestamp_sets.append(set(mapping))
    common = sorted(set.intersection(*timestamp_sets))
    if len(common) < minimum_bars:
        raise RawPipelineError(f"internal HOSE benchmark needs at least {minimum_bars} common bars")
    common = common[-minimum_bars:]

    first_close = {ticker: maps[ticker][common[0]].close for ticker in tickers}
    benchmark: list[RawBar] = []
    for timestamp in common:
        normalized = []
        total_volume = 0.0
        for ticker in tickers:
            bar = maps[ticker][timestamp]
            base = first_close[ticker]
            normalized.append((bar.open / base * 100, bar.high / base * 100, bar.low / base * 100, bar.close / base * 100))
            total_volume += bar.volume
        benchmark.append(RawBar(
            timestamp=timestamp,
            open=fmean(values[0] for values in normalized),
            high=fmean(values[1] for values in normalized),
            low=fmean(values[2] for values in normalized),
            close=fmean(values[3] for values in normalized),
            volume=total_volume,
        ))
    return tuple(benchmark)


def _validate_internal_coverage(valid_tickers: set[str], values: Mapping[str, object], label: str) -> None:
    missing = sorted(valid_tickers - set(values))
    outside = sorted(set(values) - valid_tickers)
    if missing:
        raise RawPipelineError(f"{label} missing valid HOSE ticker(s): {', '.join(missing[:10])}")
    if outside:
        raise RawPipelineError(f"{label} contains ticker outside valid HOSE universe: {', '.join(outside[:10])}")


def compute_top_from_bundle(
    *,
    bundle_dir: str | Path,
    descriptor_path: str | Path,
    research_path: str | Path,
    valuation_path: str | Path,
    now: datetime | None = None,
    max_age_seconds: int = 21_600,
    strongest_limit: int = 30,
    per_sector_limit: int = 3,
) -> RawPipelineResult:
    root = Path(bundle_dir).resolve()
    descriptor = load_descriptor(descriptor_path)
    manifest = build_manifest_from_descriptor(root, descriptor)
    gate = validate_production_manifest(manifest, now=now, max_age_seconds=max_age_seconds)
    if not gate.passed:
        raise RawPipelineError("production raw-data gate failed: " + ", ".join(gate.failures))

    snapshot_raw = manifest.get("snapshot")
    if not isinstance(snapshot_raw, Mapping):
        raise RawPipelineError("validated manifest snapshot missing")
    snapshot = UniverseSnapshot.from_dict(dict(snapshot_raw))

    security = load_security_master(_resolve_dataset(root, descriptor, "security_master"))
    all_tickers = set(security)
    if len(all_tickers) != snapshot.expected_total:
        raise RawPipelineError("security_master count does not match snapshot expected_total")
    excluded = {item.ticker for item in snapshot.exclusion_log}
    if not excluded.issubset(all_tickers):
        raise RawPipelineError("snapshot exclusion contains ticker outside security_master")
    valid_tickers = all_tickers - excluded
    if len(valid_tickers) != snapshot.valid_count:
        raise RawPipelineError("valid ticker count does not reconcile to snapshot")

    raw_bars = load_raw_ohlcv(_resolve_dataset(root, descriptor, "ohlcv"))
    adjusted_bars = apply_corporate_actions(raw_bars, _resolve_dataset(root, descriptor, "corporate_actions"))
    financials = load_raw_financials(_resolve_dataset(root, descriptor, "fundamentals"))
    research = load_research_assessments(Path(research_path))
    valuations = load_valuation_assumptions(Path(valuation_path))

    for label, mapping in (("OHLCV", adjusted_bars), ("fundamentals", financials)):
        missing = sorted(valid_tickers - set(mapping))
        if missing:
            raise RawPipelineError(f"{label} missing valid HOSE ticker(s): {', '.join(missing[:10])}")
    _validate_internal_coverage(valid_tickers, research, "StockRadar research")
    _validate_internal_coverage(valid_tickers, valuations, "StockRadar valuation assumptions")

    ordered_tickers = sorted(valid_tickers)
    benchmark = build_internal_equal_weight_benchmark(adjusted_bars, ordered_tickers)
    computations: list[InternalStockComputation] = []
    for ticker in ordered_tickers:
        try:
            computations.append(compute_stock(
                ticker=ticker,
                sector=security[ticker].sector,
                bars=adjusted_bars[ticker],
                benchmark_bars=benchmark,
                financial_periods=financials[ticker],
                research=research[ticker],
                valuation_assumptions=valuations[ticker],
            ))
        except Exception as error:
            raise RawPipelineError(f"StockRadar computation failed for {ticker}: {error}") from error

    top_hose = build_top_hose_from_internal(
        snapshot,
        computations,
        strongest_limit=strongest_limit,
        per_sector_limit=per_sector_limit,
    )
    if top_hose.get("ranking_valid") is not True:
        failures = top_hose.get("gate", {}).get("failures", []) if isinstance(top_hose.get("gate"), Mapping) else []
        raise RawPipelineError("Top HOSE ranking gate failed: " + ", ".join(str(item) for item in failures))

    top_hose = dict(top_hose)
    top_hose["benchmark_method"] = BENCHMARK_METHOD
    top_hose["pipeline_version"] = RAW_PIPELINE_VERSION
    top_hose["scanned_valid_tickers"] = len(computations)
    return RawPipelineResult(
        manifest=manifest,
        gate=gate,
        snapshot=snapshot,
        benchmark_bars=benchmark,
        computations=tuple(computations),
        top_hose=top_hose,
    )


def write_pipeline_outputs(
    result: RawPipelineResult,
    *,
    public_top_path: str | Path,
    private_computations_path: str | Path | None = None,
) -> None:
    public_path = Path(public_top_path)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_text(json.dumps(result.public_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if private_computations_path is not None:
        private_path = Path(private_computations_path)
        private_path.parent.mkdir(parents=True, exist_ok=True)
        private_path.write_text(json.dumps(result.private_payload(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
