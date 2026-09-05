#!/usr/bin/env python3
"""Build private indicators/history from one validated HOSE source run."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from stockradar.data_layer import build_data_layer, read_frame


def main():
    p = argparse.ArgumentParser()
    for key in ('security-master', 'history', 'technical', 'fundamental', 'valuation', 'output'):
        p.add_argument('--' + key, required=True)
    args = p.parse_args()
    master = read_frame(Path(args.security_master))
    if master.ticker.duplicated().any() or not master.exchange.eq('HOSE').all():
        raise ValueError('INVALID_SECURITY_MASTER')
    frames = {key: read_frame(Path(getattr(args, key))) for key in ('history', 'technical', 'fundamental', 'valuation')}
    history = frames['history']
    date_column = 'timestamp' if 'timestamp' in history else 'date'
    as_of = str(history[date_column].max())[:10]
    sources = [{'role': key, 'file': Path(getattr(args, key)).name,
                'sha256': hashlib.sha256(Path(getattr(args, key)).read_bytes()).hexdigest()}
               for key in frames]
    _, qa = build_data_layer(universe=set(master.ticker), **frames, as_of=as_of,
                            sources=sources, output=Path(args.output))
    if qa['missing_tickers']:
        raise ValueError('INCOMPLETE_HOSE_HISTORY')
    print(json.dumps(qa))


if __name__ == '__main__':
    main()
