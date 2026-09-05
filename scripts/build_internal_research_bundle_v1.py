#!/usr/bin/env python3
"""Build the fail-closed StockRadar internal research bundle from Research Decision V7.

The output deliberately contains the full canonical 405-HOSE universe, while only rows
already marked operational_research_ready_v7=True are eligible for the private cache.
This builder never opens public publication or catalyst/institutional alpha gates.
"""

from __future__ import annotations

import argparse
from datetime import datetime
import json
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

EXPECTED_HOSE = 405
PUBLICATION_BLOCKERS = ("DATA_RIGHTS", "COMPLIANCE", "ACTIVE_PRODUCTION_MANIFEST")


def as_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None:
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        if pd.isna(value):
            return False
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "y", "t"}


def clean(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        if pd.isna(value) or not math.isfinite(float(value)):
            return None
        return float(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (str, int, bool)):
        return value
    return str(value)


def pick(row: pd.Series, key: str, default: Any = None) -> Any:
    return clean(row[key]) if key in row.index else default


def read_manifest(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Manifest root must be an object: {path}")
    return data


def make_payload(row: pd.Series, publication_blockers: list[str]) -> dict[str, Any]:
    ticker = str(row["ticker"]).strip().upper()
    research_ready = as_bool(row.get("operational_research_ready_v7"))
    execution_ready = as_bool(row.get("execution_ready_internal_v7"))
    source_public_action = as_bool(row.get("public_action_allowed_v7"))
    catalyst_alpha = pick(row, "catalyst_alpha_weight_v7", 0)
    institutional_alpha = pick(row, "institutional_alpha_weight_v7", 0)

    if source_public_action:
        raise ValueError(f"{ticker}: V7 public action unexpectedly enabled")
    if catalyst_alpha not in (None, 0, 0.0):
        raise ValueError(f"{ticker}: catalyst alpha must remain zero, got {catalyst_alpha}")
    if institutional_alpha not in (None, 0, 0.0):
        raise ValueError(f"{ticker}: institutional alpha must remain zero, got {institutional_alpha}")

    # Lossless normalized V7 context is retained so downstream AI can use every field
    # without the bundle builder silently changing the research model.
    research_v7 = {str(k): clean(v) for k, v in row.items()}

    payload = {
        "ticker": ticker,
        "company_type": pick(row, "company_type"),
        "business_bucket": pick(row, "business_bucket"),
        "sector": pick(row, "sector_v4"),
        "quote": {
            "price": pick(row, "price"),
        },
        "setup": {
            "candidate_setup": pick(row, "candidate_setup"),
            "radar_status_v7": pick(row, "radar_status_v7"),
            "new_position_state_v5": pick(row, "new_position_state_v5"),
            "holding_state_v5": pick(row, "holding_state_v5"),
            "scan_sla_ready_v7": as_bool(row.get("scan_sla_ready_v7")),
        },
        "trade_plan": {
            "buy_zone_low": pick(row, "buy_zone_low_v5"),
            "buy_zone_high": pick(row, "buy_zone_high_v5"),
            "position_initial_pct": pick(row, "position_initial_pct_v5"),
            "stop_loss": pick(row, "stop_loss_v5"),
            "downside_to_stop_pct": pick(row, "downside_to_stop_pct_v5"),
            "target_near": pick(row, "target_near_rr2_v5"),
            "target_3_6m": pick(row, "target_3_6m_v5"),
            "target_12m": pick(row, "target_12m_v5"),
            "upside_from_entry_to_base_pct": pick(row, "upside_from_entry_to_base_pct_v5"),
            "risk_reward_to_base": pick(row, "rr_to_base_v5"),
        },
        "scores": {
            "radar_score_v7": pick(row, "radar_score_v7"),
            "technical_score": pick(row, "technical_score"),
            "flow_score_v4": pick(row, "flow_score_v4"),
            "fundamental_domain_score_v4": pick(row, "fundamental_domain_score_v4"),
            "valuation_domain_score_v4": pick(row, "valuation_domain_score_v4"),
            "sector_strength_score": pick(row, "sector_strength_score"),
            "market_score": pick(row, "market_score"),
            "supply_demand_score_v1": pick(row, "supply_demand_score_v1"),
            "liquidity_score_v4": pick(row, "liquidity_score_v4"),
            "risk_score": pick(row, "risk_score"),
            "factor_coverage_pct_v6": pick(row, "factor_coverage_pct_v6"),
            "decision_confidence_v5": pick(row, "decision_confidence_v5"),
        },
        "market_context": {
            "market_regime": pick(row, "market_regime"),
            "sector_regime": pick(row, "sector_regime"),
            "sector_strength_score": pick(row, "sector_strength_score"),
        },
        "fundamental_valuation": {
            "fundamental_confidence_v4": pick(row, "fundamental_confidence_v4"),
            "valuation_score_confidence_v4": pick(row, "valuation_score_confidence_v4"),
        },
        "supply_institutional": {
            "free_float_proxy_pct": pick(row, "free_float_proxy_pct"),
            "float_turnover20_pct": pick(row, "float_turnover20_pct"),
            "institutional_context_ready": as_bool(row.get("institutional_context_ready")),
            "institutional_context_note": pick(row, "institutional_context_note"),
            "institutional_alpha_weight_v7": 0,
        },
        "risk": {
            "atr20_pct": pick(row, "atr20_pct"),
            "realized_vol20_pct": pick(row, "realized_vol20_pct"),
            "max_drawdown60_pct": pick(row, "max_drawdown60_pct"),
            "decision_block_reasons_v5": pick(row, "decision_block_reasons_v5"),
            "execution_block_reasons_v7": pick(row, "execution_block_reasons_v7"),
        },
        "catalyst": {
            "data_ready_v2": as_bool(row.get("catalyst_data_ready_v2")),
            "confidence_v3": pick(row, "catalyst_confidence_v3"),
            "official_verified_v3": as_bool(row.get("catalyst_official_verified_v3")),
            "verification_state_v3": pick(row, "catalyst_verification_state_v3"),
            "official_items_90d_v3": pick(row, "official_items_90d_v3"),
            "official_items_30d_v3": pick(row, "official_items_30d_v3"),
            "latest_official_time_v3": pick(row, "latest_official_catalyst_time_v3"),
            "latest_official_title_v3": pick(row, "latest_official_catalyst_title_v3"),
            "official_hose_source_ready_v3": as_bool(row.get("official_hose_source_ready_v3")),
            "alpha_weight_v7": 0,
        },
        "corporate_action": {
            "source_ready_v2": as_bool(row.get("corporate_action_source_ready_v2")),
            "source_coverage_ratio_v2": pick(row, "corporate_action_source_coverage_ratio_v2"),
            "pagination_complete_v2": as_bool(row.get("corporate_action_pagination_complete_v2")),
            "gate_v2": pick(row, "corporate_action_gate_v2"),
            "review_required_v2": as_bool(row.get("corporate_action_review_required_v2")),
            "price_adjustment_reconciliation_required_v2": as_bool(row.get("price_adjustment_reconciliation_required_v2")),
            "next_sensitive_record_date_v2": pick(row, "next_sensitive_record_date_v2"),
            "next_sensitive_event_type_v2": pick(row, "next_sensitive_event_type_v2"),
            "next_sensitive_event_title_v2": pick(row, "next_sensitive_event_title_v2"),
            "days_to_next_sensitive_event_v2": pick(row, "days_to_next_sensitive_event_v2"),
            "execution_clear_v7": as_bool(row.get("corporate_action_execution_clear_v7")),
        },
        "release": {
            "internal_research_ready": research_ready,
            "internal_execution_ready": execution_ready,
            "decision_candidate_v7": as_bool(row.get("decision_candidate_v7")),
            "public_action_allowed": False,
            "public_release_allowed": False,
            "alpha_weight_allowed": False,
            "public_gate": pick(row, "public_gate_v7"),
            "publication_blockers": publication_blockers,
            "data_rights": "PENDING",
            "compliance": "PENDING",
            "active_production_manifest": False,
        },
        "research_v7": research_v7,
    }
    return payload


def build(args: argparse.Namespace) -> tuple[Path, Path]:
    unified_path = Path(args.unified_v7)
    manifest_path = Path(args.manifest)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(unified_path)
    manifest = read_manifest(manifest_path)
    if len(df) != EXPECTED_HOSE or df["ticker"].astype(str).str.upper().nunique() != EXPECTED_HOSE:
        raise ValueError(f"Research V7 canonical HOSE must be {EXPECTED_HOSE}, got rows={len(df)} unique={df['ticker'].nunique()}")
    if int(manifest.get("canonical_hose") or 0) != EXPECTED_HOSE:
        raise ValueError("V7 manifest canonical_hose is not 405")
    if manifest.get("public_action_allowed") is not False:
        raise ValueError("V7 manifest public action must remain false")
    if int(manifest.get("catalyst_alpha_weight") or 0) != 0:
        raise ValueError("V7 catalyst alpha must remain zero")
    if int(manifest.get("institutional_alpha_weight") or 0) != 0:
        raise ValueError("V7 institutional alpha must remain zero")

    tickers = df["ticker"].astype(str).str.strip().str.upper()
    if tickers.duplicated().any():
        dupes = sorted(set(tickers[tickers.duplicated()].tolist()))
        raise ValueError(f"Duplicate tickers: {dupes[:10]}")

    publication_blockers = list(manifest.get("publication_blockers") or PUBLICATION_BLOCKERS)
    required = set(PUBLICATION_BLOCKERS)
    if not required.issubset(set(publication_blockers)):
        publication_blockers = list(dict.fromkeys(publication_blockers + list(PUBLICATION_BLOCKERS)))

    df = df.copy()
    df["ticker"] = tickers
    df = df.sort_values("ticker")

    payloads: dict[str, dict[str, Any]] = {}
    for _, row in df.iterrows():
        ticker = str(row["ticker"])
        payloads[ticker] = make_payload(row, publication_blockers)

    internal_ready_count = sum(bool(p["release"]["internal_research_ready"]) for p in payloads.values())
    execution_ready_count = sum(bool(p["release"]["internal_execution_ready"]) for p in payloads.values())
    decision_candidate_count = sum(bool(p["release"]["decision_candidate_v7"]) for p in payloads.values())

    expected_ready = int(manifest.get("operational_research_ready") or 0)
    expected_execution = int(manifest.get("execution_ready_internal") or 0)
    expected_decisions = int(manifest.get("decision_candidates") or 0)
    if internal_ready_count != expected_ready:
        raise ValueError(f"Internal research-ready mismatch: bundle={internal_ready_count} manifest={expected_ready}")
    if execution_ready_count != expected_execution:
        raise ValueError(f"Execution-ready mismatch: bundle={execution_ready_count} manifest={expected_execution}")
    if decision_candidate_count != expected_decisions:
        raise ValueError(f"Decision-candidate mismatch: bundle={decision_candidate_count} manifest={expected_decisions}")

    now_vn = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
    generated_at_vn = now_vn.isoformat(timespec="seconds")
    as_of_date = str(manifest.get("as_of") or args.as_of or "").strip()
    if not as_of_date:
        raise ValueError("Missing as_of date")

    bundle = {
        "schema_version": "STOCKRADAR_TICKER_LOOKUP_INTERNAL_V1",
        "as_of_date": as_of_date,
        "generated_at_vn": generated_at_vn,
        "exchange": "HOSE",
        "universe_count": EXPECTED_HOSE,
        "data_role": "INTERNAL_BACKEND_RESEARCH",
        "source_updated_at": generated_at_vn,
        "source_version": "STOCKRADAR_RESEARCH_DECISION_V7",
        "price_snapshot_status": "RESEARCH_V7_VALIDATED_SNAPSHOT",
        "internal_research_ready_count": internal_ready_count,
        "decision_candidate_count": decision_candidate_count,
        "execution_ready_internal_count": execution_ready_count,
        "authoritative_corporate_action_source_ready": bool(manifest.get("authoritative_corporate_action_source_ready") is True),
        "official_hose_catalyst_source_ready": bool(manifest.get("official_hose_catalyst_source_ready") is True),
        "catalyst_alpha_weight_allowed": False,
        "institutional_alpha_weight_allowed": False,
        "public_release_allowed": False,
        "public_action_allowed": False,
        "publication_blockers": publication_blockers,
        "tickers": payloads,
    }

    if getattr(args, 'data_layer', None):
        detail = json.loads(Path(args.data_layer).read_text(encoding='utf-8'))
        if detail.get('schema_version') != 'stockradar.data.v1':
            raise ValueError('INVALID_DATA_LAYER')
        if {r['symbol'] for r in detail['records']} != set(payloads):
            raise ValueError('DATA_LAYER_UNIVERSE_MISMATCH')
        # Use observation date, never the workflow execution date to freshen old bars.
        as_of_date = detail['as_of_date']
        bundle['as_of_date'] = as_of_date
        bundle['data_layer'] = detail

    filename = f"stockradar_ticker_lookup_internal_405_{as_of_date}.json"
    output_path = out_dir / filename
    output_path.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    qa = {
        "schema_version": "STOCKRADAR_INTERNAL_RESEARCH_BUNDLE_MANIFEST_V1",
        "generated_at_vn": generated_at_vn,
        "as_of_date": as_of_date,
        "bundle_file": filename,
        "canonical_hose": EXPECTED_HOSE,
        "unique_tickers": len(payloads),
        "internal_research_ready_count": internal_ready_count,
        "decision_candidate_count": decision_candidate_count,
        "execution_ready_internal_count": execution_ready_count,
        "source_v7_manifest": manifest,
        "catalyst_alpha_weight_allowed": False,
        "institutional_alpha_weight_allowed": False,
        "public_release_allowed": False,
        "publication_blockers": publication_blockers,
        "qa_pass": True,
    }
    qa_path = out_dir / f"stockradar_ticker_lookup_internal_405_{as_of_date}_manifest.json"
    qa_path.write_text(json.dumps(qa, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")

    print(json.dumps({
        "bundle": str(output_path),
        "manifest": str(qa_path),
        "canonical_hose": EXPECTED_HOSE,
        "internal_research_ready_count": internal_ready_count,
        "decision_candidate_count": decision_candidate_count,
        "execution_ready_internal_count": execution_ready_count,
        "public_release_allowed": False,
    }, ensure_ascii=False))
    return output_path, qa_path


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--unified-v7", required=True)
    p.add_argument("--manifest", required=True)
    p.add_argument("--output-dir", default="artifacts/internal-research-bundle")
    p.add_argument("--as-of")
    p.add_argument("--data-layer")
    build(p.parse_args())


if __name__ == "__main__":
    main()
