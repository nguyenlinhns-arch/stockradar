"""Pages scheduled build: use a completed same-day post-close collector artifact.

No mailbox access or invented events. Only update prices following the immutable evidenced ledger.
"""
import io
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
import os
import subprocess
import sys
import zipfile
import pandas as pd


def eligible_run(run, today):
    started = datetime.fromisoformat(run['run_started_at'].replace('Z', '+00:00')).astimezone(timezone(timedelta(hours=7)))
    return (run.get('conclusion') == 'success' and run.get('head_branch') == 'main'
            and run.get('path') == '.github/workflows/hose-data-bootstrap.yml'
            and run.get('event') in {'schedule', 'workflow_dispatch', 'push'}
            and started.date() == today and (started.hour, started.minute) >= (15, 25))


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    today = datetime.now(timezone(timedelta(hours=7))).date()
    def gh(*args):
        return subprocess.check_output(['gh', *args])
    artifacts = json.loads(gh('api', f'/repos/{repo}/actions/artifacts?name=stockradar-hose-market-bootstrap&per_page=100'))['artifacts']
    selected = None
    for artifact in sorted(artifacts, key=lambda a: a['created_at'], reverse=True):
        if artifact['expired']:
            continue
        run = json.loads(gh('api', f"/repos/{repo}/actions/runs/{artifact['workflow_run']['id']}"))
        if eligible_run(run, today):
            selected = artifact
            break
    if not selected:
        raise RuntimeError('No successful same-day post-close market run; refusing a current-day history update')
    archive = zipfile.ZipFile(io.BytesIO(gh('api', f"/repos/{repo}/actions/artifacts/{selected['id']}/zip")))
    paths = [name for name in archive.namelist() if Path(name).name == 'ohlcv.csv']
    if len(paths) != 1:
        raise RuntimeError('Ambiguous OHLCV artifact')
    output = Path('artifacts/eod-history')
    output.mkdir(parents=True, exist_ok=True)
    history = output / 'ohlcv.csv'
    history.write_bytes(archive.read(paths[0]))
    frame = pd.read_csv(history)
    as_of = pd.to_datetime(frame.timestamp, errors='raise').max().date()
    if as_of > today or (today - as_of).days > 4:
        raise RuntimeError('Future or stale EOD observation')
    subprocess.run([sys.executable, 'scripts/build_recommendation_history.py', '--history', str(history),
                    '--as-of', as_of.isoformat(), '--skip-replay'], check=True)
    print(json.dumps({'as_of_date': str(as_of), 'source_run_id': selected['workflow_run']['id'], 'mode': 'VERIFIED_EMAIL_HISTORY'}))


if __name__ == '__main__':
    main()
