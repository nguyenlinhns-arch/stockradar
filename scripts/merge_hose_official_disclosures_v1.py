#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import pandas as pd

EXPECTED_HOSE = 405


def read_csv(path: str | None) -> pd.DataFrame:
    if not path:
        return pd.DataFrame()
    p = Path(path)
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()


def read_json(path: str | None) -> dict:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def norm_title(value: object) -> str:
    text = str(value or "").casefold()
    text = re.sub(r"\s+", " ", text).strip()
    return re.sub(r"[^0-9a-zà-ỹ]+", " ", text).strip()


def normalize(frame: pd.DataFrame, source_kind: str, priority: int) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["ticker", "title", "updated_at", "category", "source_kind", "source_priority", "source_url", "event_id"])
    out = pd.DataFrame()
    out["ticker"] = frame.get("ticker", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip().str.upper()
    out["title"] = frame.get("title", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip()
    out["updated_at"] = frame.get("updated_at", pd.Series("", index=frame.index)).fillna("").astype(str)
    out["category"] = frame.get("category", pd.Series("OTHER", index=frame.index)).fillna("OTHER").astype(str).str.strip().str.upper()
    if "link" in frame.columns:
        out["source_url"] = frame["link"].fillna("").astype(str)
    elif "source_url" in frame.columns:
        out["source_url"] = frame["source_url"].fillna("").astype(str)
    else:
        out["source_url"] = ""
    if "news_id" in frame.columns:
        out["event_id"] = frame["news_id"].fillna("").astype(str)
    elif "guid" in frame.columns:
        out["event_id"] = frame["guid"].fillna("").astype(str)
    else:
        out["event_id"] = ""
    out["source_kind"] = source_kind
    out["source_priority"] = priority
    out["title_key"] = out["title"].map(norm_title)
    out["updated_dt"] = pd.to_datetime(out["updated_at"], errors="coerce", utc=True)
    out["event_day"] = out["updated_dt"].dt.strftime("%Y-%m-%d").fillna("")
    out = out[out["ticker"].str.match(r"^[A-Z0-9]{3}$", na=False) & out["title_key"].ne("")].copy()
    return out


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--realtime-history")
    p.add_argument("--realtime-manifest")
    p.add_argument("--deep-history")
    p.add_argument("--deep-manifest")
    p.add_argument("--universe", required=True)
    p.add_argument("--output", required=True)
    p.add_argument("--manifest", required=True)
    args = p.parse_args()

    universe = pd.read_csv(args.universe)
    tickers = sorted(set(universe["ticker"].astype(str).str.strip().str.upper()))
    if len(tickers) != EXPECTED_HOSE:
        raise SystemExit(f"canonical HOSE must be {EXPECTED_HOSE}, got {len(tickers)}")

    realtime = normalize(read_csv(args.realtime_history), "HOSE_OFFICIAL_RSS_REALTIME", 1)
    deep = normalize(read_csv(args.deep_history), "HOSE_OFFICIAL_API_DEPTH", 2)
    merged = pd.concat([realtime, deep], ignore_index=True, sort=False)
    if not merged.empty:
        merged = merged[merged["ticker"].isin(tickers)].copy()
        # Same ticker + normalized title + day is the same official event. Prefer deep API provenance.
        merged = merged.sort_values(["source_priority", "updated_dt"], ascending=[False, False])
        merged = merged.drop_duplicates(subset=["ticker", "title_key", "event_day"], keep="first")
        merged = merged.sort_values(["updated_dt", "ticker"], ascending=[False, True])

    output_cols = ["ticker", "title", "updated_at", "category", "source_kind", "source_url", "event_id"]
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    merged[output_cols].to_csv(args.output, index=False, encoding="utf-8-sig")

    realtime_manifest = read_json(args.realtime_manifest)
    deep_manifest = read_json(args.deep_manifest)
    deep_ready = bool(deep_manifest.get("source_ready_internal") is True)
    realtime_ready = bool(realtime_manifest.get("source_ready_internal") is True)
    dt = pd.to_datetime(merged["updated_at"], errors="coerce", utc=True) if not merged.empty else pd.Series(dtype="datetime64[ns, UTC]")
    latest = dt.max().isoformat() if len(dt) and dt.notna().any() else None
    manifest = {
        "schema_version": "STOCKRADAR_HOSE_OFFICIAL_DISCLOSURES_MERGED_V1",
        "canonical_hose": EXPECTED_HOSE,
        "realtime_source_ready": realtime_ready,
        "deep_source_ready": deep_ready,
        "source_ready_internal": bool(deep_ready and (realtime_ready or len(deep) > 0)),
        "realtime_rows_input": int(len(realtime)),
        "deep_rows_input": int(len(deep)),
        "merged_rows": int(len(merged)),
        "merged_unique_tickers": int(merged["ticker"].nunique()) if not merged.empty else 0,
        "latest_updated_at": latest,
        "dedupe_policy": "ticker + normalized_title + event_day; prefer HOSE API depth over RSS realtime",
        "catalyst_alpha_weight_allowed": False,
        "publication_allowed": False,
    }
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == "__main__":
    main()
