from pathlib import Path

TARGET = Path("scripts/build_domain_fundamental_valuation_v4.py")
text = TARGET.read_text(encoding="utf-8")
old = ".merge(sector[['sector','sector_strength_score','sector_regime']],left_on='sector_v4',right_on='sector',how='left').drop(columns=['sector'])"
new = ".merge(sector.rename(columns={'sector':'sector_join_v4'})[['sector_join_v4','sector_strength_score','sector_regime']],left_on='sector_v4',right_on='sector_join_v4',how='left').drop(columns=['sector_join_v4'])"
if old not in text:
    if new in text:
        print("domain V4 sector join already repaired")
        raise SystemExit(0)
    raise SystemExit("expected domain V4 sector-merge anchor not found; refusing broad patch")
text = text.replace(old, new, 1)
TARGET.write_text(text, encoding="utf-8")
print("patched domain V4 sector join collision safely")
