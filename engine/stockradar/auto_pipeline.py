from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Mapping

from .internal_engine import InternalStockComputation, build_top_hose_from_internal, compute_stock
from .models import UniverseSnapshot
from .production_bundle import build_manifest_from_descriptor, load_descriptor
from .production_data import validate_production_manifest
from .raw_pipeline import (
    BENCHMARK_METHOD,
    RAW_PIPELINE_VERSION,
    RawPipelineError,
    RawPipelineResult,
    _read_csv,
    _resolve_dataset,
    _ticker,
    apply_corporate_actions,
    build_internal_equal_weight_benchmark,
    load_raw_financials,
    load_raw_ohlcv,
    load_security_master,
)


AUTO_PIPELINE_VERSION = "STOCKRADAR_AUTO_PIPELINE_V1"
ADVERSE_EVENT_TYPES = {
    "SUSPENSION",
    "TRADING_SUSPENSION",
    "DELISTING",
    "DEFAULT",
    "BANKRUPTCY",
    "INVESTIGATION",
    "MATERIAL_LITIGATION",
    "QUALIFIED_AUDIT",
    "ADVERSE_AUDIT",
    "GOING_CONCERN",
}
RESOLVED_EVENT_STATUSES = {"RESOLVED", "CLOSED", "COMPLETED", "CLEARED"}


def load_event_risk(path: Path, valid_tickers: set[str]) -> dict[str, bool]:
    """Translate raw dated events into StockRadar's own binary event-risk gate."""
    fields, rows = _read_csv(path)
    result = {ticker: True for ticker in valid_tickers}
    if not rows:
        return result
    if "ticker" not in fields or "event_type" not in fields:
        raise RawPipelineError("non-empty events dataset requires ticker and event_type raw columns")
    for row in rows:
        ticker = _ticker(row.get("ticker"), "events")
        if ticker not in valid_tickers:
            continue
        event_type = str(row.get("event_type") or "").strip().upper()
        status = str(row.get("status") or "").strip().upper()
        if event_type in ADVERSE_EVENT_TYPES and status not in RESOLVED_EVENT_STATUSES:
            result[ticker] = False
    return result


def compute_top_from_bundle_auto(
    *,
    bundle_dir: str | Path,
    descriptor_path: str | Path,
    now: datetime | None = None,
    max_age_seconds: int = 21_600,
    strongest_limit: int = 30,
    per_sector_limit: int = 3,
) -> RawPipelineResult:
    """Compute all StockRadar research, valuation and ranking from validated raw inputs.

    No per-ticker score, rank, recommendation, provider ratio, research score or
    valuation assumption is accepted as an input to this pipeline.
    """
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
    adjusted_bars = apply_corporate_actions(
        raw_bars,
        _resolve_dataset(root, descriptor, "corporate_actions"),
    )
    financials = load_raw_financials(_resolve_dataset(root, descriptor, "fundamentals"))
    event_risk = load_event_risk(_resolve_dataset(root, descriptor, "events"), valid_tickers)

    for label, mapping in (("OHLCV", adjusted_bars), ("fundamentals", financials)):
        missing = sorted(valid_tickers - set(mapping))
        if missing:
            raise RawPipelineError(f"{label} missing valid HOSE ticker(s): {', '.join(missing[:10])}")

    ordered_tickers = sorted(valid_tickers)
    benchmark = build_internal_equal_weight_benchmark(adjusted_bars, ordered_tickers)
    computations: list[InternalStockComputation] = []
    for ticker in ordered_tickers:
        identity = security[ticker]
        try:
            computation = compute_stock(
                ticker=ticker,
                sector=identity.sector,
                company_name=identity.company_name,
                bars=adjusted_bars[ticker],
                benchmark_bars=benchmark,
                financial_periods=financials[ticker],
                research=None,
                valuation_assumptions=None,
                event_risk_pass=event_risk[ticker],
            )
        except Exception as error:
            raise RawPipelineError(f"StockRadar auto computation failed for {ticker}: {error}") from error
        if computation.computation.get("research_origin") != "STOCKRADAR_ENGINE":
            raise RawPipelineError(f"research origin is not internal for {ticker}")
        if computation.computation.get("valuation_assumption_origin") != "STOCKRADAR_ENGINE":
            raise RawPipelineError(f"valuation assumption origin is not internal for {ticker}")
        computations.append(computation)

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
    top_hose.update({
        "benchmark_method": BENCHMARK_METHOD,
        "pipeline_version": AUTO_PIPELINE_VERSION,
        "base_raw_pipeline_version": RAW_PIPELINE_VERSION,
        "scanned_valid_tickers": len(computations),
        "research_input_mode": "STOCKRADAR_AUTO_INTERNAL",
        "valuation_assumption_mode": "STOCKRADAR_AUTO_INTERNAL",
    })
    return RawPipelineResult(
        manifest=manifest,
        gate=gate,
        snapshot=snapshot,
        benchmark_bars=benchmark,
        computations=tuple(computations),
        top_hose=top_hose,
    )
