from __future__ import annotations

import json
from typing import Any

MXH_BRIDGE_PREFIX = "MXH_V1:"
MXH_ACTIONS = frozenset({
    "status",
    "list_edited",
    "resolve_title",
    "content_readback",
    "plan_readback",
    "create_or_reuse_plan",
    "native_schedule",
    "job_readback",
})


class MxhContractError(ValueError):
    pass


def parse_mxh_bridge(goal: Any) -> dict[str, Any] | None:
    if not isinstance(goal, str) or not goal.startswith(MXH_BRIDGE_PREFIX):
        return None
    raw = goal[len(MXH_BRIDGE_PREFIX):].strip()
    if not raw:
        raise MxhContractError("MXH_BRIDGE_PAYLOAD_REQUIRED")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MxhContractError("MXH_BRIDGE_JSON_INVALID") from exc
    if not isinstance(payload, dict):
        raise MxhContractError("MXH_BRIDGE_OBJECT_REQUIRED")
    action = payload.get("action")
    if action not in MXH_ACTIONS:
        raise MxhContractError("MXH_BRIDGE_ACTION_INVALID")
    allowed = {
        "action", "title", "video_sha256", "flow_id", "plan_id", "job_id",
        "artifact_job_id", "caption", "hashtags", "platforms", "scheduled_at",
        "timezone", "idempotency_key", "timeout_seconds", "limit",
    }
    extras = sorted(set(payload) - allowed)
    if extras:
        raise MxhContractError("MXH_BRIDGE_UNKNOWN_FIELDS:" + ",".join(extras))
    return payload


def mxh_action_risk(action: str) -> str:
    if action in {"status", "list_edited", "resolve_title", "content_readback", "plan_readback", "job_readback"}:
        return "READ"
    if action in {"create_or_reuse_plan", "native_schedule"}:
        return "MODIFY"
    raise MxhContractError("MXH_BRIDGE_ACTION_INVALID")
