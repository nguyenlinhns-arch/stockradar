from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .production_bundle import ProductionBundleError, build_manifest_from_descriptor
from .production_data import CONTRACT_VERSION, validate_production_manifest


INTAKE_SCHEMA_VERSION = "1.0"
LICENSED_MODE = "LICENSED"
REQUIRED_RIGHTS = (
    "source_terms_reviewed",
    "publication_allowed",
    "redistribution_allowed",
    "internal_analytics_allowed",
    "derived_outputs_allowed",
    "customer_display_allowed",
)
SENSITIVE_KEY_FRAGMENTS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "authorization",
    "access_token",
    "refresh_token",
    "trading_token",
    "private_key",
    "otp",
)
SENSITIVE_VALUE_PATTERNS = (
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{12,}", re.IGNORECASE),
    re.compile(r"\bsb_secret_[A-Za-z0-9_-]{8,}", re.IGNORECASE),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}", re.IGNORECASE),
)
SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]{0,159}$")


class LicensedIntakeError(ValueError):
    pass


@dataclass(frozen=True)
class LicensedIntakeResult:
    accepted: bool
    publication_ready: bool
    provider_id: str | None
    evidence_ref: str | None
    snapshot_id: str | None
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    dataset_rows: Mapping[str, int]
    dataset_checksums: Mapping[str, str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "intake_schema_version": INTAKE_SCHEMA_VERSION,
            "accepted": self.accepted,
            "publication_ready": self.publication_ready,
            "provider_id": self.provider_id,
            "evidence_ref": self.evidence_ref,
            "snapshot_id": self.snapshot_id,
            "failures": list(self.failures),
            "warnings": list(self.warnings),
            "dataset_rows": dict(self.dataset_rows),
            "dataset_checksums": dict(self.dataset_checksums),
            "gate_mutation_performed": False,
            "credentials_persisted": False,
        }


def _inside(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def ensure_private_staging(staging_dir: str | Path, *, repo_root: str | Path | None = None) -> Path:
    staging = Path(staging_dir).resolve()
    if not staging.is_dir():
        raise LicensedIntakeError(f"staging directory is missing: {staging}")
    if repo_root is not None:
        root = Path(repo_root).resolve()
        forbidden = (root / "website", root / ".pages-site")
        for candidate in forbidden:
            if _inside(staging, candidate):
                raise LicensedIntakeError(
                    f"licensed staging must stay outside public website artifacts: {staging}"
                )
    return staging


def _find_sensitive(value: object, path: tuple[str, ...] = ()) -> list[str]:
    findings: list[str] = []
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            key = str(raw_key)
            normalized = key.lower().replace("-", "_")
            child_path = (*path, key)
            if any(fragment in normalized for fragment in SENSITIVE_KEY_FRAGMENTS):
                findings.append(".".join(child_path))
            findings.extend(_find_sensitive(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_find_sensitive(child, (*path, str(index))))
    elif isinstance(value, str):
        if any(pattern.search(value) for pattern in SENSITIVE_VALUE_PATTERNS):
            findings.append(".".join(path) or "<root>")
    return findings


def _timezone_timestamp(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise LicensedIntakeError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as error:
        raise LicensedIntakeError(f"{field} must be ISO-8601") from error
    if parsed.tzinfo is None:
        raise LicensedIntakeError(f"{field} must include timezone")
    return text


def _safe_identifier(value: object, field: str) -> str:
    text = str(value or "").strip()
    if not text or not SAFE_IDENTIFIER.fullmatch(text):
        raise LicensedIntakeError(f"{field} is missing or contains unsafe characters")
    return text


def _rights_descriptor(rights_payload: Mapping[str, Any], *, now: datetime | None = None) -> tuple[dict[str, Any], str, str]:
    if str(rights_payload.get("schema_version") or "").strip() != INTAKE_SCHEMA_VERSION:
        raise LicensedIntakeError(
            f"rights schema_version must be {INTAKE_SCHEMA_VERSION!r}"
        )
    if str(rights_payload.get("mode") or "").strip().upper() != LICENSED_MODE:
        raise LicensedIntakeError("rights mode must be LICENSED; research/reference sources cannot enter production intake")

    provider_id = _safe_identifier(rights_payload.get("provider_id"), "provider_id")
    contract_ref = _safe_identifier(rights_payload.get("contract_ref"), "contract_ref")
    evidence_ref = _safe_identifier(rights_payload.get("evidence_ref"), "evidence_ref")
    reviewed_at = _timezone_timestamp(rights_payload.get("reviewed_at"), "reviewed_at")

    permissions = rights_payload.get("permissions")
    if not isinstance(permissions, Mapping):
        raise LicensedIntakeError("permissions object is required")
    missing = [key for key in REQUIRED_RIGHTS if permissions.get(key) is not True]
    if missing:
        raise LicensedIntakeError(
            "licensed rights are incomplete: " + ", ".join(missing)
        )

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise LicensedIntakeError("now must be timezone-aware")
    effective_from_raw = rights_payload.get("effective_from")
    effective_until_raw = rights_payload.get("effective_until")
    if effective_from_raw:
        effective_from = datetime.fromisoformat(
            _timezone_timestamp(effective_from_raw, "effective_from").replace("Z", "+00:00")
        )
        if current.astimezone(timezone.utc) < effective_from.astimezone(timezone.utc):
            raise LicensedIntakeError("license is not effective yet")
    if effective_until_raw:
        effective_until = datetime.fromisoformat(
            _timezone_timestamp(effective_until_raw, "effective_until").replace("Z", "+00:00")
        )
        if current.astimezone(timezone.utc) >= effective_until.astimezone(timezone.utc):
            raise LicensedIntakeError("license has expired")

    rights = {
        "publication_allowed": True,
        "redistribution_allowed": True,
        "source_terms_reviewed": True,
        "evidence_ref": evidence_ref,
        "provider_id": provider_id,
        "contract_ref": contract_ref,
        "reviewed_at": reviewed_at,
        "internal_analytics_allowed": True,
        "derived_outputs_allowed": True,
        "customer_display_allowed": True,
    }
    return rights, provider_id, evidence_ref


def load_json_object(path: str | Path) -> Mapping[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise LicensedIntakeError(f"JSON object required: {path}")
    return payload


def _descriptor_from_package(
    package: Mapping[str, Any],
    rights: Mapping[str, Any],
) -> dict[str, Any]:
    if str(package.get("schema_version") or "").strip() != INTAKE_SCHEMA_VERSION:
        raise LicensedIntakeError(
            f"package schema_version must be {INTAKE_SCHEMA_VERSION!r}"
        )
    snapshot = package.get("snapshot")
    compliance = package.get("compliance")
    active_status = package.get("active_status")
    datasets = package.get("datasets")
    if not isinstance(snapshot, Mapping):
        raise LicensedIntakeError("package.snapshot object is required")
    if str(snapshot.get("exchange") or "").strip().upper() != "HOSE":
        raise LicensedIntakeError("licensed intake only accepts HOSE")
    if not isinstance(compliance, Mapping):
        raise LicensedIntakeError("package.compliance object is required")
    if not isinstance(active_status, Mapping):
        raise LicensedIntakeError("package.active_status object is required")
    if not isinstance(datasets, Mapping):
        raise LicensedIntakeError("package.datasets object is required")

    return {
        "contract_version": CONTRACT_VERSION,
        "snapshot": dict(snapshot),
        "rights": dict(rights),
        "compliance": dict(compliance),
        "active_status": dict(active_status),
        "datasets": {str(key): dict(value) if isinstance(value, Mapping) else value for key, value in datasets.items()},
    }


def _descriptor_sha256(descriptor: Mapping[str, Any]) -> str:
    canonical = json.dumps(
        descriptor,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def prepare_licensed_intake(
    staging_dir: str | Path,
    package_payload: Mapping[str, Any],
    rights_payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
    now: datetime | None = None,
    max_age_seconds: int = 21_600,
) -> tuple[dict[str, Any], LicensedIntakeResult, dict[str, Any]]:
    staging = ensure_private_staging(staging_dir, repo_root=repo_root)
    sensitive = _find_sensitive(package_payload) + _find_sensitive(rights_payload)
    if sensitive:
        raise LicensedIntakeError(
            "secret material is forbidden in intake metadata: " + ", ".join(dict.fromkeys(sensitive))
        )

    rights, provider_id, evidence_ref = _rights_descriptor(rights_payload, now=now)
    descriptor = _descriptor_from_package(package_payload, rights)

    try:
        manifest = build_manifest_from_descriptor(staging, descriptor)
    except ProductionBundleError as error:
        raise LicensedIntakeError(str(error)) from error

    gate = validate_production_manifest(
        manifest,
        now=now,
        max_age_seconds=max_age_seconds,
    )
    datasets = manifest.get("datasets") if isinstance(manifest.get("datasets"), Mapping) else {}
    row_counts: dict[str, int] = {}
    checksums: dict[str, str] = {}
    for name, raw in datasets.items():
        if not isinstance(raw, Mapping):
            continue
        try:
            row_counts[str(name)] = int(raw.get("row_count") or 0)
        except (TypeError, ValueError):
            row_counts[str(name)] = 0
        checksums[str(name)] = str(raw.get("sha256") or "")

    result = LicensedIntakeResult(
        accepted=True,
        publication_ready=gate.passed,
        provider_id=provider_id,
        evidence_ref=evidence_ref,
        snapshot_id=gate.snapshot_id,
        failures=gate.failures,
        warnings=gate.warnings,
        dataset_rows=row_counts,
        dataset_checksums=checksums,
    )
    report = result.to_dict()
    report["descriptor_sha256"] = _descriptor_sha256(descriptor)
    report["production_gate"] = gate.to_dict()
    return descriptor, result, report


def write_private_json(path: str | Path, payload: Mapping[str, Any], *, repo_root: str | Path | None = None) -> None:
    target = Path(path).resolve()
    if repo_root is not None:
        root = Path(repo_root).resolve()
        for candidate in (root / "website", root / ".pages-site"):
            if _inside(target, candidate):
                raise LicensedIntakeError(
                    f"licensed intake output must stay outside public website artifacts: {target}"
                )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
