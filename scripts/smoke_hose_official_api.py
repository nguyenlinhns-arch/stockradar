from __future__ import annotations

from datetime import date, timedelta
import json
import requests
from urllib.parse import urlencode

HEADERS = {
    'User-Agent': 'StockRadar-Internal-Research/1.0',
    'Accept': 'application/json, text/plain, */*',
    'Origin': 'https://www.hsx.vn',
    'Referer': 'https://www.hsx.vn/',
}
LISTING = 'https://api.hsx.vn/l/api/v1/1'
NEWS = 'https://api.hsx.vn/n/api/v1/1'


def get(url):
    r = requests.get(url, headers=HEADERS, timeout=12)
    return {'status': r.status_code, 'bytes': len(r.content), 'json': r.json() if r.ok else None}


def main():
    end = date.today(); start = end - timedelta(days=120)
    out = {}
    for ticker in ['MBB','HPG','ACB']:
        lookup = get(f"{LISTING}/securities/stock?{urlencode({'code':ticker})}")
        data = (lookup.get('json') or {}).get('data') or {}
        items = data.get('list') or []
        sid = next((int(x.get('id') or 0) for x in items if str(x.get('code') or '').upper()==ticker), 0)
        row = {'lookup_status': lookup['status'], 'lookup_bytes': lookup['bytes'], 'security_id': sid}
        if sid:
            q=urlencode({'pageIndex':1,'pageSize':20,'startDate':start.isoformat(),'endDate':end.isoformat()})
            news=get(f'{NEWS}/news/securities/{sid}/1?{q}')
            ndata=(news.get('json') or {}).get('data') or {}
            paging=ndata.get('paging') or {}
            lst=ndata.get('list') or []
            row.update({'news_status':news['status'],'news_bytes':news['bytes'],'rows_page1':len(lst),'total_pages':paging.get('totalPages'),'sample_titles':[x.get('title') for x in lst[:3]]})
        out[ticker]=row
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
