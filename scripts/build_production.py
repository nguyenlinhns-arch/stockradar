"""Cross-platform reproduction of the production Pages transforms and checks."""
import os
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
os.environ['PYTHONIOENCODING']='utf-8'
os.environ.update(STOCKRADAR_ENABLE_AUTH='1',STOCKRADAR_AUTH_EMAIL_READY='0',
 STOCKRADAR_SUPABASE_URL='https://xamviatbxufjlpiwhebb.supabase.co',
 STOCKRADAR_SUPABASE_PUBLISHABLE_KEY='sb_publishable_Ne0TfBw0Iu732yrhqRcdIA_hPGxYDAK',
 STOCKRADAR_PRODUCT_EMAIL_READY='0',STOCKRADAR_CHECKOUT_READY='0')

def run(*args):
 subprocess.run([sys.executable,*args],check=True)

run('-m','engine.cli','build-public')
run('scripts/fail_close_public_ticker_seed.py','website/public/data/ticker-universe.json')
run('scripts/build_pages.py','--output','.pages-site')
steps='''inject_public_ux inject_home_radar_polish upgrade_home_radar_operational apply_buyer_readiness
redesign_home_value_block apply_conversion_v3 link_premium_sample patch_conversion_funnel_v4
apply_ai_first_premium_email strip_public_methods inject_ai_assistant enforce_registration_plan_ctas
enforce_checkout_public_bank_info enforce_ai_registration_ctas verify_pages_auth verify_ai_first_product
verify_ai_assistant normalize_commercial_pricing normalize_commercial_plans_preflight_v1
normalize_commercial_home_preflight_v1 apply_commercial_surface_v1 apply_commercial_surface_v2
fix_commercial_auth_headings apply_commercial_runtime_v2 apply_commercial_support_v1
optimize_home_asset_budget_v1 optimize_conversion_asset_budget_v1 apply_commercial_cleanup_v3
optimize_dashboard_asset_budget_v1 apply_public_seo_v1 verify_commercial_density_v1'''.split()
for step in steps:
 run('scripts/'+step+'.py','.pages-site')
print('Production build and artifact contracts: PASS')
