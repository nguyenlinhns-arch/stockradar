#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures as cf
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import statistics
import time
from typing import Any

import pandas as pd
import requests

BASE = "https://kbbuddywts.kbsec.com.vn/iis-server/investment"
HEADERS = {
    "Accept": "application/json",
    "Accept-Language": "vi,en;q=0.8",
    "User-Agent": "StockRadar-Internal-Research/1.0",
    "x-lang": "vi",
}
TIMEOUT = 30
MAX_WORKERS = 10
SOURCE_ID = "KBS_PUBLIC_BOOTSTRAP_INTERNAL_ONLY"


def get_json(session: requests.Session, path: str, params: dict[str, Any] | None = None, retries: int = 4) -> Any:
    url = f"{BASE}{path}"
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            time.sleep(min(8, 0.8 * (2 ** attempt)))
    raise RuntimeError(f"GET failed {url}: {last}")


def post_json(session: requests.Session, path: str, payload: dict[str, Any], retries: int = 4) -> Any:
    url = f"{BASE}{path}"
    headers = dict(HEADERS)
    headers["Content-Type"] = "application/json"
    last: Exception | None = None
    for attempt in range(retries):
        try:
            r = session.post(url, json=payload, headers=headers, timeout=TIMEOUT)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            last = exc
            time.sleep(min(8, 0.8 * (2 ** attempt)))
    raise RuntimeError(f"POST failed {url}: {last}")


def clean_symbol(value: Any) -> str:
    s = str(value or "").strip().upper()
    return s if len(s) == 3 and s.isascii() and s.isalpha() else ""


def fetch_universe() -> tuple[list[dict[str, Any]], dict[str, str]]:
    with requests.Session() as s:
        listing = get_json(s, "/stock/search/data")
        industries = get_json(s, "/sector/all")
        sector_by_ticker: dict[str, str] = {}
        for item in industries if isinstance(industries, list) else []:
            code = item.get("code")
            name = str(item.get("name") or item.get("nameEn") or code or "UNCLASSIFIED").strip()
            try:
                payload = get_json(s, "/sector/stock", {"code": code, "l": 1})
            except Exception:
                continue
            stocks = payload.get("stocks", []) if isinstance(payload, dict) else []
            for row in stocks:
                ticker = clean_symbol(row.get("sb") if isinstance(row, dict) else row)
                if ticker:
                    sector_by_ticker[ticker] = name
        rows = []
        for item in listing if isinstance(listing, list) else []:
            ticker = clean_symbol(item.get("symbol"))
            ex = str(item.get("exchange") or "").upper()
            typ = str(item.get("type") or "stock").lower()
            if ticker and ex == "HOSE" and typ in {"stock", "equity", ""}:
                row = dict(item)
                row["ticker"] = ticker
                row["sector"] = sector_by_ticker.get(ticker, "UNCLASSIFIED")
                rows.append(row)
        rows.sort(key=lambda x: x["ticker"])
        return rows, sector_by_ticker


def fmt_date(d: date) -> str:
    return d.strftime("%d-%m-%Y")


def fetch_history(ticker: str, start: date, end: date, interval: str) -> tuple[str, list[dict[str, Any]], str | None]:
    try:
        with requests.Session() as s:
            payload = get_json(s, f"/stocks/{ticker}/data_{interval}", {"sdate": fmt_date(start), "edate": fmt_date(end)})
        key = {"day": "data_day", "5P": "data_5P"}.get(interval)
        if key and isinstance(payload, dict) and isinstance(payload.get(key), list):
            data = payload[key]
        elif isinstance(payload, dict):
            candidates = [v for k, v in payload.items() if isinstance(v, list) and str(k).lower().startswith("data")]
            data = max(candidates, key=len) if candidates else []
        else:
            data = []
        return ticker, data, None
    except Exception as exc:
        return ticker, [], str(exc)


def history_rows(ticker: str, data: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    out = []
    for b in data:
        try:
            out.append({
                "ticker": ticker,
                "timestamp": str(b.get("t") or "").strip(),
                "open": float(b.get("o")),
                "high": float(b.get("h")),
                "low": float(b.get("l")),
                "close": float(b.get("c")),
                "volume": float(b.get("v")),
                "source": source,
            })
        except Exception:
            continue
    return out


def fetch_index_history(symbol: str, start: date, end: date, interval: str) -> list[dict[str, Any]]:
    with requests.Session() as s:
        payload = get_json(s, f"/index/{symbol}/data_{interval}", {"sdate": fmt_date(start), "edate": fmt_date(end)})
    if not isinstance(payload, dict):
        return []
    candidates = [v for k, v in payload.items() if isinstance(v, list) and str(k).lower().startswith("data")]
    data = max(candidates, key=len) if candidates else []
    return history_rows(symbol, data, SOURCE_ID)


def fetch_price_board(tickers: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    errors: list[str] = []
    with requests.Session() as s:
        for i in range(0, len(tickers), 40):
            chunk = tickers[i:i+40]
            try:
                payload = post_json(s, "/stock/iss", {"code": ",".join(chunk)})
                if isinstance(payload, list):
                    rows.extend(payload)
                else:
                    errors.append(f"chunk {i//40}: non-list response")
            except Exception as exc:
                errors.append(f"chunk {i//40}: {exc}")
    return rows, errors


def normalize_board(raw: list[dict[str, Any]]) -> pd.DataFrame:
    mapping = {
        "SB":"ticker","t":"source_time_ms","EX":"exchange","RE":"reference_price","CL":"ceiling_price","FL":"floor_price",
        "CP":"price","CV":"match_volume","OP":"open","HI":"high","LO":"low","AP":"average_price","TV":"total_value",
        "CH":"change","CHP":"pct_change","FB":"foreign_buy_volume","FR":"foreign_sell_volume","TT":"total_trades",
        "LS":"outstanding_shares","TLQ":"listed_shares","FS":"foreign_room","FO":"foreign_ownership","ST":"status","MS":"match_status"
    }
    rows=[]
    for r in raw:
        x={mapping[k]:v for k,v in r.items() if k in mapping}
        t=clean_symbol(x.get("ticker"))
        if t:
            x["ticker"]=t
            x["source"]=SOURCE_ID
            rows.append(x)
    return pd.DataFrame(rows)


def sma(s: pd.Series, n: int) -> float | None:
    s = pd.to_numeric(s, errors="coerce").dropna()
    return float(s.tail(n).mean()) if len(s) >= n else None


def compute_technical(daily: pd.DataFrame, intraday: pd.DataFrame, board: pd.DataFrame) -> pd.DataFrame:
    board_map = board.set_index("ticker").to_dict("index") if not board.empty and "ticker" in board else {}
    rows=[]
    for ticker, g in daily.groupby("ticker"):
        g=g.copy()
        g["timestamp"]=pd.to_datetime(g["timestamp"], errors="coerce")
        g=g.dropna(subset=["timestamp"]).sort_values("timestamp")
        for c in ["open","high","low","close","volume"]:
            g[c]=pd.to_numeric(g[c], errors="coerce")
        g=g.dropna(subset=["close","volume"])
        if g.empty: continue
        close=g["close"]
        volume=g["volume"]
        ma10,ma20,ma50,ma150,ma200=[sma(close,n) for n in [10,20,50,150,200]]
        vol20=sma(volume,20)
        last=float(close.iloc[-1])
        b=board_map.get(ticker,{})
        current_price=pd.to_numeric(pd.Series([b.get("price")]),errors="coerce").iloc[0]
        current_price=float(current_price) if pd.notna(current_price) and current_price>0 else last
        current_vol=pd.to_numeric(pd.Series([b.get("match_volume")]),errors="coerce").iloc[0]
        ig=intraday[intraday["ticker"]==ticker].copy() if not intraday.empty else pd.DataFrame()
        same_time_ratio=None; current_cum=None; projected_vol=None
        if not ig.empty:
            ig["timestamp"]=pd.to_datetime(ig["timestamp"],errors="coerce")
            ig["volume"]=pd.to_numeric(ig["volume"],errors="coerce")
            ig=ig.dropna(subset=["timestamp","volume"]).sort_values("timestamp")
            if not ig.empty:
                ig["session"]=ig["timestamp"].dt.date
                sessions=sorted(ig["session"].unique())
                cur=sessions[-1]
                curg=ig[ig["session"]==cur].copy()
                curg["cumvol"]=curg["volume"].cumsum()
                current_cum=float(curg["cumvol"].iloc[-1]) if not curg.empty else None
                cur_time=curg["timestamp"].iloc[-1].time() if not curg.empty else None
                pri=[]
                for d in sessions[-21:-1]:
                    dg=ig[ig["session"]==d].copy()
                    if cur_time is not None:
                        dg=dg[dg["timestamp"].dt.time<=cur_time]
                    if not dg.empty: pri.append(float(dg["volume"].sum()))
                if current_cum is not None and pri and statistics.fmean(pri)>0:
                    same_time_ratio=current_cum/statistics.fmean(pri)
                if current_cum is not None and curg.shape[0]>0:
                    projected_vol=current_cum*52/max(1,curg.shape[0])
        if current_cum is None and pd.notna(current_vol): current_cum=float(current_vol)
        rvol=(current_cum/vol20) if current_cum is not None and vol20 and vol20>0 else None
        down=g[g["close"].diff()<0].tail(10)
        max_down_vol10=float(down["volume"].max()) if not down.empty else None
        pocket_vol_pass=bool(projected_vol and max_down_vol10 and projected_vol>max_down_vol10)
        pivot20=float(g["high"].iloc[-21:-1].max()) if len(g)>=21 else None
        dist=((current_price/pivot20)-1)*100 if pivot20 else None
        ma200_slope=None
        if len(g)>=220:
            ma200_now=float(close.tail(200).mean()); ma200_prev=float(close.iloc[-220:-20].mean()); ma200_slope=ma200_now-ma200_prev
        stage="UNKNOWN"
        if all(v is not None for v in [ma50,ma150,ma200]):
            if current_price>ma50>ma150>ma200 and (ma200_slope or 0)>=0: stage="STAGE_2"
            elif current_price<ma50<ma150 and current_price<ma200: stage="STAGE_4"
            elif current_price>=ma200 and ma50>=ma150: stage="STAGE_1_TO_2"
            else: stage="STAGE_1_OR_3"
        tenkan=(float(g["high"].tail(9).max())+float(g["low"].tail(9).min()))/2 if len(g)>=9 else None
        kijun=(float(g["high"].tail(26).max())+float(g["low"].tail(26).min()))/2 if len(g)>=26 else None
        span_b=(float(g["high"].tail(52).max())+float(g["low"].tail(52).min()))/2 if len(g)>=52 else None
        span_a=(tenkan+kijun)/2 if tenkan is not None and kijun is not None else None
        ichimoku="ABOVE_KUMO" if span_a is not None and span_b is not None and current_price>max(span_a,span_b) else "BELOW_KUMO" if span_a is not None and span_b is not None and current_price<min(span_a,span_b) else "IN_KUMO"
        bb_width=None; squeeze=False
        if len(close)>=20:
            m=close.tail(20).mean(); sd=close.tail(20).std(ddof=0)
            bb_width=float((4*sd/m)*100) if m else None
            widths=[]
            if len(close)>=120:
                for i in range(20,len(close)+1):
                    w=close.iloc[i-20:i]; mm=w.mean(); ss=w.std(ddof=0)
                    if mm: widths.append((4*ss/mm)*100)
            if bb_width is not None and widths:
                squeeze=bb_width<=pd.Series(widths).quantile(.2)
        vol_dry=bool(vol20 and len(volume)>=5 and volume.tail(5).mean()<0.65*vol20)
        vcp_score=None
        if len(g)>=60:
            ranges=[]
            for n in (60,30,15):
                w=g.tail(n); base=float(w["close"].mean()); ranges.append((float(w["high"].max())-float(w["low"].min()))/base if base else 0)
            vcp_score=max(0.0,min(100.0,100*(1-(ranges[2]/ranges[0] if ranges[0] else 1)))) if ranges[0]>0 else 0
        rows.append({
            "ticker":ticker,"price":current_price,"last_daily_close":last,"ma10":ma10,"ma20":ma20,"ma50":ma50,"ma150":ma150,"ma200":ma200,
            "vol20":vol20,"current_cum_volume":current_cum,"rvol_vs_full_day_vol20":rvol,"same_time_volume_ratio":same_time_ratio,"projected_full_day_volume":projected_vol,
            "max_down_volume_10":max_down_vol10,"pocket_pivot_volume_pass_intraday_projection":pocket_vol_pass,"pivot20":pivot20,"distance_to_pivot_pct":dist,
            "stage":stage,"ma200_slope_20d":ma200_slope,"tenkan":tenkan,"kijun":kijun,"kumo_span_a":span_a,"kumo_span_b":span_b,"ichimoku_state":ichimoku,
            "bollinger_width_pct":bb_width,"bollinger_squeeze":squeeze,"volume_dry_up_5d":vol_dry,"vcp_contraction_score":vcp_score,
            "source":SOURCE_ID,"rights_publication":"BLOCKED_PENDING_TERMS_REVIEW"
        })
    return pd.DataFrame(rows).sort_values("ticker")


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str)+"\n",encoding="utf-8")


def run_market(out: Path) -> None:
    universe, _ = fetch_universe()
    tickers=[r["ticker"] for r in universe]
    if len(tickers)<350:
        raise RuntimeError(f"HOSE universe unexpectedly small: {len(tickers)}")
    sm=pd.DataFrame([{"ticker":r["ticker"],"name":r.get("name") or r.get("nameEn") or r["ticker"],"exchange":"HOSE","sector":r.get("sector") or "UNCLASSIFIED","source":SOURCE_ID} for r in universe])
    sm.to_csv(out/"security_master.csv",index=False,encoding="utf-8-sig")
    write_json(out/"kbs_listing_raw.json",universe)
    end=date.today(); start=end-timedelta(days=365*3+60); intra_start=end-timedelta(days=35)
    daily_rows=[]; intra_rows=[]; errors=[]
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures=[ex.submit(fetch_history,t,start,end,"day") for t in tickers]
        for fut in cf.as_completed(futures):
            ticker,data,err=fut.result(); daily_rows.extend(history_rows(ticker,data,SOURCE_ID))
            if err: errors.append({"ticker":ticker,"dataset":"daily","error":err})
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futures=[ex.submit(fetch_history,t,intra_start,end,"5P") for t in tickers]
        for fut in cf.as_completed(futures):
            ticker,data,err=fut.result(); intra_rows.extend(history_rows(ticker,data,SOURCE_ID))
            if err: errors.append({"ticker":ticker,"dataset":"5m","error":err})
    daily=pd.DataFrame(daily_rows); intra=pd.DataFrame(intra_rows)
    if not daily.empty: daily.sort_values(["ticker","timestamp"]).to_csv(out/"ohlcv.csv",index=False,encoding="utf-8-sig")
    if not intra.empty: intra.sort_values(["ticker","timestamp"]).to_csv(out/"intraday_5m.csv",index=False,encoding="utf-8-sig")
    raw_board,board_errors=fetch_price_board(tickers); errors.extend({"ticker":"*","dataset":"board","error":e} for e in board_errors)
    board=normalize_board(raw_board); board.to_csv(out/"latest_snapshot.csv",index=False,encoding="utf-8-sig")
    write_json(out/"kbs_price_board_raw.json",raw_board)
    vn_daily=pd.DataFrame(fetch_index_history("VNINDEX",start,end,"day")); vn_5m=pd.DataFrame(fetch_index_history("VNINDEX",intra_start,end,"5P"))
    if not vn_daily.empty: vn_daily.to_csv(out/"vnindex_daily.csv",index=False,encoding="utf-8-sig")
    if not vn_5m.empty: vn_5m.to_csv(out/"vnindex_5m.csv",index=False,encoding="utf-8-sig")
    technical=compute_technical(daily,intra,board); technical.to_csv(out/"technical_features_bootstrap.csv",index=False,encoding="utf-8-sig")
    coverage={
        "as_of":datetime.now(timezone.utc).isoformat(),"source":SOURCE_ID,"public_rights":"BLOCKED_PENDING_TERMS_REVIEW",
        "universe_count":len(tickers),"daily_covered":int(daily["ticker"].nunique()) if not daily.empty else 0,
        "intraday_5m_covered":int(intra["ticker"].nunique()) if not intra.empty else 0,"board_covered":int(board["ticker"].nunique()) if not board.empty else 0,
        "technical_feature_count":len(technical),"errors":errors
    }
    write_json(out/"market_coverage.json",coverage)
    if coverage["daily_covered"] < len(tickers)*0.95:
        raise RuntimeError(f"daily coverage too low: {coverage['daily_covered']}/{len(tickers)}")


def fetch_reference_finance(ticker: str) -> tuple[str, dict[str, Any], str | None]:
    try:
        with requests.Session() as s:
            profile=get_json(s,f"/stockinfo/profile/{ticker}",{"l":1})
            events=get_json(s,f"/stockinfo/event/{ticker}",{"l":1,"p":1,"s":50})
            reports={}
            specs=[("KQKD",2,1),("KQKD",2,2),("KQKD",1,1),("CDKT",1,1),("LCTT",1,1),("CSTC",2,1),("CSTC",1,1)]
            for typ,term,page in specs:
                params={"type":typ,"termtype":term,"termType":term,"code":ticker,"page":page,"pageSize":4,"unit":1,"languageid":1}
                reports[f"{typ}_{'Q' if term==2 else 'Y'}_P{page}"]=get_json(s,f"/stock/finance-info/{ticker}",params)
        return ticker,{"profile":profile,"events":events,"reports":reports},None
    except Exception as exc:
        return ticker,{},str(exc)


def flatten_finance_payload(ticker: str, key: str, payload: dict[str, Any]) -> list[dict[str, Any]]:
    heads=payload.get("Head",[]) if isinstance(payload,dict) else []
    content=payload.get("Content",{}) if isinstance(payload,dict) else {}
    rows=[]
    if not isinstance(content,dict): return rows
    for group,items in content.items():
        if not isinstance(items,list): continue
        for item in items:
            if not isinstance(item,dict): continue
            for i,h in enumerate(heads[:4],start=1):
                rows.append({
                    "ticker":ticker,"report_key":key,"content_group":group,"item_id":item.get("ReportNormID") or item.get("ID"),
                    "item_name_vi":item.get("Name"),"item_name_en":item.get("NameEn"),"unit":item.get("Unit"),
                    "year":h.get("YearPeriod"),"term_code":h.get("TermCode"),"period_begin":h.get("PeriodBegin"),"period_end":h.get("PeriodEnd"),
                    "report_date":h.get("ReportDate"),"last_update":h.get("LastUpdate"),"value":item.get(f"Value{i}"),"source":SOURCE_ID
                })
    return rows


def run_fundamentals(out: Path) -> None:
    universe,_=fetch_universe(); tickers=[r["ticker"] for r in universe]
    profiles=[]; events=[]; fin_rows=[]; errors=[]
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futures=[ex.submit(fetch_reference_finance,t) for t in tickers]
        for fut in cf.as_completed(futures):
            ticker,payload,err=fut.result()
            if err:
                errors.append({"ticker":ticker,"error":err}); continue
            p=payload.get("profile") if isinstance(payload,dict) else None
            if isinstance(p,dict):
                profiles.append({"ticker":ticker,"source":SOURCE_ID,"payload":json.dumps(p,ensure_ascii=False,separators=(",",":"),default=str)})
            ev=payload.get("events") if isinstance(payload,dict) else None
            events.append({"ticker":ticker,"source":SOURCE_ID,"payload":json.dumps(ev,ensure_ascii=False,separators=(",",":"),default=str)})
            for key,report in (payload.get("reports") or {}).items():
                if isinstance(report,dict): fin_rows.extend(flatten_finance_payload(ticker,key,report))
    pd.DataFrame(profiles).sort_values("ticker").to_csv(out/"company_profiles_raw.csv",index=False,encoding="utf-8-sig")
    pd.DataFrame(events).sort_values("ticker").to_csv(out/"corporate_events_raw.csv",index=False,encoding="utf-8-sig")
    fin=pd.DataFrame(fin_rows)
    if not fin.empty: fin.sort_values(["ticker","report_key","year","term_code","item_id"],na_position="last").to_csv(out/"financial_statements_long.csv",index=False,encoding="utf-8-sig")
    coverage={"as_of":datetime.now(timezone.utc).isoformat(),"source":SOURCE_ID,"public_rights":"BLOCKED_PENDING_TERMS_REVIEW","universe_count":len(tickers),"profile_covered":len(profiles),"events_covered":len(events),"finance_tickers_covered":int(fin["ticker"].nunique()) if not fin.empty else 0,"finance_rows":len(fin),"errors":errors}
    write_json(out/"fundamentals_coverage.json",coverage)
    if coverage["finance_tickers_covered"] < len(tickers)*0.90:
        raise RuntimeError(f"fundamental coverage too low: {coverage['finance_tickers_covered']}/{len(tickers)}")


def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--mode",choices=["market","fundamentals"],required=True); p.add_argument("--output-dir",type=Path,required=True); args=p.parse_args()
    args.output_dir.mkdir(parents=True,exist_ok=True)
    if args.mode=="market": run_market(args.output_dir)
    else: run_fundamentals(args.output_dir)
    write_json(args.output_dir/"bootstrap_metadata.json",{"mode":args.mode,"generated_at_utc":datetime.now(timezone.utc).isoformat(),"source":SOURCE_ID,"calculation_origin":"STOCKRADAR_INTERNAL_RESEARCH","external_scores_accepted":False,"publication_allowed":False,"redistribution_allowed":False,"note":"Bootstrap internal research only; production/public gate remains closed until rights and reconciliation are approved."})


if __name__ == "__main__":
    main()
