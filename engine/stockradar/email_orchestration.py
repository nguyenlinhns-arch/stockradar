from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Any, Mapping

from .premium_email import build_premium_action_alert, build_premium_daily


EMAIL_KINDS = {"DAILY_BRIEF", "EVENT_ALERT", "POST_SESSION_DIGEST", "WEEKLY_REPORT"}


@dataclass(frozen=True)
class EmailRecipientContext:
    user_id: str
    ticker: str | None = None
    horizon: str | None = None
    owns_stock: bool = False
    alert_enabled: bool = False


@dataclass(frozen=True)
class EmailCandidate:
    user_id: str
    email_kind: str
    idempotency_key: str
    snapshot_id: str | None
    payload: dict[str, Any]
    scheduled_at: str
    expires_at: str
    priority: int
    decision_ref: str | None

    def as_rpc_params(self) -> dict[str, Any]:
        return {
            "p_user_id": self.user_id,
            "p_email_kind": self.email_kind,
            "p_idempotency_key": self.idempotency_key,
            "p_snapshot_id": self.snapshot_id,
            "p_payload": self.payload,
            "p_scheduled_at": self.scheduled_at,
            "p_expires_at": self.expires_at,
            "p_priority": self.priority,
            "p_decision_ref": self.decision_ref,
        }


def _time(value: Any, name: str) -> datetime:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        raise ValueError(f"{name} is required")
    try:
        return datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"invalid {name}") from exc


def _require_text(value: Any, name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} is required")
    return text


def _idempotency(*parts: str) -> str:
    canonical = "|".join(str(part).strip() for part in parts)
    return "sr:" + sha256(canonical.encode("utf-8")).hexdigest()


def _validate_window(scheduled_at: str, expires_at: str) -> None:
    scheduled = _time(scheduled_at, "scheduled_at")
    expires = _time(expires_at, "expires_at")
    if expires <= scheduled:
        raise ValueError("expires_at must be after scheduled_at")


def build_action_email_candidate(
    recipient: EmailRecipientContext,
    decision: Mapping[str, Any],
    *,
    snapshot_id: str,
    decision_ref: str,
    scheduled_at: str,
    expires_at: str,
) -> EmailCandidate | None:
    """Convert one already-confirmed decision transition into a recipient-specific outbox candidate.

    This function never derives a stock decision. `decision` must already contain the confirmed
    previous/current decision state and action map from the StockRadar engine.
    """

    if not recipient.alert_enabled:
        return None
    ticker = _require_text(decision.get("ticker"), "ticker").upper()
    if recipient.ticker and recipient.ticker.strip().upper() != ticker:
        raise ValueError("recipient ticker context does not match decision")
    horizon = _require_text(decision.get("horizon"), "horizon").upper()
    if recipient.horizon and recipient.horizon.strip().upper() != horizon:
        raise ValueError("recipient horizon context does not match decision")

    _validate_window(scheduled_at, expires_at)
    snapshot = _require_text(snapshot_id, "snapshot_id")
    reference = _require_text(decision_ref, "decision_ref")

    payload = dict(decision)
    # Holding context is recipient-specific, but the engine-supplied decision values remain the source of truth.
    payload["recipient_owns_stock"] = bool(recipient.owns_stock)
    view_model = build_premium_action_alert(payload)
    previous_state = _require_text(payload.get("previous_state"), "previous_state").upper()
    current_state = _require_text(payload.get("current_state"), "current_state").upper()

    priority = {"P0": 0, "P1": 10, "P2": 20, "P3": 40}.get(str(view_model.get("urgency")), 40)
    return EmailCandidate(
        user_id=_require_text(recipient.user_id, "user_id"),
        email_kind="EVENT_ALERT",
        idempotency_key=_idempotency("EVENT_ALERT", recipient.user_id, reference, previous_state, current_state),
        snapshot_id=snapshot,
        payload=view_model,
        scheduled_at=scheduled_at,
        expires_at=expires_at,
        priority=priority,
        decision_ref=reference,
    )


def build_daily_email_candidate(
    user_id: str,
    report: Mapping[str, Any],
    *,
    snapshot_id: str,
    report_ref: str,
    scheduled_at: str,
    expires_at: str,
) -> EmailCandidate:
    """Build a 09:00 candidate from an already-assembled watchlist report."""

    _validate_window(scheduled_at, expires_at)
    snapshot = _require_text(snapshot_id, "snapshot_id")
    reference = _require_text(report_ref, "report_ref")
    view_model = build_premium_daily(report)
    return EmailCandidate(
        user_id=_require_text(user_id, "user_id"),
        email_kind="DAILY_BRIEF",
        idempotency_key=_idempotency("DAILY_BRIEF", user_id, reference),
        snapshot_id=snapshot,
        payload=view_model,
        scheduled_at=scheduled_at,
        expires_at=expires_at,
        priority=30,
        decision_ref=reference,
    )


def build_digest_email_candidate(
    user_id: str,
    email_kind: str,
    payload: Mapping[str, Any],
    *,
    snapshot_id: str | None,
    digest_ref: str,
    scheduled_at: str,
    expires_at: str,
) -> EmailCandidate:
    """Build optional post-session/weekly candidate without inventing stock decisions."""

    kind = _require_text(email_kind, "email_kind").upper()
    if kind not in {"POST_SESSION_DIGEST", "WEEKLY_REPORT"}:
        raise ValueError("digest email_kind is invalid")
    _validate_window(scheduled_at, expires_at)
    reference = _require_text(digest_ref, "digest_ref")
    body = dict(payload)
    if "summary" not in body:
        raise ValueError("digest summary is required")
    return EmailCandidate(
        user_id=_require_text(user_id, "user_id"),
        email_kind=kind,
        idempotency_key=_idempotency(kind, user_id, reference),
        snapshot_id=str(snapshot_id).strip() if snapshot_id else None,
        payload=body,
        scheduled_at=scheduled_at,
        expires_at=expires_at,
        priority=60 if kind == "POST_SESSION_DIGEST" else 70,
        decision_ref=reference,
    )
