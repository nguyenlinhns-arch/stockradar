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
MXH_READ_ACTIONS = frozenset({
    "status",
    "list_edited",
    "resolve_title",
    "content_readback",
    "plan_readback",
    "job_readback",
})


class MxhContractError(ValueError):
    pass


def parse_mxh_bridge(goal: Any) -> tuple[str, dict[str, Any]] | None:
    if not isinstance(goal, str) or not goal.startswith(MXH_BRIDGE_PREFIX):
        return None
    raw = goal[len(MXH_BRIDGE_PREFIX):].strip()
    if not raw or len(raw) > 12000:
        raise MxhContractError("MXH_BRIDGE_INVALID")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise MxhContractError("MXH_BRIDGE_INVALID") from exc
    if not isinstance(payload, dict) or set(payload) - {"action", "arguments"}:
        raise MxhContractError("MXH_BRIDGE_INVALID")
    action = payload.get("action")
    arguments = payload.get("arguments", {})
    if action not in MXH_ACTIONS or not isinstance(arguments, dict):
        raise MxhContractError("MXH_BRIDGE_INVALID")
    if len(json.dumps(arguments, ensure_ascii=False)) > 10000:
        raise MxhContractError("MXH_BRIDGE_ARGUMENTS_TOO_LARGE")
    return str(action), arguments


def mxh_action_risk(action: str) -> str:
    if action in MXH_READ_ACTIONS:
        return "READ"
    if action in {"create_or_reuse_plan", "native_schedule"}:
        return "MODIFY"
    raise MxhContractError("MXH_BRIDGE_ACTION_INVALID")
