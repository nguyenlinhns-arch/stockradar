#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

import pandas as pd

import acquire_hose_official_disclosures_v1 as base


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument('--universe', required=True)
    p.add_argument('--as-of', required=True)
    p.add_argument('--lookback-days', type=int, default=120)
    p.add_argument('--shard-index', type=int, required=True)
    p.add_argument('--shard-count', type=int, required=True)
    p.add_argument('--workers', type=int, default=8)
    p.add_argument('--output-dir', required=True)
    args = p.parse_args()

    universe = pd.read_csv(args.universe)
    if 'ticker' not in universe.columns:
        raise SystemExit('universe missing ticker')
    all_tickers = sorted(set(universe['ticker'].astype(str).str.strip().str.upper()))
    if len(all_tickers) != base.EXPECTED_HOSE:
        raise SystemExit(f'canonical HOSE must contain {base.EXPECTED_HOSE}, got {len(all_tickers)}')
    if args.shard_count < 1 or not (0 <= args.shard_index < args.shard_count):
        raise SystemExit('invalid shard index/count')

    tickers = [t for i, t in enumerate(all_tickers) if i % args.shard_count == args.shard_index]
    as_of = date.fromisoformat(args.as_of)
    lookback = max(30, min(int(args.lookback_days), 370))
    start = as_of - timedelta(days=lookback)
    workers = max(1, min(int(args.workers), 12))

    rows: list[dict] = []
    status_rows: list[dict] = []
    with cf.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(base.fetch_ticker, ticker, start, as_of, 0) for ticker in tickers]
        for future in cf.as_completed(futures):
            ticker, sid, ticker_rows, error = future.result()
            status_rows.append({
                'ticker': ticker,
                'security_id': sid,
                'query_ok': error is None,
                'row_count': len(ticker_rows),
                'error': error,
                'shard_index': args.shard_index,
            })
            if error is None:
                rows.extend(ticker_rows)

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    status = pd.DataFrame(status_rows).sort_values('ticker')
    status.to_csv(out / 'coverage.csv', index=False, encoding='utf-8-sig')
    history = pd.DataFrame(rows)
    if history.empty:
        history = pd.DataFrame(columns=['ticker','security_id','news_id','title','category','updated_at','source','source_url','attachment_count','attachment_urls'])
    else:
        history = history.drop_duplicates(subset=['ticker','news_id','title']).sort_values(['updated_at','ticker'], ascending=[False, True])
    history.to_csv(out / 'history.csv', index=False, encoding='utf-8-sig')

    manifest = {
        'schema_version': 'STOCKRADAR_HOSE_OFFICIAL_DISCLOSURES_SHARD_V1',
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'as_of': as_of.isoformat(),
        'window_start': start.isoformat(),
        'window_end': as_of.isoformat(),
        'shard_index': args.shard_index,
        'shard_count': args.shard_count,
        'ticker_count': len(tickers),
        'query_ok': int(status['query_ok'].fillna(False).astype(bool).sum()),
        'row_count': int(len(history)),
        'catalyst_alpha_weight_allowed': False,
        'publication_allowed': False,
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(manifest, ensure_ascii=False))


if __name__ == '__main__':
    main()
