#!/usr/bin/env python3
# One-time migration trigger: 2026-09-04.
from pathlib import Path


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"Expected patch target not found in {path}: {old[:100]!r}")
    text = text.replace(old, new, 1)
    path.write_text(text, encoding="utf-8")


bootstrap = Path("scripts/bootstrap_kbs_hose_data.py")
raw_pipeline = Path("engine/stockradar/raw_pipeline.py")

replace_once(
    bootstrap,
    '''def clean_symbol(value: Any) -> str:
    s = str(value or "").strip().upper()
    return s if len(s) == 3 and s.isascii() and s.isalpha() else ""
''',
    '''def clean_symbol(value: Any) -> str:
    s = str(value or "").strip().upper()
    # HOSE has valid 3-character alphanumeric equity tickers such as C32, HT1, NT2 and PC1.
    return s if len(s) == 3 and s.isascii() and s.isalnum() and any(ch.isalpha() for ch in s) else ""
''',
)

replace_once(
    bootstrap,
    '"FB":"foreign_buy_volume","FR":"foreign_sell_volume","TT":"total_trades",',
    '"FB":"foreign_buy_volume","FR":"foreign_sell_volume","TT":"total_volume",',
)

replace_once(
    bootstrap,
    'current_vol=pd.to_numeric(pd.Series([b.get("match_volume")]),errors="coerce").iloc[0]',
    'current_vol=pd.to_numeric(pd.Series([b.get("total_volume")]),errors="coerce").iloc[0]',
)

replace_once(
    bootstrap,
    '''                pri=[]
                for d in sessions[-21:-1]:
                    dg=ig[ig["session"]==d].copy()
                    if cur_time is not None:
                        dg=dg[dg["timestamp"].dt.time<=cur_time]
                    if not dg.empty: pri.append(float(dg["volume"].sum()))
                if current_cum is not None and pri and statistics.fmean(pri)>0:
                    same_time_ratio=current_cum/statistics.fmean(pri)
                if current_cum is not None and curg.shape[0]>0:
                    # ~52 five-minute bars in continuous trading; projection is diagnostic only.
                    projected_vol=current_cum*52/max(1,curg.shape[0])
''',
    '''                pri=[]
                progress=[]
                daily_by_date={ts.date(): float(v) for ts,v in zip(g["timestamp"],g["volume"]) if pd.notna(ts) and pd.notna(v)}
                for d in sessions[-21:-1]:
                    dg=ig[ig["session"]==d].copy()
                    if cur_time is not None:
                        dg=dg[dg["timestamp"].dt.time<=cur_time]
                    if not dg.empty:
                        cum=float(dg["volume"].sum())
                        pri.append(cum)
                        full=daily_by_date.get(d)
                        if full and full>0:
                            frac=cum/full
                            if 0 < frac <= 1.25:
                                progress.append(frac)
                if current_cum is not None and pri and statistics.fmean(pri)>0:
                    same_time_ratio=current_cum/statistics.fmean(pri)
                if current_cum is not None and progress:
                    # Progress-adjusted projection derived from the historical same-time fraction.
                    frac=float(statistics.median(progress))
                    projected_vol=current_cum/frac if frac>0 else None
''',
)

replace_once(
    bootstrap,
    '''    if len(tickers)<350:
        raise RuntimeError(f"HOSE universe unexpectedly small: {len(tickers)}")
''',
    '''    if len(tickers)<405:
        raise RuntimeError(f"HOSE universe unexpectedly small: {len(tickers)}; expected at least 405")
''',
)

replace_once(
    bootstrap,
    'events=get_json(s,f"/stockinfo/event/{ticker}",{"l":1,"p":1,"s":50})',
    'events=get_json(s,f"/stockinfo/event/{ticker}",{"l":1,"p":1,"s":20})',
)

replace_once(
    bootstrap,
    '''            specs=[("KQKD",2,1),("KQKD",2,2),("KQKD",1,1),("CDKT",1,1),("LCTT",1,1),("CSTC",2,1),("CSTC",1,1)]
''',
    '''            specs=[
                ("KQKD",2,1),("KQKD",2,2),
                ("KQKD",1,1),("KQKD",1,2),
                ("CDKT",1,1),("CDKT",1,2),
                ("LCTT",1,1),("LCTT",1,2),
                ("CSTC",2,1),("CSTC",2,2),
                ("CSTC",1,1),("CSTC",1,2),
            ]
''',
)

replace_once(
    bootstrap,
    '''def run_fundamentals(out: Path) -> None:
    universe,_=fetch_universe(); tickers=[r["ticker"] for r in universe]
    profiles=[]; events=[]; fin_rows=[]; errors=[]
''',
    '''def run_fundamentals(out: Path) -> None:
    universe,_=fetch_universe(); tickers=[r["ticker"] for r in universe]
    if len(tickers)<405:
        raise RuntimeError(f"HOSE universe unexpectedly small: {len(tickers)}; expected at least 405")
    profiles=[]; events=[]; fin_rows=[]; errors=[]
''',
)

replace_once(
    raw_pipeline,
    '''def _ticker(value: object, dataset: str) -> str:
    ticker = str(value or "").strip().upper()
    if len(ticker) != 3 or not ticker.isalpha() or not ticker.isascii():
        raise RawPipelineError(f"invalid ticker in {dataset}: {ticker!r}")
    return ticker
''',
    '''def _ticker(value: object, dataset: str) -> str:
    ticker = str(value or "").strip().upper()
    if (
        len(ticker) != 3
        or not ticker.isascii()
        or not ticker.isalnum()
        or not any(ch.isalpha() for ch in ticker)
    ):
        raise RawPipelineError(f"invalid ticker in {dataset}: {ticker!r}")
    return ticker
''',
)

print("Patched StockRadar for full HOSE alphanumeric ticker coverage and intraday volume progress.")
