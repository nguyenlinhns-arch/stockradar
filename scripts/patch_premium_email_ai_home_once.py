from pathlib import Path

path = Path('scripts/apply_premium_email_product_v1.py')
text = path.read_text(encoding='utf-8')
old = '''def transform_home(source: str) -> str:
    marker = '          </div>\\n          <aside class="home-premium-buybox">'
'''
new = '''def transform_home(source: str) -> str:
    if "data-stockradar-ai-center" in source:
        return inject_css(source)
    marker = '          </div>\\n          <aside class="home-premium-buybox">'
'''
if old in text:
    text = text.replace(old, new, 1)
elif 'if "data-stockradar-ai-center" in source:' not in text:
    raise SystemExit('Premium email transform_home target not found')
path.write_text(text, encoding='utf-8')

for helper in (
    '.github/workflows/patch-premium-email-ai-home-once.yml',
    'scripts/patch_premium_email_ai_home_once.py',
):
    Path(helper).unlink(missing_ok=True)
