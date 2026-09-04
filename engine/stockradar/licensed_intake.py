from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping

from .input_policy import CALCULATION_ORIGIN, CALCULATION_POLICY_VERSION, EXTERNAL_INPUT_ROLE, is_derived_field
from .production_bundle import (
    CONTRACT_VERSION,
    REQUIRED_DATASETS,
    ProductionBundleError,
    build_manifest_from_descriptor,
)
from .production_data import validate_production_manifest


INTAKE_SCHEMA_VERSION = "1.0"
RIGHTS_SCHEMA_VERSION = "1.0"
REQUIRED_PERMISSIONS = (
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
    "otp",
)


@dataclass(frozen=True)
class LicensedIntakeResult:
    accepted: bool
    publication_ready: bool
    provider_id: str
    evidence_ref: str
    snapshot_id: str | None
    failures: tuple[str, ...]
    warnings: tuple[str, ...]
    dataset_rows: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "publication_ready": self.publication_ready,
            "provider_id": self.provider_id,
            "evidence_ref": self.evidence_ref,
            "snapshot_id": self.snapshot_id,
            "failures": list(self.failures),
            "warnings": list(self.warnings),
            "dataset_rows": dict(self.dataset_rows),
            "input_role": EXTERNAL_INPUT_ROLE,
            "calculation_origin": CALCULATION_ORIGIN,
            "calculation_policy_version": CALCULATION_POLICY_VERSION,
        }


class LicensedIntakeError(RuntimeError):
    pass


def _parse_timestamp(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else None


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
    return findings


def _is_public_path(path: Path, repo_root: Path | None) -> bool:
    if repo_root is None:
        return False
    public_root = (repo_root / "website").resolve()
    try:
        path.resolve().relative_to(public_root)
    except ValueError:
        return False
    return True


def ensure_private_staging(path: str | Path, *, repo_root: str | Path | None = None) -> Path:
    staging = Path(path).resolve()
    if not staging.is_dir():
        raise LicensedIntakeError(f"licensed staging directory is missing: {staging}")
    root = Path(repo_root).resolve() if repo_root is not None else None
    if _is_public_path(staging, root):
        raise LicensedIntakeError("licensed staging must remain outside public website")
    return staging


def write_private_json(
    path: str | Path,
    payload: Mapping[str, Any],
    *,
    repo_root: str | Path | None = None,
) -> Path:
    target = Path(path).resolve()
    root = Path(repo_root).resolve() if repo_root is not None else None
    if _is_public_path(target, root):
        raise LicensedIntakeError("licensed output must remain outside public website")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def copy_private_bundle(
    source: str | Path,
    target: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> Path:
    source_root = ensure_private_staging(source, repo_root=repo_root)
    target_root = Path(target).resolve()
    root = Path(repo_root).resolve() if repo_root is not None else None
    if _is_public_path(target_root, root):
        raise LicensedIntakeError("licensed bundle target must remain outside public website")
    if target_root.exists():
        shutil.rmtree(target_root)
    shutil.copytree(source_root, target_root)
    return target_root


def _rights_descriptor(
    rights_payload: Mapping[str, Any],
    *,
    now: datetime | None = None,
) -> tuple[dict[str, Any], str, str]:
    if str(rights_payload.get("schema_version") or "").strip() != RIGHTS_SCHEMA_VERSION:
        raise LicensedIntakeError(
            f"rights schema_version must be {RIGHTS_SCHEMA_VERSION!r}"
        )
    mode = str(rights_payload.get("mode") or "").strip().upper()
    if mode != "LICENSED":
        raise LicensedIntakeError("rights mode must be LICENSED")

    provider_id = str(rights_payload.get("provider_id") or "").strip()
    contract_ref = str(rights_payload.get("contract_ref") or "").strip()
    evidence_ref = str(rights_payload.get("evidence_ref") or "").strip()
    reviewed_at = str(rights_payload.get("reviewed_at") or "").strip()
    if not provider_id or not contract_ref or not evidence_ref or not reviewed_at:
        raise LicensedIntakeError("provider_id, contract_ref, evidence_ref and reviewed_at are required")

    permissions = rights_payload.get("permissions")
    if not isinstance(permissions, Mapping):
        raise LicensedIntakeError("rights permissions object is required")
    for permission in REQUIRED_PERMISSIONS:
        if permissions.get(permission) is not True:
            raise LicensedIntakeError(f"licensed permission must be explicitly true: {permission}")

    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    effective_from = _parse_timestamp(rights_payload.get("effective_from"))
    effective_until = _parse_timestamp(rights_payload.get("effective_until"))
    if effective_from is not None and current < effective_from.astimezone(current.tzinfo):
        raise LicensedIntakeError("license is not yet effective")
    if effective_until is not None and current > effective_until.astimezone(current.tzinfo):
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
    )
    report = {
        "schema_version": INTAKE_SCHEMA_VERSION,
        "accepted": True,
        "publication_ready": gate.passed,
        "provider_id": provider_id,
        "evidence_ref": evidence_ref,
        "descriptor_sha256": _descriptor_sha256(descriptor),
        "dataset_rows": row_counts,
        "dataset_checksums": checksums,
        "production_gate": gate.to_dict(),
        "gate_mutation_performed": False,
        "credentials_persisted": False,
        "public_output_written": False,
    }
    return descriptor, result, report
