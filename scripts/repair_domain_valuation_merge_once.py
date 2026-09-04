from pathlib import Path

TARGET = Path("scripts/build_domain_fundamental_valuation_v4.py")
text = TARGET.read_text(encoding="utf-8")

old = ".merge(val[['ticker','fv_pe_bootstrap','fv_pb_bootstrap','fair_value_bootstrap_bear','fair_value_bootstrap_base','fair_value_bootstrap_bull','valuation_model_status']],on='ticker',how='left')"
new = ""

if old not in text:
    if "scanner missing canonical valuation columns" in text:
        print("Domain V4 valuation merge already repaired")
        raise SystemExit(0)
    raise SystemExit("expected duplicate valuation-merge anchor not found; refusing broad patch")

validation_anchor = "if len(scanner)!=EXPECTED_HOSE or scanner.ticker.nunique()!=EXPECTED_HOSE: raise ValueError('scanner universe !=405')\n"
validation = (
    validation_anchor
    + "    required_val_cols=['fv_pe_bootstrap','fv_pb_bootstrap','fair_value_bootstrap_bear','fair_value_bootstrap_base','fair_value_bootstrap_bull','valuation_model_status']\n"
    + "    missing_val_cols=[c for c in required_val_cols if c not in scanner.columns]\n"
    + "    if missing_val_cols: raise ValueError('scanner missing canonical valuation columns: '+','.join(missing_val_cols))\n"
)
if validation_anchor not in text:
    raise SystemExit("scanner validation anchor not found; refusing broad patch")

text = text.replace(validation_anchor, validation, 1)
text = text.replace(old, new, 1)
TARGET.write_text(text, encoding="utf-8")
print("removed duplicate valuation merge and asserted canonical scanner valuation columns")

# Trigger marker: exact canonical valuation-field collision repair.
