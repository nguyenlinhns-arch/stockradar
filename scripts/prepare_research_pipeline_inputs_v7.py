from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_HOSE = 405
FINANCIAL_SECTOR_TYPES = {
    "Ngân hàng": "Ngân hàng",
    "Chứng khoán": "Công ty chứng khoán",
    "Bảo hiểm": "Công ty bảo hiểm",
}


def _numeric(value):
    return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def _parse_payload(value) -> dict:
    try:
        obj = json.loads(value) if isinstance(value, str) else value
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}


def _items(value) -> list[dict]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _sum_pct(items: list[dict], keywords: tuple[str, ...]) -> float:
    values: list[float] = []
    for item in items:
        name = str(item.get("NM") or "").casefold()
        if any(keyword in name for keyword in keywords):
            value = _numeric(item.get("OR"))
            if pd.notna(value):
                values.append(float(value))
    return float(sum(values)) if values else np.nan


def _latest_ownership_date(ownership: list[dict], shareholders: list[dict]):
    dates = []
    for item in ownership + shareholders:
        dt = pd.to_datetime(item.get("D"), errors="coerce")
        if pd.notna(dt):
            dates.append(dt)
    return max(dates).date().isoformat() if dates else None


def _normalize_profile_rows(profile_raw: pd.DataFrame, security: pd.DataFrame, snapshot: pd.DataFrame) -> pd.DataFrame:
    sector_map = security.set_index("ticker")["sector"].to_dict()
    snapshot_shares = snapshot.set_index("ticker")["outstanding_shares"].to_dict() if "outstanding_shares" in snapshot.columns else {}
    rows = []
    for _, record in profile_raw.iterrows():
        ticker = str(record.get("ticker") or "").strip().upper()
        payload = _parse_payload(record.get("payload"))
        ownership = _items(payload.get("Ownership"))
        shareholders = _items(payload.get("Shareholders"))
        sector = sector_map.get(ticker)
        raw_type = str(payload.get("TY") or "").strip() or None
        company_type = FINANCIAL_SECTOR_TYPES.get(str(sector), raw_type or "Công ty")

        outstanding = _numeric(payload.get("KLCPLH"))
        if pd.isna(outstanding) or outstanding <= 0:
            outstanding = _numeric(snapshot_shares.get(ticker))

        shareholder_pcts = [_numeric(item.get("OR")) for item in shareholders]
        shareholder_pcts = [float(v) for v in shareholder_pcts if pd.notna(v) and v >= 0]
        major_reported = min(100.0, sum(shareholder_pcts)) if shareholder_pcts else np.nan
        top_shareholder = max(shareholder_pcts) if shareholder_pcts else np.nan

        institutional = _sum_pct(
            ownership,
            ("tổ chức", "to chuc", "institution", "quỹ", "fund"),
        )
        foreign = _sum_pct(
            ownership,
            ("nước ngoài", "nuoc ngoai", "foreign"),
        )

        rows.append(
            {
                "ticker": ticker,
                "company_type": company_type,
                "outstanding_shares_profile": outstanding,
                "audit_firm": str(payload.get("KT") or "").strip() or None,
                "institutional_ownership_profile_pct": institutional,
                "foreign_ownership_profile_pct": foreign,
                "major_shareholders_reported_pct": major_reported,
                "top_shareholder_pct": top_shareholder,
                "ownership_asof": _latest_ownership_date(ownership, shareholders),
                "profile_source": str(record.get("source") or ""),
            }
        )
    return pd.DataFrame(rows)


def build(args) -> None:
    security = pd.read_csv(args.security_master)
    technical = pd.read_csv(args.technical)
    fundamental = pd.read_csv(args.fundamental)
    scanner = pd.read_csv(args.scanner)
    profile_raw = pd.read_csv(args.profile_raw)
    snapshot = pd.read_csv(args.snapshot)

    for name, frame in {
        "security_master": security,
        "technical": technical,
        "fundamental": fundamental,
        "scanner": scanner,
        "profile_raw": profile_raw,
        "snapshot": snapshot,
    }.items():
        if "ticker" not in frame.columns:
            raise ValueError(f"{name} missing ticker")
        frame["ticker"] = frame["ticker"].astype(str).str.strip().str.upper()

    if len(security) != EXPECTED_HOSE or security["ticker"].nunique() != EXPECTED_HOSE:
        raise ValueError("security master must be exactly 405 unique HOSE tickers")
    canonical = set(security["ticker"])
    coverage = {}
    for name, frame in {
        "technical": technical,
        "fundamental": fundamental,
        "scanner": scanner,
        "profile_raw": profile_raw,
        "snapshot": snapshot,
    }.items():
        covered = set(frame["ticker"])
        coverage[name] = len(canonical & covered)
        if covered != canonical:
            missing = sorted(canonical - covered)[:20]
            extra = sorted(covered - canonical)[:20]
            raise ValueError(f"{name} universe mismatch; missing={missing}, extra={extra}")

    scanner_compat = scanner.copy()
    aliases = {
        "technical_score": "technical_score_v2",
        "stockradar_score": "stockradar_score_v2",
        "candidate_setup": "setup_internal",
        "action_candidate": "action_candidate_internal",
    }
    for target, source in aliases.items():
        if source not in scanner_compat.columns:
            raise ValueError(f"scanner missing required V2 field {source}")
        scanner_compat[target] = scanner_compat[source]

    profile = _normalize_profile_rows(profile_raw, security, snapshot)
    if len(profile) != EXPECTED_HOSE or profile["ticker"].nunique() != EXPECTED_HOSE:
        raise ValueError("normalized profile coverage !=405")

    status = security[["ticker", "name", "sector"]].rename(columns={"name": "company_name_vi"})
    status = status.merge(
        scanner_compat[
            [
                "ticker",
                "daily_bar_count",
                "technical_history_eligible",
                "fundamental_feature_status",
            ]
        ],
        on="ticker",
        how="left",
    )
    status["technical_data_ready"] = (
        status["technical_history_eligible"].fillna(False).astype(bool)
        & (pd.to_numeric(status["daily_bar_count"], errors="coerce").fillna(0) >= 210)
    )
    status["fundamental_data_ready"] = status["fundamental_feature_status"].astype(str).str.upper().eq("OK")

    market_context = {
        "universe_count": EXPECTED_HOSE,
        "advancers": int((pd.to_numeric(scanner_compat["pct_change"], errors="coerce") > 0).sum()),
        "above_ma50": int(
            (
                pd.to_numeric(scanner_compat["price"], errors="coerce")
                > pd.to_numeric(scanner_compat["ma50"], errors="coerce")
            ).sum()
        ),
        "above_ma200": int(
            (
                pd.to_numeric(scanner_compat["price"], errors="coerce")
                > pd.to_numeric(scanner_compat["ma200"], errors="coerce")
            ).sum()
        ),
        "stage2_count": int(scanner_compat["stage"].astype(str).eq("STAGE_2").sum()),
        "full_scan_eligible": int(scanner_compat["full_scan_eligible"].fillna(False).astype(bool).sum()),
        "liquid_vol20_ge_500k": int(scanner_compat["liquidity_pass_500k"].fillna(False).astype(bool).sum()),
    }

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    scanner_compat.to_csv(out_dir / "scanner_compat_v7.csv", index=False, encoding="utf-8-sig")
    profile.to_csv(out_dir / "profile_normalized_v7.csv", index=False, encoding="utf-8-sig")
    status.to_csv(out_dir / "status_normalized_v7.csv", index=False, encoding="utf-8-sig")
    (out_dir / "market_context_v7.json").write_text(
        json.dumps(market_context, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "STOCKRADAR_RESEARCH_INPUTS_V7",
        "canonical_hose": EXPECTED_HOSE,
        "coverage": coverage,
        "technical_ready_210d": int(status["technical_data_ready"].sum()),
        "fundamental_ready": int(status["fundamental_data_ready"].sum()),
        "profile_outstanding_shares_ready": int(pd.to_numeric(profile["outstanding_shares_profile"], errors="coerce").gt(0).sum()),
        "ownership_asof_ready": int(profile["ownership_asof"].notna().sum()),
        "market_context": market_context,
        "publication_allowed": False,
        "note": "Compatibility/normalization only. No public rights are created and missing ownership evidence is never converted into negative alpha.",
    }
    (out_dir / "research_inputs_v7_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--security-master", required=True)
    parser.add_argument("--technical", required=True)
    parser.add_argument("--fundamental", required=True)
    parser.add_argument("--scanner", required=True)
    parser.add_argument("--profile-raw", required=True)
    parser.add_argument("--snapshot", required=True)
    parser.add_argument("--output-dir", required=True)
    build(parser.parse_args())


if __name__ == "__main__":
    main()

# Regression trigger after Domain V4 canonical valuation-column repair.
