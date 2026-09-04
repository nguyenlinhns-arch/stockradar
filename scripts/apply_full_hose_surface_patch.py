from __future__ import annotations

from pathlib import Path


def replace(path: str, old: str, new: str) -> None:
    target = Path(path)
    text = target.read_text(encoding="utf-8")
    if new in text:
        return
    if old not in text:
        raise SystemExit(f"Patch target not found: {path}: {old[:100]!r}")
    target.write_text(text.replace(old, new, 1), encoding="utf-8")


replace(
    "engine/cli.py",
    "from engine.stockradar.ticker_lookup import TickerMaster\n",
    "from engine.stockradar.ticker_lookup import TickerMaster\nfrom engine.stockradar.ticker_symbol import is_valid_hose_ticker\n",
)
replace(
    "engine/cli.py",
    '''            if str(item.get("ticker", "")).isalpha()\n            and len(str(item.get("ticker", ""))) == 3\n            and str(item.get("ticker", "")).isupper()''',
    '''            if is_valid_hose_ticker(item.get("ticker", ""))\n            and str(item.get("ticker", "")).isupper()''',
)

replace(
    "website/assets/app.js",
    "return String(value || '').trim().toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);",
    "return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 3);",
)
replace(
    "website/assets/app.js",
    "return /^[A-Z]{3}$/.test(String(value || ''));",
    "return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(String(value || ''));",
)
replace(
    "website/assets/app.js",
    '''  function horizonCards(report) {''',
    '''  function enableAlphanumericTickerInputs() {\n    document.querySelectorAll('input[name="ticker"], #watch-ticker').forEach(input => {\n      input.setAttribute('pattern', '[A-Za-z0-9]{3}');\n      input.setAttribute('title', 'Mã HOSE gồm 3 ký tự chữ/số, ví dụ FPT, C32, HT1');\n    });\n  }\n\n  function horizonCards(report) {''',
)
replace(
    "website/assets/app.js",
    "/^[A-Z]{3}$/.test(item.ticker)",
    "/^(?=.*[A-Z])[A-Z0-9]{3}$/.test(item.ticker)",
)
replace(
    "website/assets/app.js",
    '''    mountPortalShell();\n    wireNavigation();''',
    '''    mountPortalShell();\n    enableAlphanumericTickerInputs();\n    wireNavigation();''',
)

replace(
    "website/assets/account-preferences.js",
    "return String(value || '').trim().toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);",
    "return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 3);",
)
replace(
    "website/assets/account-preferences.js",
    "const ticker = String(item.ticker || '').replace(/[^A-Z]/g, '');",
    "const ticker = String(item.ticker || '').replace(/[^A-Z0-9]/g, '');",
)
replace(
    "website/assets/account-preferences.js",
    "if (!/^[A-Z]{3}$/.test(ticker)) return setMessage(watchlistMessage, 'Nhập mã gồm đúng 3 chữ cái.', 'error');",
    "if (!/^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker)) return setMessage(watchlistMessage, 'Nhập mã HOSE gồm đúng 3 ký tự chữ/số.', 'error');",
)

replace(
    "website/assets/home-core-v1.js",
    "return String(value || '').trim().toUpperCase().replace(/[^A-Z]/g, '').slice(0, 3);",
    "return String(value || '').trim().toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 3);",
)
replace(
    "website/assets/home-core-v1.js",
    "return /^[A-Z]{3}$/.test(value);",
    "return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(value);",
)
replace(
    "website/assets/stock-api-client.js",
    "return /^[A-Z]{3}$/.test(ticker) ? ticker : '';",
    "return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker) ? ticker : '';",
)
replace(
    "website/assets/buyer-readiness-v1.js",
    "if (/^[A-Z]{3}$/.test(staticTicker)) return staticTicker;",
    "if (/^(?=.*[A-Z])[A-Z0-9]{3}$/.test(staticTicker)) return staticTicker;",
)
replace(
    "website/assets/buyer-readiness-v1.js",
    "return /^[A-Z]{3}$/.test(ticker) ? ticker : '';",
    "return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker) ? ticker : '';",
)
replace(
    "website/assets/public-copy-v7.js",
    "if (!/^[A-Z]{3}$/.test(ticker)) return;",
    "if (!/^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker)) return;",
)
replace(
    "website/assets/free-stock-context-v1.js",
    "return /^[A-Z]{3}$/.test(ticker) ? ticker : '';",
    "return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker) ? ticker : '';",
)
replace(
    "website/assets/direct-ticker-nav-v1.js",
    "return /^[A-Z]{3}$/.test(ticker);",
    "return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker);",
)
replace(
    "website/assets/stock-page-context-v1.js",
    "return /^[A-Z]{3}$/.test(ticker) ? ticker : '';",
    "return /^(?=.*[A-Z])[A-Z0-9]{3}$/.test(ticker) ? ticker : '';",
)

print("Full-HOSE alphanumeric CLI/web surface patch applied.")
