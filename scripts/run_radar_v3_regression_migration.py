#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

import migrate_radar_v3_regressions as migration


def robust_replace_function(path: Path, name: str, next_name: str, body: str) -> None:
    source = path.read_text(encoding="utf-8")
    start_match = re.search(rf"(?m)^    def {re.escape(name)}\(self\)(?:\s*->\s*[^:]+)?\s*:\s*$", source)
    if not start_match:
        raise RuntimeError(f"Cannot locate start function {name} in {path}")
    end_match = re.search(rf"(?m)^    def {re.escape(next_name)}\(self\)(?:\s*->\s*[^:]+)?\s*:\s*$", source[start_match.end():])
    if not end_match:
        raise RuntimeError(f"Cannot locate next function {next_name} in {path}")
    start = start_match.start()
    end = start_match.end() + end_match.start()
    source = source[:start] + body.rstrip() + "\n\n" + source[end:]
    path.write_text(source, encoding="utf-8")


migration.replace_function = robust_replace_function
migration.main()
