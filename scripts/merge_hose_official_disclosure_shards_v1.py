#!/usr/bin/env python3
from __future__ import annotations

import argparse
from datetime import datetime, timezone, timedelta, date
import json
from pathlib import Path

import pandas as pd

EXPECTED_HOSE = 405


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--universe', required=True)
    p.add_argument('--as-of', required=True)
    p.add_argument('--lookback-days', type=int, default=120)
    p.add_argument('--output-dir', required=True)
    args = p.parse_args()

    universe = pd.read_csv(args.universe)
    tickers = sorted(set(universe['ticker'].astype(str).str.strip().str.upper()))
    if len(tickers) != EXPECTED_HOSE:
        raise SystemExit(f'canonical HOSE must contain {EXPECTED_HOSE}, got {len(tickers)}')

    root = Path(args.root)
    coverage_files = sorted(root.rglob('coverage.csv'))
    history_files = sorted(root.rglob('history.csv'))
    manifest_files = sorted(root.rglob('manifest.json'))
    if not coverage_files or not manifest_files:
        raise SystemExit('no shard artifacts found')

    coverage = pd.concat([pd.read_csv(x) for x in coverage_files], ignore_index=True, sort=False)
    coverage['ticker'] = coverage['ticker'].astype(str).str.strip().str.upper()
    coverage = coverage.drop_duplicates(subset=['ticker'], keep='last').sort_values('ticker')

    histories = []
    for x in history_files:
        df = pd.read_csv(x)
        if not df.empty:
            histories.append(df)
    history = pd.concat(histories, ignore_index=True, sort=False) if histories else pd.DataFrame()
    if history.empty:
        history = pd.DataFrame(columns=['ticker','security_id','news_id','title','category','updated_at','source','source_url','attachment_count','attachment_urls'])
    else:
        history['ticker'] = history['ticker'].astype(str).str.strip().str.upper()
        history = history.drop_duplicates(subset=['ticker','news_id','title']).sort_values(['updated_at','ticker'], ascending=[False, True])

    manifests = [json.loads(x.read_text(encoding='utf-8')) for x in manifest_files]
    shard_indices = sorted(set(int(x.get('shard_index')) for x in manifests if x.get('shard_index') is not None))
    shard_counts = set(int(x.get('shard_count')) for x in manifests if x.get('shard_count') is not None)

    query_ok = int(coverage.get('query_ok', pd.Series(False, index=coverage.index)).fillna(False).astype(bool).sum())
    ratio = query_ok / EXPECTED_HOSE
    dt = pd.to_datetime(history['updated_at'], errors='coerce', utc=True) if not history.empty else pd.Series(dtype='datetime64[ns, UTC]')
    latest = dt.max().isoformat() if len(dt) and dt.notna().any() else None
    as_of = date.fromisoformat(args.as_of)
    cutoff30 = pd.Timestamp(as_of - timedelta(days=30), tz='UTC')
    tickers30 = int(history.loc[dt >= cutoff30, 'ticker'].nunique()) if len(dt) else 0

    source_ready = bool(
        len(coverage) == EXPECTED_HOSE
        and coverage['ticker'].nunique() == EXPECTED_HOSE
        and ratio >= 0.98
        and len(history) > 0
        and latest is not None
        and len(shard_counts) == 1
        and shard_indices == list(range(next(iter(shard_counts))))
    )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    coverage.to_csv(out / 'hose_official_disclosures_coverage_405.csv', index=False, encoding='utf-8-sig')
    history.to_csv(out / 'hose_official_disclosures_history.csv', index=False, encoding='utf-8-sig')
    manifest = {
        'schema_version': 'STOCKRADAR_HOSE_OFFICIAL_DISCLOSURES_DEPTH_V1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'as_of': as_of.isoformat(),
        'window_start': (as_of - timedelta(days=max(30, min(args.lookback_days, 370)))).isoformat(),
        'window_end': as_of.isoformat(),
        'canonical_hose': EXPECTED_HOSE,
        'ticker_queries_ok': query_ok,
        'ticker_query_coverage_ratio': ratio,
        'row_count': int(len(history)),
        'tickers_with_rows': int(history['ticker'].nunique()) if not history.empty else 0,
        'tickers_with_rows_30d': tickers30,
        'latest_updated_at': latest,
        'shards_seen': shard_indices,
        'source_ready_internal': source_ready,
        'source': 'HOSE_OFFICIAL_API_SHARDED',
        'catalyst_alpha_weight_allowed': False,
        'publication_allowed': False,
    }
    (out / 'hose_official_disclosures_manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False))
    if not source_ready:
        raise SystemExit('merged HOSE official disclosure shards are not source-ready')


if __name__ == '__main__':
    main()
