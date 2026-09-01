#!/usr/bin/env python3
"""Build the static StockRadar site that GitHub Pages can publish."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEBSITE = ROOT / "website"
DEFAULT_OUTPUT = ROOT / ".pages-site"
EXCLUDED_NAMES = {"server.py", "__pycache__"}


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
        output / "track-record" / "index.html",
        output / "nganh" / "index.html",
        output / "phan-tich" / "index.html",
        output / "khuyen-nghi" / "index.html",
        output / "hieu-qua" / "index.html",
        output / "co-phieu" / "demo1" / "index.html",
        output / "email" / "index.html",
        output / "theo-doi" / "index.html",
        output / "tai-khoan" / "index.html",
        output / "kien-thuc" / "index.html",
        output / "kien-thuc" / "quy-trinh-stockradar" / "index.html",
        output / "kien-thuc" / "quan-tri-rui-ro" / "index.html",
    ]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(f"Missing Pages assets: {missing}")
    if (output / "server.py").exists():
        raise RuntimeError("The Python server must not be included in GitHub Pages")


if __name__ == "__main__":
    build(parse_args().output)
