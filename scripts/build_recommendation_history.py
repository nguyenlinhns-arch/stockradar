"""Reconcile evidenced alerts and replay historical technical screens without backdating releases.

Raw market data and email originals stay private. Public output contains only audited
alert terms and derived observations. A price change is never an executed trade return.
"""
from __future__ import annotations

import argparse
from calendar import monthrange
from dataclasses import asdict
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.stockradar.internal_features import RawBar, compute_technical_features

VERSION = "TECHNICAL_EOD_REVIEW_V1"
HOLIDAYS = {"2026-08-31", "2026-09-01", "2026-09-02"}
CALENDAR_SOURCE = "https://dxkmmj70ij70u.cloudfront.net/thong-bao-lich-nghi-le-quoc-khanh-02092026"


def price_change(current, reference):
    return round((current / reference - 1) * 100, 4) if current and reference else None


def validate_history(history):
    frame = history.copy()
    frame["date"] = pd.to_datetime(frame.timestamp, errors="raise").dt.strftime("%Y-%m-%d")
    if frame.duplicated(["ticker", "date"]).any():
        raise ValueError("Duplicate ticker/session: refusing ambiguous history")
    cols = ["open", "high", "low", "close", "volume"]
    if frame[cols].isna().any().any():
        raise ValueError("Missing OHLCV values")
    bad = ((frame[cols[:4]] <= 0).any(axis=1) | (frame.volume < 0)
           | (frame.high < frame[["open", "close", "low"]].max(axis=1))
           | (frame.low > frame[["open", "close", "high"]].min(axis=1)))
    # Invalid source bars are excluded explicitly, not repaired or silently zero-filled.
    return frame.loc[~bad].sort_values(["ticker", "date"]), int(bad.sum())


def reconcile_alerts(ledger, history, as_of):
    events = sorted(ledger["events"], key=lambda e: e["sent_at"])
    if len({e["event_id"] for e in events}) != len(events):
        raise ValueError("Duplicate alert event")
    rows = []
    for rid in dict.fromkeys(e["recommendation_id"] for e in events):
        timeline = [e for e in events if e["recommendation_id"] == rid]
        first = timeline[0]
        if first["kind"] != "BUY" or not all(e.get("evidence_sha256") for e in timeline):
            raise ValueError("Historical alert requires an evidenced initial buy")
        sells = [e for e in timeline if e["kind"] == "SELL"]
        prices = history[(history.ticker == first["ticker"]) & (history.date <= as_of)]
        last = prices.iloc[-1] if not prices.empty else None
        current = float(last.close) if last is not None else None
        rows.append({"recommendation_id": rid, "ticker": first["ticker"],
                     "record_mode": "VERIFIED_EMAIL_HISTORY", "new_buy_allowed": False,
                     "status": "SELL_EMAIL_RECORDED" if sells else "NO_SELL_EMAIL_FOUND",
                     "first_sent_at": first["sent_at"], "signal_at": first["signal_at"],
                     "reference_price": first["reference_price"],
                     "latest_price": current, "price_date": str(last.date) if last is not None else None,
                     "price_change_pct": price_change(current, first["reference_price"]),
                     "execution_return_pct": None, "execution_status": "NO_BROKER_FILL_EVIDENCE",
                     "timeline": timeline})
    return {"schema_version": "STOCKRADAR_VERIFIED_HISTORY_V1", "as_of_date": as_of,
            "audit_at": ledger["audit_at"], "mail_search_through": ledger["mail_search_through"],
            "source": "Email StockRadar đã đối chiếu với thư gốc và nhật ký gửi",
            "summary": {"tickers": len({r["ticker"] for r in rows}), "alerts": len(events),
                        "without_sell_email": sum(r["status"] == "NO_SELL_EMAIL_FOUND" for r in rows),
                        "with_sell_email": sum(r["status"] == "SELL_EMAIL_RECORDED" for r in rows),
                        "realized_return_pct": None}, "items": rows}


def feature_at(group, cutoff):
    """Indicators see no bar later than cutoff, including for moving-average baselines."""
    past = group[group.date <= cutoff]
    if len(past) < 252 or past.iloc[-1].date != cutoff:
        return None
    bars = [RawBar(str(r.date), r.open, r.high, r.low, r.close, r.volume)
            for r in past.tail(252).itertuples()]
    return compute_technical_features(bars)


def setup_for(f):
    """EOD technical subset of scanner-v2. No fabricated fundamental pass."""
    if f is None or f.avg_volume20 < 500_000:
        return None
    stage2 = f.close > f.ma50 > f.ma150 > f.ma200 and f.ma200 >= f.ma200_20d_ago
    transition = f.close >= f.ma200 and f.ma50 >= f.ma150
    if not (stage2 or transition) or f.close > f.ma50 * 1.10 or f.last_change_pct < 2:
        return None
    distance = (f.close / f.pivot20 - 1) * 100
    if stage2 and f.close >= f.pivot20 and f.volume_ratio20 >= 1.4:
        return "CONFIRMED_BREAKOUT"
    if -1.5 <= distance <= 2.5 and f.volume_ratio20 >= 1.1:
        return "EARLY_BREAKOUT"
    near = abs(f.close / f.ma10 - 1) <= .08 or abs(f.close / f.ma50 - 1) <= .08
    # max_down_volume10 is over the previous ten sessions, not ten down sessions.
    if f.max_down_volume10 > 0 and near:
        volume = f.avg_volume20 * f.volume_ratio20
        if volume > f.max_down_volume10:
            return "POCKET_PIVOT"
    return None


def replay_month(history, month, as_of, generated_at):
    year, number = map(int, month.split("-"))
    groups = {t: g for t, g in history[history.date <= as_of].groupby("ticker")}
    universe = sorted(groups)
    days, candidates = [], []
    features = {}
    def get(ticker, day):
        key = (ticker, day)
        if key not in features:
            features[key] = feature_at(groups[ticker], day)
        return features[key]
    for day_num in range(1, monthrange(year, number)[1] + 1):
        d = date(year, number, day_num)
        day = d.isoformat()
        closed = d.weekday() >= 5 or day in HOLIDAYS
        present = history[history.date == day]
        if closed:
            days.append({"date": day, "status": "HOLIDAY" if day in HOLIDAYS else "WEEKEND", "available": 0, "evaluated": 0, "candidates": []})
            continue
        tickers = sorted(present.ticker.unique())
        evaluated = 0
        hits = []
        for ticker in tickers:
            f = get(ticker, day)
            if f is None:
                continue
            evaluated += 1
            setup = setup_for(f)
            if not setup:
                continue
            follow = groups[ticker][groups[ticker].date > day]
            exit_date, exit_reason = None, None
            # A technical review condition, not a reconstructed email or a fill.
            for bar in follow.itertuples():
                later = get(ticker, bar.date)
                if later and (bar.close < later.ma200 * .97 or bar.close < later.ma50 * .97):
                    exit_date = bar.date
                    exit_reason = "CLOSE_BELOW_MA200_3PCT" if bar.close < later.ma200 * .97 else "CLOSE_BELOW_MA50_3PCT"
                    break
            latest = groups[ticker].iloc[-1]
            sessions = sorted(history.loc[(history.date > day) & (history.date <= as_of), "date"].unique())
            missing_followup = sorted(set(sessions) - set(follow.date))
            hits.append(ticker)
            candidates.append({"id": f"{ticker}-{day}", "ticker": ticker, "signal_date": day,
                "setup": setup, "record_mode": "RETROSPECTIVE_TECHNICAL_SCREEN",
                "full_buy_criteria": "UNVERIFIED", "new_buy_allowed": False,
                "reference_close": f.close, "latest_close": float(latest.close), "price_date": str(latest.date),
                "price_change_pct": price_change(float(latest.close), f.close),
                "volume_ratio": f.volume_ratio20, "ma10": f.ma10, "ma50": f.ma50, "ma200": f.ma200,
                "pivot20": f.pivot20, "change_on_signal_pct": f.last_change_pct,
                "technical_exit_date": exit_date, "technical_exit_reason": exit_reason,
                "followup_status": "GAPS" if missing_followup else "COMPLETE",
                "missing_followup_sessions": missing_followup,
                "status": "TECHNICAL_EXIT_SEEN" if exit_date else "UNRESOLVED_DATA" if missing_followup else "NO_TECHNICAL_EXIT_SEEN"})
        days.append({"date": day, "status": "REVIEWED" if tickers else "MISSING_DATA", "available": len(tickers),
                     "evaluated": evaluated, "missing_tickers": sorted(set(universe) - set(tickers)), "candidates": hits})
    open_rows = [r for r in candidates if r["status"] == "NO_TECHNICAL_EXIT_SEEN"]
    return {"schema_version": VERSION, "month": month, "as_of_date": as_of, "generated_at": generated_at,
            "calendar_source": CALENDAR_SOURCE, "universe_basis": "CURRENT_405_HOSE_NOT_HISTORICAL_CONSTITUENTS",
            "summary": {"universe": len(universe), "sessions": sum(d["status"] == "REVIEWED" for d in days),
                "candidate_occurrences": len(candidates), "candidate_tickers": len({r["ticker"] for r in candidates}),
                "without_technical_exit_tickers": sorted({r["ticker"] for r in open_rows}),
                "full_buy_criteria_verified": None},
            "limitations": ["4M và CANSLIM chưa có đủ hồ sơ công bố tại từng ngày để xác minh toàn bộ tiêu chí mua.",
                "Rà soát giá và khối lượng cuối phiên; không khôi phục tín hiệu trong phiên hoặc email đã gửi.",
                "Dùng danh sách 405 mã HOSE hiện tại; có thể thiếu mã đã rời sàn trong tháng 8.",
                "Biến động giá tham khảo, chưa tính phí, thuế, cổ tức và quyền; không phải lãi/lỗ của giao dịch.",
                "Điều kiện thoát kỹ thuật: đóng cửa thấp hơn MA50 hoặc MA200 trên 3%; chưa thay thế đánh giá bán đầy đủ."],
            "days": days, "items": candidates}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--history", type=Path, required=True)
    p.add_argument("--ledger", type=Path, default=Path("track-record/verified-email-alerts.json"))
    p.add_argument("--output", type=Path, default=Path("website/public/data"))
    p.add_argument("--month", default="2026-08")
    p.add_argument("--as-of", required=True)
    p.add_argument("--skip-replay", action="store_true", help="Refresh evidenced email quote follow-up only; retain the dated historical study")
    args = p.parse_args()
    history, invalid = validate_history(pd.read_csv(args.history))
    history = history[history.date <= args.as_of]
    ledger = json.loads(args.ledger.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc).isoformat()
    observed = reconcile_alerts(ledger, history, args.as_of)
    if args.skip_replay:
        args.output.mkdir(parents=True, exist_ok=True)
        write_path = args.output / 'recommendation-history.json'
        write_path.write_text(json.dumps(observed, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'history': observed['summary'], 'as_of_date': args.as_of, 'invalid_bars_excluded': invalid}))
        return
    replay = replay_month(history, args.month, args.as_of, now)
    replay["input_sha256"] = hashlib.sha256(args.history.read_bytes()).hexdigest()
    replay["invalid_bars_excluded"] = invalid
    args.output.mkdir(parents=True, exist_ok=True)
    for name, data in [("recommendation-history.json", observed), ("recommendation-review-" + args.month + ".json", replay)]:
        (args.output / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"history": observed["summary"], "replay": replay["summary"], "invalid": invalid}, ensure_ascii=False))


if __name__ == "__main__":
    main()
