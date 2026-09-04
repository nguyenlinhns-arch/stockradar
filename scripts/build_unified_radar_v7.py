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


def build(args) -> None:
    unified = pd.read_csv(args.unified_v6)
    catalyst = pd.read_csv(args.catalyst_v2)
    sla = _read_optional_json(args.sla)
    authority = _read_optional_json(args.authoritative_ca_coverage)
    as_of = pd.Timestamp(args.as_of)

    for frame_name, frame in {"unified_v6": unified, "catalyst_v2": catalyst}.items():
        if "ticker" not in frame.columns:
            raise ValueError(f"{frame_name} missing ticker")
        frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()
    if len(unified) != EXPECTED_HOSE or unified["ticker"].nunique() != EXPECTED_HOSE:
        raise ValueError("Unified V6 must contain exactly 405 unique HOSE tickers")
    if catalyst["ticker"].nunique() != EXPECTED_HOSE:
        raise ValueError("Catalyst V2 must cover exactly 405 HOSE tickers")

    tickers = unified["ticker"].tolist()
    ca_context = _capital_action_context(args.news_ca_candidates, tickers, as_of)
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
    ]
    catalyst_keep = [c for c in catalyst_keep if c in catalyst.columns]
    out = unified.merge(catalyst[catalyst_keep], on="ticker", how="left").merge(ca_context, on="ticker", how="left")

    sla_ready = bool(sla.get("internal_scan_ready") is True)
    authority_ratio = authority.get("source_coverage_ratio", authority.get("coverage_ratio", 0))
    try:
        authority_ratio = float(authority_ratio or 0)
    except Exception:
        authority_ratio = 0.0
    authoritative_ready = bool(authority.get("source_ready") is True and authority_ratio >= 0.98)

    out["radar_score_v7"] = pd.to_numeric(out["radar_score_v6"], errors="coerce")
    out["catalyst_alpha_weight_v7"] = 0.0
    out["institutional_alpha_weight_v7"] = 0.0
    out["scan_sla_ready_v7"] = sla_ready
    out["authoritative_corporate_action_source_ready_v7"] = authoritative_ready
    out["authoritative_corporate_action_source_coverage_v7"] = authority_ratio
    out["decision_candidate_v7"] = _bool_series(out["private_action_candidate_v6"])
    out["operational_research_ready_v7"] = _bool_series(out["operational_research_ready_v6"])
    out["news_derived_capital_action_review_required_v7"] = _bool_series(out["news_derived_capital_action_review_required_v7"])

    # An execution-ready action requires authoritative current corporate-action coverage.
    # News-derived candidates can only add a review blocker; they can never unlock action.
    out["execution_ready_internal_v7"] = (
        out["decision_candidate_v7"]
        & out["operational_research_ready_v7"]
        & out["scan_sla_ready_v7"]
        & out["authoritative_corporate_action_source_ready_v7"]
        & ~out["news_derived_capital_action_review_required_v7"]
    )
    out["public_action_allowed_v7"] = False

    statuses = []
    blockers = []
    for _, row in out.iterrows():
        reasons: list[str] = []
        decision_candidate = bool(row["decision_candidate_v7"])
        if not bool(row["operational_research_ready_v7"]):
            reasons.append("RESEARCH_OR_DATA_GATE_NOT_READY")
        if decision_candidate and not sla_ready:
            reasons.append("SCAN_SLA_NOT_READY")
        if decision_candidate and not authoritative_ready:
            reasons.append("AUTHORITATIVE_CORPORATE_ACTION_SOURCE_UNAVAILABLE")
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

    manifest = {
        "schema_version": "STOCKRADAR_UNIFIED_V7",
        "as_of": args.as_of,
        "canonical_hose": EXPECTED_HOSE,
        "scan_sla_ready": sla_ready,
        "authoritative_corporate_action_source_ready": authoritative_ready,
        "authoritative_corporate_action_source_coverage": authority_ratio,
        "operational_research_ready": int(out["operational_research_ready_v7"].sum()),
        "decision_candidates": int(out["decision_candidate_v7"].sum()),
        "execution_ready_internal": int(out["execution_ready_internal_v7"].sum()),
        "news_derived_capital_action_review_required": int(out["news_derived_capital_action_review_required_v7"].sum()),
        "catalyst_data_ready": int(_bool_series(out.get("catalyst_data_ready_v2", pd.Series(False, index=out.index))).sum()),
        "radar_status_counts": out["radar_status_v7"].value_counts().to_dict(),
        "catalyst_alpha_weight": 0,
        "institutional_alpha_weight": 0,
        "corporate_action_policy": "AUTHORITATIVE_GATE_NOT_ALPHA; NEWS_DERIVED_EVENTS_ONLY_ADD_REVIEW_BLOCKERS",
        "public_action_allowed": False,
        "publication_blockers": [
            "DATA_RIGHTS",
            "COMPLIANCE",
            "ACTIVE_PRODUCTION_MANIFEST",
            "AUTHORITATIVE_CURRENT_CORPORATE_ACTIONS",
        ],
        "note": "V7 separates research ranking, private decision candidates, execution readiness, and public publication. Missing authoritative events can never be interpreted as no event.",
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
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()
