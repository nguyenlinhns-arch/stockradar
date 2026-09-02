#!/usr/bin/env python3
"""Build the static StockRadar site that GitHub Pages can publish."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
DEFAULT_OUTPUT = ROOT / ".pages-site"
EXCLUDED_NAMES = {
    "server.py",
    "__pycache__",
    "kien-thuc",
    "demo1",
    "email",
    "theo-doi",
    "tai-khoan",
    "signup",
    "pro",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def validate_output(output: Path) -> Path:
    resolved = output.resolve()
    if resolved in {ROOT.resolve(), WEBSITE.resolve(), Path(resolved.anchor)}:
        raise ValueError(f"Unsafe output directory: {resolved}")
    return resolved


def ignore(directory: str, names: list[str]) -> set[str]:
    excluded = {name for name in names if name in EXCLUDED_NAMES or name.endswith(".sqlite")}
    if Path(directory).resolve() == WEBSITE.resolve() and "data" in names:
        excluded.add("data")
    return excluded


def build(output: Path) -> None:
    output = validate_output(output)
    if output.exists():
        shutil.rmtree(output)
    shutil.copytree(WEBSITE, output, ignore=ignore)

    for page in output.rglob("*.html"):
        source = page.read_text(encoding="utf-8")
        source = source.replace('data-api-mode="auto"', 'data-api-mode="disabled"')
        if 'name="robots"' not in source:
            source = source.replace(
                "<head>",
                '<head><meta name="robots" content="noindex,nofollow">',
                1,
            )
        page.write_text(source, encoding="utf-8")

    (output / ".nojekyll").write_text("", encoding="utf-8")

    required = [
        output / "index.html",
        output / "assets" / "app.js",
        output / "public" / "data" / "radar.json",
        output / "public" / "data" / "recommendations.json",
        output / "public" / "data" / "ticker-universe.json",
        output / "public" / "data" / "stock-reports.json",
        output / "public" / "data" / "today-changes.json",
        output / "public" / "data" / "recommendation-journal.json",
        output / "public" / "data" / "track-record.json",
        output / "track-record" / "index.html",
        output / "radar5" / "index.html",
        output / "breakout" / "index.html",
        output / "risk" / "index.html",
        output / "nganh" / "index.html",
        output / "phan-tich" / "index.html",
        output / "khuyen-nghi" / "index.html",
        output / "hieu-qua" / "index.html",
        output / "co-phieu" / "index.html",
        output / "kiem-tra-co-phieu" / "index.html",
        output / "thay-doi-hom-nay" / "index.html",
        output / "404.html",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing Pages assets: {missing}")
    if (output / "server.py").exists():
        raise RuntimeError("The Python server must not be included in GitHub Pages")

    public_data = sorted((output / "public" / "data").glob("*.json"))
    for path in public_data:
        json.loads(path.read_text(encoding="utf-8"))
    for path in [*public_data, output / "assets" / "app.js"]:
        source = path.read_text(encoding="utf-8").upper()
        for forbidden in ("DEMO", "MOCK", "MÔ PHỎNG", "FIXTURE"):
            if forbidden in source:
                raise RuntimeError(f"Publication-only artifact contains {forbidden}: {path}")


if __name__ == "__main__":
    build(parse_args().output)
