from pathlib import Path

TARGET = Path("scripts/build_internal_scanner_feed_v2.py")
OLD = '    source_ms = pd.to_numeric(out.get("source_time_ms"), errors="coerce").dropna()\n'
NEW = (
    '    source_time_series = (\n'
    '        out["source_time_ms"]\n'
    '        if "source_time_ms" in out.columns\n'
    '        else pd.Series(np.nan, index=out.index, dtype="float64")\n'
    '    )\n'
    '    source_ms = pd.to_numeric(source_time_series, errors="coerce").dropna()\n'
)

text = TARGET.read_text(encoding="utf-8")
if OLD in text:
    TARGET.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    print("patched scanner source_time_ms fallback")
elif "source_time_series = (" in text:
    print("scanner source_time_ms fallback already patched")
else:
    raise SystemExit("expected scanner source_time_ms line not found; refusing broad rewrite")
