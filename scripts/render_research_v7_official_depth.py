from __future__ import annotations

from pathlib import Path

SOURCE = Path('.github/workflows/research-decision-v7.yml')
OUTPUT = Path('docs/research-decision-v7-official-depth-rendered.yml')
text = SOURCE.read_text(encoding='utf-8')

anchor = '''      - name: Resolve authoritative corporate-action coverage\n'''
insert = '''      - name: Download latest deep official HOSE disclosure artifact when available\n        env:\n          GH_TOKEN: ${{ github.token }}\n        shell: bash\n        run: |\n          set -euo pipefail\n          mkdir -p artifacts/hose-official-depth\n          id="$(gh api "/repos/${GITHUB_REPOSITORY}/actions/artifacts?name=stockradar-hose-official-disclosures-depth-v1&per_page=100" --jq '.artifacts | map(select(.expired == false)) | sort_by(.created_at) | reverse | .[0].id // empty')"\n          if [ -n "$id" ]; then\n            gh api "/repos/${GITHUB_REPOSITORY}/actions/artifacts/${id}/zip" > /tmp/hose-official-depth.zip\n            unzip -q -o /tmp/hose-official-depth.zip -d artifacts/hose-official-depth\n          else\n            echo 'Deep official HOSE disclosure artifact unavailable; official catalyst source remains fail-closed.'\n          fi\n\n      - name: Merge realtime and deep official HOSE disclosures\n        shell: bash\n        run: |\n          set -euo pipefail\n          mkdir -p artifacts/hose-official-merged\n          realtime_csv="$(find artifacts/hose-official -name 'hose_official_disclosures_history.csv' -print -quit || true)"\n          realtime_manifest="$(find artifacts/hose-official -name 'hose_official_disclosures_manifest.json' -print -quit || true)"\n          deep_csv="$(find artifacts/hose-official-depth -name 'hose_official_disclosures_history.csv' -print -quit || true)"\n          deep_manifest="$(find artifacts/hose-official-depth -name 'hose_official_disclosures_manifest.json' -print -quit || true)"\n          args=(\n            --universe artifacts/market/security_master.csv\n            --output artifacts/hose-official-merged/hose_official_disclosures_history.csv\n            --manifest artifacts/hose-official-merged/hose_official_disclosures_manifest.json\n          )\n          if [ -n "$realtime_csv" ]; then args+=(--realtime-history "$realtime_csv"); fi\n          if [ -n "$realtime_manifest" ]; then args+=(--realtime-manifest "$realtime_manifest"); fi\n          if [ -n "$deep_csv" ]; then args+=(--deep-history "$deep_csv"); fi\n          if [ -n "$deep_manifest" ]; then args+=(--deep-manifest "$deep_manifest"); fi\n          python scripts/merge_hose_official_disclosures_v1.py "${args[@]}"\n\n'''
if 'Download latest deep official HOSE disclosure artifact when available' not in text:
    if anchor not in text:
        raise SystemExit('V7 authoritative CA anchor missing')
    text = text.replace(anchor, insert + anchor, 1)

old_find = '''          official_csv="$(find artifacts/hose-official -name 'hose_official_disclosures_history.csv' -print -quit || true)"\n          official_manifest="$(find artifacts/hose-official -name 'hose_official_disclosures_manifest.json' -print -quit || true)"\n'''
new_find = '''          official_csv="artifacts/hose-official-merged/hose_official_disclosures_history.csv"\n          official_manifest="artifacts/hose-official-merged/hose_official_disclosures_manifest.json"\n'''
if old_find in text:
    text = text.replace(old_find, new_find, 1)
elif new_find not in text:
    raise SystemExit('Catalyst V3 official-source locator anchor missing')

old_paths = '''      - 'scripts/build_catalyst_layer_v3.py'\n'''
new_paths = '''      - 'scripts/build_catalyst_layer_v3.py'\n      - 'scripts/merge_hose_official_disclosures_v1.py'\n'''
if 'scripts/merge_hose_official_disclosures_v1.py' not in text:
    if old_paths not in text:
        raise SystemExit('V7 trigger path anchor missing')
    text = text.replace(old_paths, new_paths, 1)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_text(text, encoding='utf-8')
print(OUTPUT)
