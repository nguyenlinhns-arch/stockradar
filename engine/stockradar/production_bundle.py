from __future__ import annotations

import csv
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from .input_policy import (
    EXTERNAL_INPUT_ROLE,
    ExternalDerivedDataError,
    computation_provenance,
    validate_external_raw_columns,
)
from .production_data import CONTRACT_VERSION, COVERAGE_DATASETS, REQUIRED_DATASETS
from .ticker_symbol import is_valid_hose_ticker


class ProductionBundleError(ValueError):
    pass


@dataclass(frozen=True)
class DatasetInspection:
    path: Path
    sha256: str
    row_count: int
    covered_tickers: int | None
    columns: tuple[str, ...]
    tickers: frozenset[str] | None = None

    def to_manifest_entry(self, *, snapshot_id: str, as_of: str) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "present": True,
            "snapshot_id": snapshot_id,
            "as_of": as_of,
            "sha256": self.sha256,
            "row_count": self.row_count,
            "input_role": EXTERNAL_INPUT_ROLE,
            "columns": list(self.columns),
        }
        if self.covered_tickers is not None:
            payload["covered_tickers"] = self.covered_tickers
        return payload


def _resolve_inside(bundle_dir: Path, relative_path: object) -> Path:
    raw = str(relative_path or "").strip()
    if not raw:
        raise ProductionBundleError("dataset path is required")
    candidate = (bundle_dir / raw).resolve()
    root = bundle_dir.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ProductionBundleError(f"dataset path escapes bundle directory: {raw}") from error
    if not candidate.is_file():
        raise ProductionBundleError(f"dataset file is missing: {raw}")
    return candidate


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalized_ticker(value: object) -> str | None:
    ticker = str(value or "").strip().upper()
    if not ticker:
        return None
    if not is_valid_hose_ticker(ticker):
        raise ProductionBundleError(f"invalid ticker in bundle: {ticker!r}")
    return ticker


def inspect_csv_dataset(
    path: Path,
    *,
    dataset_name: str | None = None,
    ticker_column: str | None = None,
    exchange_column: str | None = None,
    expected_exchange: str | None = None,
) -> DatasetInspection:
    row_count = 0
    tickers: set[str] | None = set() if ticker_column else None
    expected_exchange_normalized = str(expected_exchange or "").strip().upper() or None
    if expected_exchange_normalized and not exchange_column:
        raise ProductionBundleError(
            f"exchange_column is required when expected_exchange is set for {path.name}"
        )

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ProductionBundleError(f"CSV header is missing: {path.name}")
        try:
            columns = validate_external_raw_columns(dataset_name or path.stem, reader.fieldnames)
        except ExternalDerivedDataError as error:
            raise ProductionBundleError(str(error)) from error
        if ticker_column and ticker_column not in reader.fieldnames:
            raise ProductionBundleError(
                f"ticker column {ticker_column!r} is missing from {path.name}"
            )
        if exchange_column and exchange_column not in reader.fieldnames:
            raise ProductionBundleError(
                f"exchange column {exchange_column!r} is missing from {path.name}"
            )

        for row in reader:
            row_count += 1
            if tickers is not None:
                ticker = _normalized_ticker(row.get(ticker_column or ""))
                if ticker is None:
                    raise ProductionBundleError(
                        f"blank ticker at row {row_count + 1} in {path.name}"
                    )
                tickers.add(ticker)
            if expected_exchange_normalized:
                exchange = str(row.get(exchange_column or "") or "").strip().upper()
                if exchange != expected_exchange_normalized:
                    raise ProductionBundleError(
                        f"non-{expected_exchange_normalized} row in {path.name} at row {row_count + 1}: {exchange or '<blank>'}"
                    )

    frozen_tickers = frozenset(tickers) if tickers is not None else None
    return DatasetInspection(
        path=path,
        sha256=_sha256(path),
        row_count=row_count,
        covered_tickers=len(frozen_tickers) if frozen_tickers is not None else None,
        columns=columns,
        tickers=frozen_tickers,
    )


def _dataset_as_of(spec: Mapping[str, Any], snapshot_as_of: str) -> str:
    value = str(spec.get("as_of") or snapshot_as_of).strip()
    if not value:
        raise ProductionBundleError("dataset as_of is required")
    return value


def build_manifest_from_descriptor(
    bundle_dir: str | Path,
    descriptor: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(bundle_dir).resolve()
    if not root.is_dir():
        raise ProductionBundleError(f"bundle directory is missing: {root}")

    contract_version = str(descriptor.get("contract_version") or "").strip()
    if contract_version != CONTRACT_VERSION:
        raise ProductionBundleError(
            f"descriptor contract_version must be {CONTRACT_VERSION!r}"
        )

    snapshot_raw = descriptor.get("snapshot")
    rights_raw = descriptor.get("rights")
    active_status_raw = descriptor.get("active_status")
    dataset_specs = descriptor.get("datasets")
    if not isinstance(snapshot_raw, Mapping):
        raise ProductionBundleError("snapshot object is required")
    if not isinstance(rights_raw, Mapping):
        raise ProductionBundleError("rights object is required")
    if not isinstance(active_status_raw, Mapping):
        raise ProductionBundleError("active_status object is required")
    if not isinstance(dataset_specs, Mapping):
        raise ProductionBundleError("datasets object is required")

    snapshot = dict(snapshot_raw)
    snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
    snapshot_as_of = str(snapshot.get("as_of") or "").strip()
    snapshot_exchange = str(snapshot.get("exchange") or "").strip().upper()
    if not snapshot_id:
        raise ProductionBundleError("snapshot.snapshot_id is required")
    if not snapshot_as_of:
        raise ProductionBundleError("snapshot.as_of is required")
    if snapshot_exchange != "HOSE":
        raise ProductionBundleError("production bundle exchange must be HOSE")

    datasets: dict[str, Any] = {}
    inspections: dict[str, DatasetInspection] = {}
    for name in REQUIRED_DATASETS:
        raw_spec = dataset_specs.get(name)
        if not isinstance(raw_spec, Mapping):
            raise ProductionBundleError(f"dataset descriptor is missing: {name}")
        path = _resolve_inside(root, raw_spec.get("path"))
        format_name = str(raw_spec.get("format") or path.suffix.lstrip(".")).strip().lower()
        if format_name != "csv":
            raise ProductionBundleError(
                f"unsupported dataset format for {name}: {format_name or '<blank>'}; only CSV is accepted in V1"
            )
        ticker_column = str(raw_spec.get("ticker_column") or "").strip() or None
        if name in COVERAGE_DATASETS and not ticker_column:
            raise ProductionBundleError(f"ticker_column is required for {name}")

        exchange_column = str(raw_spec.get("exchange_column") or "").strip() or None
        expected_exchange = None
        if name == "security_master":
            if not exchange_column:
                raise ProductionBundleError("exchange_column is required for security_master")
            expected_exchange = snapshot_exchange
        elif exchange_column:
            expected_exchange = snapshot_exchange

        inspection = inspect_csv_dataset(
            path,
            dataset_name=name,
            ticker_column=ticker_column,
            exchange_column=exchange_column,
            expected_exchange=expected_exchange,
        )
        inspections[name] = inspection
        datasets[name] = inspection.to_manifest_entry(
            snapshot_id=snapshot_id,
            as_of=_dataset_as_of(raw_spec, snapshot_as_of),
        )

    universe_tickers = inspections["security_master"].tickers or frozenset()
    for name in ("ohlcv", "fundamentals"):
        dataset_tickers = inspections[name].tickers or frozenset()
        outside = sorted(dataset_tickers - universe_tickers)
        if outside:
            preview = ", ".join(outside[:5])
            raise ProductionBundleError(
                f"{name} contains ticker outside HOSE security_master: {preview}"
            )

    return {
        "contract_version": CONTRACT_VERSION,
        "snapshot": snapshot,
        "rights": dict(rights_raw),
        "active_status": dict(active_status_raw),
        "computation": computation_provenance(),
        "datasets": datasets,
    }


def load_descriptor(path: str | Path) -> Mapping[str, Any]:
    descriptor_path = Path(path)
    payload = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ProductionBundleError("bundle descriptor must be a JSON object")
    return payload


def write_manifest(path: str | Path, payload: Mapping[str, Any]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
