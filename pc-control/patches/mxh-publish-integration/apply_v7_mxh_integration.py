from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EXPECTED_SOURCE_SHA256 = {
    "agent/semantic_host.py": "3287ac65b7f34f0a423f713f919a3dca3ade7a3fd9611b863c8dcc67c89f251b",
    "desktop/MainWindow.xaml": "99a382c15fd551859a01bb2e99150ba56d76fa30ad798906f7812312c518473b",
    "desktop/MainWindow.xaml.cs": "ce463dd2c8490a0014559155e12c3b94e3ffb36c83b27dccd49c346ae2b74729",
}

PARSER_ANCHOR = "\ndef permission(spec,cfg):"
ROUTE_ANCHOR = "            bridge=parse_capcut_bridge(payload.get('goal'))"
XAML_ANCHOR = '        <TabItem Header="Cài đặt">'
CS_ANCHOR = "    void LoadSettings()"

PARSER_SENTINEL = "MXH_BRIDGE_PREFIX='MXH_V1:'"
ROUTE_SENTINEL = "mxh_bridge=parse_mxh_bridge(payload.get('goal'))"
XAML_SENTINEL = 'Header="MXH PUBLISH"'
CS_SENTINEL = "async Task<JsonObject> MxhCall("


class PatchError(RuntimeError):
    pass


@dataclass
class PatchResult:
    changed: list[str]
    already_integrated: bool
    build_ok: bool | None
    receipt: Path


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


def read_fragment(base: Path, relative: str) -> str:
    path = base / "fragments" / relative
    if not path.is_file():
        raise PatchError(f"FRAGMENT_MISSING:{path}")
    return path.read_text(encoding="utf-8")


def all_integrated(root: Path) -> bool:
    targets = {
        root / "agent" / "semantic_host.py": (PARSER_SENTINEL, ROUTE_SENTINEL),
        root / "desktop" / "MainWindow.xaml": (XAML_SENTINEL,),
        root / "desktop" / "MainWindow.xaml.cs": (CS_SENTINEL,),
    }
    for path, sentinels in targets.items():
        if not path.is_file():
            return False
        text = path.read_text(encoding="utf-8")
        if any(sentinel not in text for sentinel in sentinels):
            return False
    connector = root / "agent" / "src" / "connectors" / "mxh"
    return all((connector / name).is_file() for name in ("__init__.py", "adapter.py", "contract.py"))


def partial_integration(root: Path) -> bool:
    paths = [
        root / "agent" / "semantic_host.py",
        root / "desktop" / "MainWindow.xaml",
        root / "desktop" / "MainWindow.xaml.cs",
    ]
    needles = [PARSER_SENTINEL, ROUTE_SENTINEL, XAML_SENTINEL, CS_SENTINEL]
    found = 0
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        found += sum(needle in text for needle in needles)
    connector = root / "agent" / "src" / "connectors" / "mxh"
    found += sum((connector / name).exists() for name in ("__init__.py", "adapter.py", "contract.py"))
    return found > 0 and not all_integrated(root)


def check_source(root: Path) -> None:
    for relative, expected in EXPECTED_SOURCE_SHA256.items():
        path = root / relative
        if not path.is_file():
            raise PatchError(f"SOURCE_MISSING:{relative}")
        actual = sha256(path)
        if actual != expected:
            raise PatchError(f"SOURCE_SHA_MISMATCH:{relative}:{actual}")


def insert_once(text: str, *, sentinel: str, anchor: str, fragment: str, before: bool = True) -> str:
    if sentinel in text:
        return text
    index = text.find(anchor)
    if index < 0:
        raise PatchError(f"ANCHOR_NOT_FOUND:{anchor[:80]}")
    if before:
        return text[:index] + fragment.rstrip() + "\n\n" + text[index:]
    end = index + len(anchor)
    return text[:end] + "\n" + fragment.rstrip() + text[end:]


def apply_patch(source_root: Path, package_root: Path, *, run_build: bool = True) -> PatchResult:
    source_root = source_root.resolve()
    package_root = package_root.resolve()
    receipt_dir = source_root / ".mxh-integration"
    receipt_dir.mkdir(parents=True, exist_ok=True)
    receipt = receipt_dir / "V7_MXH_INTEGRATION_RECEIPT.json"

    if all_integrated(source_root):
        payload = {
            "schema": "thaylinh.v7.mxh-integration.v1",
            "status": "ALREADY_INTEGRATED",
            "source_root": str(source_root),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_write(receipt, json.dumps(payload, ensure_ascii=False, indent=2))
        return PatchResult([], True, None, receipt)

    if partial_integration(source_root):
        raise PatchError("PARTIAL_INTEGRATION_DETECTED")

    check_source(source_root)

    semantic = source_root / "agent" / "semantic_host.py"
    xaml = source_root / "desktop" / "MainWindow.xaml"
    cs = source_root / "desktop" / "MainWindow.xaml.cs"

    backup_root = receipt_dir / ("backup-" + datetime.now().strftime("%Y%m%d-%H%M%S"))
    for path in (semantic, xaml, cs):
        dest = backup_root / path.relative_to(source_root)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)

    semantic_text = semantic.read_text(encoding="utf-8")
    semantic_text = insert_once(
        semantic_text,
        sentinel=PARSER_SENTINEL,
        anchor=PARSER_ANCHOR,
        fragment=read_fragment(package_root, "semantic_host_parser.py"),
    )
    semantic_text = insert_once(
        semantic_text,
        sentinel=ROUTE_SENTINEL,
        anchor=ROUTE_ANCHOR,
        fragment=read_fragment(package_root, "semantic_host_route.py"),
    )

    xaml_text = insert_once(
        xaml.read_text(encoding="utf-8"),
        sentinel=XAML_SENTINEL,
        anchor=XAML_ANCHOR,
        fragment=read_fragment(package_root, "MainWindow.MXH.xaml"),
    )
    cs_text = insert_once(
        cs.read_text(encoding="utf-8"),
        sentinel=CS_SENTINEL,
        anchor=CS_ANCHOR,
        fragment=read_fragment(package_root, "MainWindow.MXH.cs"),
    )

    # Python compile gate before any source replacement.
    compile(semantic_text, str(semantic), "exec")

    connector_src = package_root / "connector"
    for name in ("__init__.py", "adapter.py", "contract.py"):
        compile((connector_src / name).read_text(encoding="utf-8"), name, "exec")

    atomic_write(semantic, semantic_text)
    atomic_write(xaml, xaml_text)
    atomic_write(cs, cs_text)

    connector_dst = source_root / "agent" / "src" / "connectors" / "mxh"
    connector_dst.mkdir(parents=True, exist_ok=True)
    for name in ("__init__.py", "adapter.py", "contract.py"):
        shutil.copy2(connector_src / name, connector_dst / name)

    changed = [
        "agent/semantic_host.py",
        "agent/src/connectors/mxh/__init__.py",
        "agent/src/connectors/mxh/adapter.py",
        "agent/src/connectors/mxh/contract.py",
        "desktop/MainWindow.xaml",
        "desktop/MainWindow.xaml.cs",
    ]

    build_ok: bool | None = None
    build_output = ""
    if run_build:
        project = source_root / "desktop" / "ThayLinh-PC-Control.csproj"
        if not project.is_file():
            raise PatchError("DESKTOP_CSPROJ_MISSING")
        completed = subprocess.run(
            ["dotnet", "build", str(project), "-c", "Release", "--no-restore"],
            cwd=str(source_root),
            text=True,
            capture_output=True,
            timeout=180,
            check=False,
        )
        build_ok = completed.returncode == 0
        build_output = (completed.stdout + "\n" + completed.stderr)[-12000:]
        if not build_ok:
            # Fail closed: restore original source and remove only newly added connector dir.
            for path in (semantic, xaml, cs):
                src = backup_root / path.relative_to(source_root)
                shutil.copy2(src, path)
            if connector_dst.exists():
                shutil.rmtree(connector_dst)
            payload = {
                "schema": "thaylinh.v7.mxh-integration.v1",
                "status": "BUILD_FAILED_ROLLED_BACK",
                "source_root": str(source_root),
                "build_output": build_output,
                "completed_at": datetime.now(timezone.utc).isoformat(),
            }
            atomic_write(receipt, json.dumps(payload, ensure_ascii=False, indent=2))
            raise PatchError("BUILD_FAILED_ROLLED_BACK")

    payload = {
        "schema": "thaylinh.v7.mxh-integration.v1",
        "status": "PASS",
        "source_root": str(source_root),
        "changed": changed,
        "backup_root": str(backup_root),
        "build_ok": build_ok,
        "build_output_tail": build_output,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    atomic_write(receipt, json.dumps(payload, ensure_ascii=False, indent=2))
    return PatchResult(changed, False, build_ok, receipt)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--no-build", action="store_true")
    args = parser.parse_args()
    package_root = Path(__file__).resolve().parent
    try:
        result = apply_patch(Path(args.source_root), package_root, run_build=not args.no_build)
    except PatchError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps({
        "ok": True,
        "already_integrated": result.already_integrated,
        "changed": result.changed,
        "build_ok": result.build_ok,
        "receipt": str(result.receipt),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
