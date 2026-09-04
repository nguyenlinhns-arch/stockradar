from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_HOSE = 405


def _bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series.fillna(False)
    return series.fillna(False).astype(str).str.lower().isin({"true", "1", "yes"})


def _read_optional_json(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _capital_action_context(path: str, tickers: list[str], as_of: pd.Timestamp) -> pd.DataFrame:
    p = Path(path)
    if not p.exists():
        return pd.DataFrame({"ticker": tickers})
    events = pd.read_csv(p)
    if events.empty or "ticker" not in events.columns:
        return pd.DataFrame({"ticker": tickers})
    events["ticker"] = events["ticker"].astype(str).str.strip().str.upper()
    events["publish_time_dt"] = pd.to_datetime(events.get("publish_time"), errors="coerce", utc=True).dt.tz_convert(None)
    events["age_days"] = (as_of.normalize() - events["publish_time_dt"].dt.normalize()).dt.days
    events = events[events["ticker"].isin(tickers)]

    rows = []
    for ticker in tickers:
        g = events[events["ticker"].eq(ticker)].copy()
        recent90 = g[g["age_days"].between(0, 90, inclusive="both")] if not g.empty else g
        recent45 = g[g["age_days"].between(0, 45, inclusive="both")] if not g.empty else g
        latest = recent90.sort_values("publish_time_dt", ascending=False).iloc[0] if not recent90.empty else None
        rows.append(
            {
                "ticker": ticker,
                "news_derived_capital_action_items_90d_v7": int(len(recent90)),
                "news_derived_capital_action_items_45d_v7": int(len(recent45)),
                "news_derived_capital_action_review_required_v7": bool(len(recent45) > 0),
                "latest_news_derived_capital_action_time_v7": latest["publish_time_dt"] if latest is not None else pd.NaT,
                "latest_news_derived_capital_action_title_v7": latest.get("title") if latest is not None else None,
                "capital_action_news_verification_state_v7": "NEWS_DERIVED_UNVERIFIED" if len(recent90) else "NO_RECENT_NEWS_DERIVED_EVENT",
            }
        )
    return pd.DataFrame(rows)


def _corporate_action_gate(path: str | None, tickers: list[str]) -> pd.DataFrame:
    defaults = pd.DataFrame({
        "ticker": tickers,
        "corporate_action_source_ready_v2": False,
        "corporate_action_pagination_complete_v2": False,
        "corporate_action_gate_v2": "BLOCK_SOURCE_COVERAGE",
        "corporate_action_action_allowed_v2": False,
        "corporate_action_review_required_v2": False,
        "price_adjustment_reconciliation_required_v2": False,
    })
    if not path:
        return defaults
    p = Path(path)
    if not p.exists():
        return defaults
    gate = pd.read_csv(p)
    if "ticker" not in gate.columns:
        raise ValueError("Corporate-action gate missing ticker")
    gate["ticker"] = gate["ticker"].astype(str).str.strip().str.upper()
    if len(gate) != EXPECTED_HOSE or gate["ticker"].nunique() != EXPECTED_HOSE or set(gate["ticker"]) != set(tickers):
        raise ValueError("Corporate-action gate must contain exactly the canonical 405 HOSE tickers")
    keep = [
        "ticker",
        "corporate_action_source_ready_v2",
        "corporate_action_source_coverage_ratio_v2",
        "corporate_action_pagination_complete_v2",
        "corporate_action_event_count_window_v2",
        "sensitive_event_count_window_v2",
        "near_sensitive_event_count_v2",
        "upcoming_sensitive_event_count_30d_v2",
        "next_sensitive_record_date_v2",
        "next_sensitive_event_type_v2",
        "next_sensitive_event_title_v2",
        "days_to_next_sensitive_event_v2",
        "corporate_action_gate_v2",
        "corporate_action_action_allowed_v2",
        "corporate_action_review_required_v2",
        "price_adjustment_reconciliation_required_v2",
    ]
    return gate[[c for c in keep if c in gate.columns]].copy()


def build(args) -> None:
    unified = pd.read_csv(args.unified_v6)
    catalyst = pd.read_csv(args.catalyst_v2)
    sla = _read_optional_json(args.sla)
    authority = _read_optional_json(args.authoritative_ca_coverage)
    as_of = pd.Timestamp(args.as_of)

    for frame_name, frame in {"unified_v6": unified, "catalyst": catalyst}.items():
        if "ticker" not in frame.columns:
            raise ValueError(f"{frame_name} missing ticker")
        frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    if len(unified) != EXPECTED_HOSE or unified["ticker"].nunique() != EXPECTED_HOSE:
        raise ValueError("Unified V6 must contain exactly 405 unique HOSE tickers")
    if len(catalyst) != EXPECTED_HOSE or catalyst["ticker"].nunique() != EXPECTED_HOSE:
        raise ValueError("Catalyst layer must cover exactly 405 unique HOSE tickers")

    tickers = unified["ticker"].tolist()
    ca_context = _capital_action_context(args.news_ca_candidates, tickers, as_of)
    ca_gate = _corporate_action_gate(args.corporate_action_gate, tickers)
    catalyst_keep = [
        "ticker",
        "items_90d",
        "items_30d",
        "catalyst_confidence_v2",
        "catalyst_data_ready_v2",
        "catalyst_score_v2",
        "top_catalyst_category_v2",
        "latest_catalyst_time_v2",
        "latest_catalyst_title_v2",
        "catalyst_alpha_weight_allowed_v2",
        "official_items_90d_v3",
        "official_items_30d_v3",
        "recall_only_items_90d_v3",
        "latest_official_catalyst_time_v3",
        "latest_official_catalyst_title_v3",
        "catalyst_confidence_v3",
        "catalyst_official_verified_v3",
        "catalyst_verification_state_v3",
        "official_hose_source_ready_v3",
        "catalyst_alpha_weight_allowed_v3",
    ]
    catalyst_keep = [c for c in catalyst_keep if c in catalyst.columns]
    out = (
        unified.merge(catalyst[catalyst_keep], on="ticker", how="left")
        .merge(ca_context, on="ticker", how="left")
        .merge(ca_gate, on="ticker", how="left")
    )

    sla_ready = bool(sla.get("internal_scan_ready") is True)
    authority_ratio = authority.get("source_coverage_ratio", authority.get("coverage_ratio", 0))
    try:
        authority_ratio = float(authority_ratio or 0)
    except Exception:
        authority_ratio = 0.0
    authority_pagination_complete = bool(
        authority.get("pagination_complete") is True
        and int(authority.get("days_pagination_incomplete") or 0) == 0
    )
    authoritative_ready = bool(authority.get("source_ready") is True and authority_ratio >= 0.98 and authority_pagination_complete)

    out["radar_score_v7"] = pd.to_numeric(out["radar_score_v6"], errors="coerce")
    out["catalyst_alpha_weight_v7"] = 0.0
    out["institutional_alpha_weight_v7"] = 0.0
    out["scan_sla_ready_v7"] = sla_ready
    out["authoritative_corporate_action_source_ready_v7"] = authoritative_ready
    out["authoritative_corporate_action_source_coverage_v7"] = authority_ratio
    out["authoritative_corporate_action_pagination_complete_v7"] = authority_pagination_complete
    out["decision_candidate_v7"] = _bool_series(out["private_action_candidate_v6"])
    out["operational_research_ready_v7"] = _bool_series(out["operational_research_ready_v6"])
    out["news_derived_capital_action_review_required_v7"] = _bool_series(out["news_derived_capital_action_review_required_v7"])
    out["corporate_action_source_ready_v2"] = _bool_series(out.get("corporate_action_source_ready_v2", pd.Series(False, index=out.index)))
    out["corporate_action_pagination_complete_v2"] = _bool_series(out.get("corporate_action_pagination_complete_v2", pd.Series(False, index=out.index)))
    out["corporate_action_action_allowed_v2"] = _bool_series(out.get("corporate_action_action_allowed_v2", pd.Series(False, index=out.index)))
    out["corporate_action_gate_v2"] = out.get("corporate_action_gate_v2", pd.Series("BLOCK_SOURCE_COVERAGE", index=out.index)).fillna("BLOCK_SOURCE_COVERAGE").astype(str)
    out["catalyst_official_verified_v3"] = _bool_series(out.get("catalyst_official_verified_v3", pd.Series(False, index=out.index)))
    out["official_hose_source_ready_v3"] = _bool_series(out.get("official_hose_source_ready_v3", pd.Series(False, index=out.index)))
    out["catalyst_alpha_weight_allowed_v3"] = _bool_series(out.get("catalyst_alpha_weight_allowed_v3", pd.Series(False, index=out.index)))
    out["corporate_action_execution_clear_v7"] = (
        out["authoritative_corporate_action_source_ready_v7"]
        & out["corporate_action_source_ready_v2"]
        & out["corporate_action_pagination_complete_v2"]
        & out["corporate_action_action_allowed_v2"]
        & out["corporate_action_gate_v2"].eq("PASS_NO_NEAR_SENSITIVE_EVENT")
    )

    # Official HOSE catalyst metadata improves provenance/context only. It never enables alpha or action by itself.
    # Execution readiness remains governed by the existing decision/data/SLA/corporate-action gates.
    out["execution_ready_internal_v7"] = (
        out["decision_candidate_v7"]
        & out["operational_research_ready_v7"]
        & out["scan_sla_ready_v7"]
        & out["corporate_action_execution_clear_v7"]
        & ~out["news_derived_capital_action_review_required_v7"]
    )
    out["public_action_allowed_v7"] = False

    statuses = []
    blockers = []
    for _, row in out.iterrows():
        reasons: list[str] = []
        decision_candidate = bool(row["decision_candidate_v7"])
        ca_gate_state = str(row.get("corporate_action_gate_v2") or "BLOCK_SOURCE_COVERAGE")
        if not bool(row["operational_research_ready_v7"]):
            reasons.append("RESEARCH_OR_DATA_GATE_NOT_READY")
        if decision_candidate and not sla_ready:
            reasons.append("SCAN_SLA_NOT_READY")
        if decision_candidate and not authoritative_ready:
            reasons.append("AUTHORITATIVE_CORPORATE_ACTION_SOURCE_UNAVAILABLE")
        if decision_candidate and authoritative_ready and not bool(row["corporate_action_execution_clear_v7"]):
            reasons.append(f"CORPORATE_ACTION_GATE_{ca_gate_state}")
        if decision_candidate and bool(row["news_derived_capital_action_review_required_v7"]):
            reasons.append("RECENT_NEWS_DERIVED_CAPITAL_ACTION_REQUIRES_VERIFICATION")
        if not decision_candidate:
            existing = str(row.get("decision_block_reasons_v5") or "").strip()
            if existing and existing.lower() != "nan":
                reasons.append(existing)

        if bool(row["execution_ready_internal_v7"]):
            status = "PRIVATE_EXECUTION_READY_PENDING_PUBLICATION_GATE"
        elif decision_candidate and not authoritative_ready:
            status = "DECISION_CANDIDATE_PENDING_AUTHORITATIVE_EVENT_VERIFICATION"
        elif decision_candidate and not bool(row["corporate_action_execution_clear_v7"]):
            status = "DECISION_CANDIDATE_BLOCKED_CORPORATE_ACTION_GATE"
        elif decision_candidate and bool(row["news_derived_capital_action_review_required_v7"]):
            status = "DECISION_CANDIDATE_PENDING_EVENT_REVIEW"
        elif decision_candidate and not sla_ready:
            status = "DECISION_CANDIDATE_BLOCKED_SCAN_SLA"
        else:
            status = str(row.get("radar_status_v6") or "WATCH")
        statuses.append(status)
        blockers.append("|".join(dict.fromkeys(reasons)) if reasons else "PASS_PRIVATE_V7_GATES")

    out["radar_status_v7"] = statuses
    out["execution_block_reasons_v7"] = blockers
    out["public_gate_v7"] = "BLOCKED_PENDING_DATA_RIGHTS_COMPLIANCE_ACTIVE_PRODUCTION_MANIFEST"

    out = out.sort_values(
        ["execution_ready_internal_v7", "decision_candidate_v7", "operational_research_ready_v7", "radar_score_v7"],
        ascending=[False, False, False, False],
    )
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.output, index=False, encoding="utf-8-sig")

    publication_blockers = ["DATA_RIGHTS", "COMPLIANCE", "ACTIVE_PRODUCTION_MANIFEST"]
    if not authoritative_ready:
        publication_blockers.append("AUTHORITATIVE_CURRENT_CORPORATE_ACTIONS")

    official_source_ready_count = int(out["official_hose_source_ready_v3"].sum())
    official_verified_count = int(out["catalyst_official_verified_v3"].sum())
    official_items_90d = int(pd.to_numeric(out.get("official_items_90d_v3", pd.Series(0, index=out.index)), errors="coerce").fillna(0).sum())

    manifest = {
        "schema_version": "STOCKRADAR_UNIFIED_V7",
        "as_of": args.as_of,
        "canonical_hose": EXPECTED_HOSE,
        "scan_sla_ready": sla_ready,
        "authoritative_corporate_action_source_ready": authoritative_ready,
        "authoritative_corporate_action_source_coverage": authority_ratio,
        "authoritative_corporate_action_pagination_complete": authority_pagination_complete,
        "corporate_action_gate_counts": out["corporate_action_gate_v2"].value_counts().to_dict(),
        "corporate_action_execution_clear": int(out["corporate_action_execution_clear_v7"].sum()),
        "operational_research_ready": int(out["operational_research_ready_v7"].sum()),
        "decision_candidates": int(out["decision_candidate_v7"].sum()),
        "execution_ready_internal": int(out["execution_ready_internal_v7"].sum()),
        "news_derived_capital_action_review_required": int(out["news_derived_capital_action_review_required_v7"].sum()),
        "catalyst_data_ready": int(_bool_series(out.get("catalyst_data_ready_v2", pd.Series(False, index=out.index))).sum()),
        "official_hose_catalyst_source_ready": bool(official_source_ready_count == EXPECTED_HOSE),
        "official_hose_catalyst_verified_tickers_90d": official_verified_count,
        "official_hose_catalyst_items_90d": official_items_90d,
        "radar_status_counts": out["radar_status_v7"].value_counts().to_dict(),
        "catalyst_alpha_weight": 0,
        "institutional_alpha_weight": 0,
        "corporate_action_policy": "AUTHORITATIVE_TICKER_GATE_NOT_ALPHA; TICKER_GATE_MUST_PASS; NEWS_DERIVED_EVENTS_ONLY_ADD_REVIEW_BLOCKERS",
        "catalyst_policy": "KBS_RECALL_ONLY; HOSE_OFFICIAL_VERIFICATION_CONTEXT; OFFICIAL_EVIDENCE_DOES_NOT_ENABLE_ALPHA",
        "public_action_allowed": False,
        "publication_blockers": publication_blockers,
        "note": "V7 separates research ranking, private decision candidates, ticker-level corporate-action execution readiness, official catalyst provenance, and public publication. Missing/incomplete authoritative evidence can never be interpreted as no event.",
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--unified-v6", required=True)
    parser.add_argument("--catalyst-v2", required=True)
    parser.add_argument("--news-ca-candidates", required=True)
    parser.add_argument("--sla", required=True)
    parser.add_argument("--authoritative-ca-coverage")
    parser.add_argument("--corporate-action-gate")
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
