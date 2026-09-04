#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def fail_close(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    reference = dict(payload.get("internal_reference", {}))
    result = {
        "schema_version": str(payload.get("schema_version", "2.1.2")),
        "snapshot_id": payload.get("snapshot_id") or reference.get("snapshot_id") or "UNAVAILABLE",
        "as_of": payload.get("as_of") or reference.get("as_of"),
        "full_universe": False,
        "data_grade": "REFERENCE_ONLY",
        "data_status": "BLOCKED_DATA_GATE",
        "public_scope": "FAIL_CLOSED_NO_PUBLIC_TICKER_SEED",
        "selection_label": "Không công bố shortlist cố định",
        "selection_kind": "NONE_FAIL_CLOSED",
        "internal_reference": reference,
        "items": [],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Remove reference/demo ticker seed from the public artifact until the full production master is approved.")
    parser.add_argument("path", nargs="?", default="website/public/data/ticker-universe.json", type=Path)
    args = parser.parse_args()
    result = fail_close(args.path)
    print(json.dumps({"status": result["data_status"], "public_items": len(result["items"]), "scope": result["public_scope"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
