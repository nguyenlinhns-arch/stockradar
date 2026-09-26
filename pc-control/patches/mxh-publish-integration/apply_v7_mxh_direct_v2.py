from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

V1_ADAPTER_SHA256 = "a5ffaa84528d0d174b91a60afb018a423f3f3c34"
V1_CONTRACT_SHA256 = "aad30bcd070ceb3cf16053543a8a916c406d2595"
V2_ADAPTER_SENTINEL = "def schedule_exact_title("
V2_CONTRACT_SENTINEL = '"schedule_exact_title"'


class UpgradeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    tmp = path.with_suffix(path.suffix + ".new")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def write_receipt(receipt: Path, payload: dict) -> None:
    receipt.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(receipt, json.dumps(payload, ensure_ascii=False, indent=2))


def upgrade(source_root: Path, package_root: Path) -> Path:
    source_root = source_root.resolve()
    package_root = package_root.resolve()
    semantic = source_root / "agent" / "semantic_host.py"
    connector = source_root / "agent" / "src" / "connectors" / "mxh"
    adapter = connector / "adapter.py"
    contract = connector / "contract.py"
    receipt = source_root / ".mxh-integration" / "V7_MXH_DIRECT_V2_RECEIPT.json"

    for path in (semantic, adapter, contract):
        if not path.is_file():
            raise UpgradeError(f"SOURCE_MISSING:{path.relative_to(source_root)}")

    semantic_text = semantic.read_text(encoding="utf-8")
    adapter_text = adapter.read_text(encoding="utf-8")
    contract_text = contract.read_text(encoding="utf-8")

    if "V7_MXH_PUBLISH_INTEGRATION" not in semantic_text or "MXH_V1:" not in semantic_text:
        raise UpgradeError("V1_SEMANTIC_BRIDGE_NOT_INSTALLED")

    if V2_ADAPTER_SENTINEL in adapter_text and V2_CONTRACT_SENTINEL in contract_text:
        write_receipt(receipt, {
            "schema": "thaylinh.v7.mxh-direct.v2",
            "status": "ALREADY_V2",
            "source_root": str(source_root),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        return receipt

    if V2_ADAPTER_SENTINEL in adapter_text or V2_CONTRACT_SENTINEL in contract_text:
        raise UpgradeError("PARTIAL_V2_INTEGRATION_DETECTED")

    if sha256(adapter) != V1_ADAPTER_SHA256:
        raise UpgradeError(f"V1_ADAPTER_SHA_MISMATCH:{sha256(adapter)}")
    if sha256(contract) != V1_CONTRACT_SHA256:
        raise UpgradeError(f"V1_CONTRACT_SHA_MISMATCH:{sha256(contract)}")

    package_connector = package_root / "connector"
    package_adapter = package_connector / "adapter.py"
    package_contract = package_connector / "contract.py"
    for path in (package_adapter, package_contract):
        if not path.is_file():
            raise UpgradeError(f"PACKAGE_MISSING:{path.name}")
        compile(path.read_text(encoding="utf-8"), str(path), "exec")

    package_adapter_text = package_adapter.read_text(encoding="utf-8")
    package_contract_text = package_contract.read_text(encoding="utf-8")
    if V2_ADAPTER_SENTINEL not in package_adapter_text or V2_CONTRACT_SENTINEL not in package_contract_text:
        raise UpgradeError("PACKAGE_NOT_V2")

    backup = source_root / ".mxh-integration" / (
        "backup-direct-v2-" + datetime.now().strftime("%Y%m%d-%H%M%S")
    )
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(adapter, backup / "adapter.py")
    shutil.copy2(contract, backup / "contract.py")

    try:
        shutil.copy2(package_adapter, adapter)
        shutil.copy2(package_contract, contract)
        compile(adapter.read_text(encoding="utf-8"), str(adapter), "exec")
        compile(contract.read_text(encoding="utf-8"), str(contract), "exec")
    except Exception:
        shutil.copy2(backup / "adapter.py", adapter)
        shutil.copy2(backup / "contract.py", contract)
        raise UpgradeError("V2_COMPILE_FAILED_ROLLED_BACK")

    write_receipt(receipt, {
        "schema": "thaylinh.v7.mxh-direct.v2",
        "status": "PASS",
        "source_root": str(source_root),
        "backup_root": str(backup),
        "changed": [
            "agent/src/connectors/mxh/adapter.py",
            "agent/src/connectors/mxh/contract.py",
        ],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    args = parser.parse_args()
    try:
        receipt = upgrade(
            Path(args.source_root),
            Path(__file__).resolve().parent,
        )
    except UpgradeError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({"ok": True, "receipt": str(receipt)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
