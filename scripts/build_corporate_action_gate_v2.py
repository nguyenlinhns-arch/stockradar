from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_HOSE = 405
SENSITIVE_TYPES = {"DIVIDEND", "RIGHTS_OR_ISSUANCE", "BONUS_SHARES"}


def build(args) -> None:
    universe = pd.read_csv(args.universe)
    events = pd.read_csv(args.events)
    coverage = json.loads(Path(args.coverage).read_text(encoding="utf-8"))
    as_of = pd.Timestamp(args.as_of)
    tickers = sorted(set(universe["ticker"].astype(str).str.strip().str.upper()))
    if len(tickers) != EXPECTED_HOSE:
        raise ValueError(f"canonical HOSE must be {EXPECTED_HOSE}, got {len(tickers)}")

    requested = max(int(coverage.get("days_requested") or 0), 1)
    fetched = int(coverage.get("days_fetched") or 0)
    global_coverage_ratio = float(coverage.get("source_coverage_ratio") or (fetched / requested))
    pagination_complete = bool(coverage.get("pagination_complete") is True and int(coverage.get("days_pagination_incomplete") or 0) == 0)
    source_ready = bool(coverage.get("source_ready") is True and global_coverage_ratio >= 0.98 and pagination_complete)

    events = events.copy()
    if not events.empty:
        events["ticker"] = events["ticker"].astype(str).str.strip().str.upper()
        events["record_date"] = pd.to_datetime(events["record_date"], errors="coerce")
        events["days_from_asof"] = (events["record_date"].dt.normalize() - as_of.normalize()).dt.days
        events["sensitive"] = events["event_type"].isin(SENSITIVE_TYPES)

    rows = []
    for ticker in tickers:
        g = events[events["ticker"].eq(ticker)].copy() if not events.empty else pd.DataFrame()
        sensitive = g[g["sensitive"]] if not g.empty else g
        upcoming = sensitive[sensitive["days_from_asof"].between(0, 30, inclusive="both")] if not sensitive.empty else sensitive
        near = sensitive[sensitive["days_from_asof"].between(-2, 7, inclusive="both")] if not sensitive.empty else sensitive
        recent = sensitive[sensitive["days_from_asof"].between(-5, -1, inclusive="both")] if not sensitive.empty else sensitive
        next_row = upcoming.sort_values("record_date").iloc[0] if not upcoming.empty else None

        if not source_ready:
            gate = "BLOCK_SOURCE_COVERAGE"
        elif not near.empty:
            gate = "BLOCK_NEAR_PRICE_ADJUSTMENT_EVENT"
        elif not recent.empty:
            gate = "BLOCK_RECENT_EVENT_RECONCILIATION"
        elif not upcoming.empty:
            gate = "REVIEW_UPCOMING_30D"
        else:
            gate = "PASS_NO_NEAR_SENSITIVE_EVENT"

        rows.append({
            "ticker": ticker,
            "corporate_action_source_ready_v2": source_ready,
            "corporate_action_source_coverage_ratio_v2": round(global_coverage_ratio, 4),
            "corporate_action_pagination_complete_v2": pagination_complete,
            "corporate_action_event_count_window_v2": int(len(g)),
            "sensitive_event_count_window_v2": int(len(sensitive)),
            "near_sensitive_event_count_v2": int(len(near)),
            "upcoming_sensitive_event_count_30d_v2": int(len(upcoming)),
            "next_sensitive_record_date_v2": next_row["record_date"] if next_row is not None else pd.NaT,
            "next_sensitive_event_type_v2": next_row["event_type"] if next_row is not None else None,
            "next_sensitive_event_title_v2": next_row["title"] if next_row is not None else None,
            "days_to_next_sensitive_event_v2": int(next_row["days_from_asof"]) if next_row is not None else np.nan,
            "corporate_action_gate_v2": gate,
            "corporate_action_action_allowed_v2": gate == "PASS_NO_NEAR_SENSITIVE_EVENT",
            "corporate_action_review_required_v2": gate == "REVIEW_UPCOMING_30D",
            "price_adjustment_reconciliation_required_v2": gate in {"BLOCK_NEAR_PRICE_ADJUSTMENT_EVENT", "BLOCK_RECENT_EVENT_RECONCILIATION"},
        })

    out = pd.DataFrame(rows)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")
    manifest = {
        "schema_version": "STOCKRADAR_CORPORATE_ACTION_GATE_V2",
        "canonical_hose": EXPECTED_HOSE,
        "source_ready": bool(source_ready),
        "source_coverage_ratio": round(global_coverage_ratio, 4),
        "pagination_complete": pagination_complete,
        "days_pagination_incomplete": int(coverage.get("days_pagination_incomplete") or 0),
        "advertised_records_all_markets": int(coverage.get("advertised_records_all_markets") or 0),
        "raw_table_rows_all_markets": int(coverage.get("raw_table_rows_all_markets") or 0),
        "event_rows": int(len(events)),
        "unique_event_tickers": int(events["ticker"].nunique()) if not events.empty else 0,
        "gate_counts": out["corporate_action_gate_v2"].value_counts().to_dict(),
        "policy": "Corporate actions are a price-adjustment/risk gate, never alpha. Source readiness requires complete pagination. Upcoming sensitive events require review; near/recent sensitive events block action until reconciliation passes.",
        "publication_allowed": False,
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--universe", required=True)
    p.add_argument("--events", required=True)
    p.add_argument("--coverage", required=True)
    p.add_argument("--as-of", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--manifest", required=True)
    build(p.parse_args())


if __name__ == "__main__":
    main()
