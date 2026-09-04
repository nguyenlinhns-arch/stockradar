from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence


STATE_LABELS = {
    "BUY": "MUA",
    "WAIT": "CHỜ",
    "HOLD": "GIỮ",
    "ADD": "TĂNG",
    "REDUCE": "GIẢM",
    "SELL": "BÁN",
}

URGENT_STATES = {"SELL": "P0", "REDUCE": "P1", "BUY": "P2", "ADD": "P2"}
TACTICAL_HORIZONS = {"SHORT_TERM", "MEDIUM_TERM"}


def _required(payload: Mapping[str, Any], key: str) -> Any:
    value = payload.get(key)
    if value is None or value == "" or value == []:
        raise ValueError(f"missing required email field: {key}")
    return value


def _parse_time(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        raise ValueError("missing timestamp")
    return datetime.fromisoformat(text)


def _state(value: Any) -> str:
    state = str(value or "").strip().upper()
    if state not in STATE_LABELS:
        raise ValueError(f"invalid decision state: {state}")
    return state


def _ticker(value: Any) -> str:
    ticker = str(value or "").strip().upper()
    if len(ticker) != 3 or not ticker.isalnum() or not any(ch.isalpha() for ch in ticker):
        raise ValueError("invalid HOSE ticker")
    return ticker


def _reasons(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("reasons must be a sequence")
    reasons = [str(item).strip() for item in value if str(item).strip()]
    if not 2 <= len(reasons) <= 4:
        raise ValueError("Premium alert requires 2-4 strongest reasons")
    return reasons


def build_premium_action_alert(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build a provider-agnostic Premium action-alert view model.

    This function does not send mail and does not calculate a stock decision. It only
    validates and formats a decision already confirmed by StockRadar's state machine.
    """

    ticker = _ticker(_required(payload, "ticker"))
    horizon = str(_required(payload, "horizon")).strip().upper()
    previous_state = _state(_required(payload, "previous_state"))
    current_state = _state(_required(payload, "current_state"))
    evaluated_at = _parse_time(_required(payload, "evaluated_at"))
    generated_at = _parse_time(_required(payload, "generated_at"))
    next_review = _required(payload, "next_review")
    reasons = _reasons(_required(payload, "reasons"))
    invalidation = str(_required(payload, "invalidation")).strip()

    if previous_state == current_state:
        raise ValueError("NO_MATERIAL_STATE_CHANGE")
    if generated_at < evaluated_at:
        raise ValueError("generated_at cannot precede evaluated_at")

    reference_price = payload.get("reference_price")
    if current_state in {"BUY", "ADD", "REDUCE", "SELL"} and reference_price is None:
        raise ValueError("price-dependent action requires reference_price")

    buy_zone = payload.get("buy_zone")
    stop = payload.get("stop")
    target = payload.get("target")
    risk_reward = payload.get("risk_reward")

    if current_state in {"BUY", "ADD"}:
        if not buy_zone:
            raise ValueError("BUY/ADD alert requires buy_zone")
        if stop is None and not invalidation:
            raise ValueError("BUY/ADD alert requires stop or invalidation")
        if horizon in TACTICAL_HORIZONS and (target is None or risk_reward is None):
            raise ValueError("tactical BUY/ADD alert requires target and risk_reward")

    previous_label = STATE_LABELS[previous_state]
    current_label = STATE_LABELS[current_state]
    evaluated_label = evaluated_at.strftime("%H:%M")

    subject = f"[StockRadar] {ticker} · {previous_label} → {current_label} | {evaluated_label}"
    preheader = f"{ticker}: trạng thái vừa đổi. Xem việc cần làm và điều kiện làm quyết định không còn đúng."

    decision_card = {
        "ticker": ticker,
        "horizon": horizon,
        "previous_state": previous_label,
        "current_state": current_label,
        "evaluated_at": evaluated_at.isoformat(),
        "generated_at": generated_at.isoformat(),
        "reference_price": reference_price,
        "new_position_decision": payload.get("new_position_decision"),
        "holding_decision": payload.get("holding_decision"),
        "buy_zone": buy_zone,
        "stop": stop,
        "target": target,
        "risk_reward": risk_reward,
        "invalidation": invalidation,
        "next_review": next_review,
    }

    return {
        "kind": "EVENT_ALERT",
        "urgency": URGENT_STATES.get(current_state, "P3"),
        "subject": subject,
        "preheader": preheader,
        "headline": f"{ticker} · {previous_label} → {current_label}",
        "decision_card": decision_card,
        "reasons": reasons,
        "late_open_notice": (
            "Quyết định được đánh giá tại thời điểm nêu trên. Nếu bạn mở email muộn, "
            "hãy xem trạng thái mới nhất trước khi hành động."
        ),
        "no_chase_notice": (
            "Chỉ cân nhắc trong vùng hành động; nếu giá đã rời vùng, không mặc định đuổi giá."
            if current_state in {"BUY", "ADD"}
            else None
        ),
        "primary_cta": "XEM TRẠNG THÁI MỚI NHẤT",
    }


def build_premium_daily(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build a watchlist-first Premium 09:00 report view model."""

    report_date = _parse_time(_required(payload, "report_date"))
    generated_at = _parse_time(_required(payload, "generated_at"))
    market_context = str(_required(payload, "market_context")).strip()
    changes = payload.get("watchlist_changes") or []
    if not isinstance(changes, Sequence) or isinstance(changes, (str, bytes)):
        raise ValueError("watchlist_changes must be a sequence")

    normalized_changes: list[dict[str, Any]] = []
    for item in changes:
        if not isinstance(item, Mapping):
            raise ValueError("watchlist change must be an object")
        ticker = _ticker(_required(item, "ticker"))
        current_state = _state(_required(item, "current_state"))
        previous = item.get("previous_state")
        previous_state = _state(previous) if previous else None
        normalized_changes.append(
            {
                "ticker": ticker,
                "previous_state": STATE_LABELS[previous_state] if previous_state else None,
                "current_state": STATE_LABELS[current_state],
                "owns_stock": bool(item.get("owns_stock")),
                "note": str(item.get("note") or "").strip(),
                "urgency": URGENT_STATES.get(current_state, "P3"),
            }
        )

    urgency_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    normalized_changes.sort(key=lambda row: (urgency_order[row["urgency"]], row["ticker"]))

    date_label = report_date.strftime("%d/%m")
    if normalized_changes:
        subject = f"[StockRadar] {len(normalized_changes)} mã cần chú ý hôm nay · {date_label}"
        headline = f"Hôm nay bạn cần chú ý {len(normalized_changes)} mã"
    else:
        subject = f"[StockRadar] Watchlist ổn định · chưa cần hành động · {date_label}"
        headline = "Watchlist ổn định · chưa cần hành động"

    return {
        "kind": "DAILY_BRIEF",
        "subject": subject,
        "preheader": "Watchlist của bạn trước, bối cảnh thị trường sau.",
        "headline": headline,
        "watchlist_changes": normalized_changes,
        "stable_watchlist_count": int(payload.get("stable_watchlist_count") or 0),
        "market_context": market_context,
        "opportunities": list(payload.get("opportunities") or []),
        "risk_items": list(payload.get("risk_items") or []),
        "report_date": report_date.isoformat(),
        "generated_at": generated_at.isoformat(),
        "primary_cta": "MỞ MY STOCKRADAR",
    }
