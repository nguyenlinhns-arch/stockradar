from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import csv
import math
import os
from pathlib import Path
from typing import Any, Iterable, Mapping, Protocol, Sequence
from .ticker_symbol import is_valid_hose_ticker


DATACORE_RAW_FUNDAMENTALS_VERSION = "STOCKRADAR_DATACORE_RAW_FUNDAMENTALS_V1"
DATACORE_ANNUAL_DATASET = "fundamental_annual"
DATACORE_QUARTERLY_DATASET = "fundamental_quaterly"
DATACORE_INPUT_ROLE = "RAW_FINANCIAL_STATEMENT_LINE_ITEMS_ONLY"


class DataCoreRawFundamentalsError(RuntimeError):
    pass


@dataclass(frozen=True)
class DataCoreCredentials:
    api_key: str

    @classmethod
    def from_env(cls) -> "DataCoreCredentials":
        key = (os.environ.get("DATACORE_API_KEY") or os.environ.get("X_API_KEY") or "").strip()
        if not key:
            raise DataCoreRawFundamentalsError(
                "DataCore API key is not configured; set DATACORE_API_KEY or X_API_KEY"
            )
        return cls(api_key=key)


class DataCoreClientLike(Protocol):
    def paginate(
        self,
        dataset_code: str,
        *,
        limit: int = 100,
        max_pages: int | None = None,
    ) -> Iterable[object]: ...


@dataclass(frozen=True)
class SecurityShares:
    ticker: str
    shares_outstanding: float


@dataclass(frozen=True)
class NormalizedFinancialRow:
    ticker: str
    period_end: str
    period_type: str
    revenue: float
    net_income: float
    total_assets: float
    equity: float
    total_debt: float
    cash: float
    operating_cash_flow: float
    capex: float
    shares_outstanding: float
    operating_profit: float | None = None
    depreciation_amortization: float | None = None

    def to_row(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "period_end": self.period_end,
            "period_type": self.period_type,
            "revenue": self.revenue,
            "net_income": self.net_income,
            "total_assets": self.total_assets,
            "equity": self.equity,
            "total_debt": self.total_debt,
            "cash": self.cash,
            "operating_cash_flow": self.operating_cash_flow,
            "capex": self.capex,
            "shares_outstanding": self.shares_outstanding,
            "operating_profit": "" if self.operating_profit is None else self.operating_profit,
            "depreciation_amortization": (
                "" if self.depreciation_amortization is None else self.depreciation_amortization
            ),
        }


RAW_ALIASES: dict[str, tuple[str, ...]] = {
    "ticker": ("symbol", "ticker", "stock_code", "code"),
    "year": ("year", "fiscal_year", "report_year"),
    "quarter": ("quarter", "quater", "quarter_no", "report_quarter"),
    "period_end": ("period_end", "report_date", "date", "fiscal_period_end"),
    "revenue": ("is_net_revenue", "net_revenue", "revenue"),
    "net_income": ("is_shareholders_eat", "is_eat", "net_income", "profit_after_tax"),
    "total_assets": ("total_asset", "total_assets"),
    "equity": ("total_equity", "e_equity", "equity"),
    "operating_cash_flow": ("total_cfo", "operating_cash_flow", "cash_flow_from_operations"),
    "capex": ("capex", "capital_expenditure"),
    "cash": ("ca_cce", "cash_and_cash_equivalents", "cash"),
    "operating_profit": ("is_net_business_profit", "operating_profit"),
    "depreciation_amortization": (
        "depreciation_amortization",
        "depreciation_and_amortization",
        "depreciation",
    ),
    "total_debt": ("total_debt", "interest_bearing_debt"),
    "cl_loan": ("cl_loan",),
    "cl_finlease": ("cl_finlease",),
    "cl_due_long_debt": ("cl_due_long_debt",),
    "nl_loan": ("nl_loan",),
    "nl_finlease": ("nl_finlease",),
}

# These are raw accounting line items StockRadar is willing to consume. Provider
# ratios, scores, growth rates, EPS and valuation metrics are deliberately absent.
OUTPUT_FIELDS = (
    "ticker",
    "period_end",
    "period_type",
    "revenue",
    "net_income",
    "total_assets",
    "equity",
    "total_debt",
    "cash",
    "operating_cash_flow",
    "capex",
    "shares_outstanding",
    "operating_profit",
    "depreciation_amortization",
)


def _lower_keys(row: Mapping[str, object]) -> dict[str, object]:
    return {str(key).strip().lower(): value for key, value in row.items()}


def _lookup(row: Mapping[str, object], field: str) -> object | None:
    lowered = _lower_keys(row)
    for alias in RAW_ALIASES[field]:
        if alias in lowered:
            return lowered[alias]
    return None


def _ticker(value: object) -> str:
    ticker = str(value or "").strip().upper()
    if not is_valid_hose_ticker(ticker):
        raise DataCoreRawFundamentalsError(f"invalid listed-company ticker: {ticker!r}")
    return ticker


def _float(value: object, field: str, *, allow_blank: bool = False) -> float | None:
    if value is None or str(value).strip() == "":
        if allow_blank:
            return None
        raise DataCoreRawFundamentalsError(f"required raw financial field is blank: {field}")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise DataCoreRawFundamentalsError(f"raw financial field is not numeric: {field}") from error
    if not math.isfinite(result):
        raise DataCoreRawFundamentalsError(f"raw financial field is not finite: {field}")
    return result


def _int(value: object, field: str) -> int:
    number = _float(value, field)
    assert number is not None
    result = int(number)
    if float(result) != number:
        raise DataCoreRawFundamentalsError(f"raw financial field must be integer-like: {field}")
    return result


def _period_end(row: Mapping[str, object], *, period_type: str) -> str:
    raw_date = _lookup(row, "period_end")
    if raw_date is not None and str(raw_date).strip():
        text = str(raw_date).strip().replace("/", "-")
        try:
            return date.fromisoformat(text[:10]).isoformat()
        except ValueError:
            try:
                return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
            except ValueError as error:
                raise DataCoreRawFundamentalsError(f"invalid raw financial period_end: {raw_date!r}") from error

    year = _int(_lookup(row, "year"), "year")
    if year < 1990 or year > 2100:
        raise DataCoreRawFundamentalsError(f"raw financial year outside expected range: {year}")
    if period_type == "ANNUAL":
        return date(year, 12, 31).isoformat()
    quarter = _int(_lookup(row, "quarter"), "quarter")
    quarter_ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    if quarter not in quarter_ends:
        raise DataCoreRawFundamentalsError(f"raw financial quarter outside 1..4: {quarter}")
    month, day = quarter_ends[quarter]
    return date(year, month, day).isoformat()


def _sum_debt(row: Mapping[str, object]) -> float:
    direct = _float(_lookup(row, "total_debt"), "total_debt", allow_blank=True)
    if direct is not None:
        return max(0.0, direct)
    components = []
    for field in ("cl_loan", "cl_finlease", "cl_due_long_debt", "nl_loan", "nl_finlease"):
        value = _float(_lookup(row, field), field, allow_blank=True)
        components.append(0.0 if value is None else value)
    return max(0.0, sum(components))


def normalize_financial_row(
    raw: Mapping[str, object],
    *,
    period_type: str,
    shares_by_ticker: Mapping[str, float],
) -> NormalizedFinancialRow:
    period_type = period_type.strip().upper()
    if period_type not in {"ANNUAL", "QUARTER"}:
        raise ValueError("period_type must be ANNUAL or QUARTER")
    ticker = _ticker(_lookup(raw, "ticker"))
    if ticker not in shares_by_ticker:
        raise DataCoreRawFundamentalsError(f"fundamental row ticker outside HOSE security master: {ticker}")
    shares = float(shares_by_ticker[ticker])
    if not math.isfinite(shares) or shares <= 0:
        raise DataCoreRawFundamentalsError(f"invalid raw shares_outstanding for {ticker}")

    revenue = _float(_lookup(raw, "revenue"), "revenue")
    net_income = _float(_lookup(raw, "net_income"), "net_income")
    total_assets = _float(_lookup(raw, "total_assets"), "total_assets")
    equity = _float(_lookup(raw, "equity"), "equity")
    ocf = _float(_lookup(raw, "operating_cash_flow"), "operating_cash_flow")
    cash = _float(_lookup(raw, "cash"), "cash", allow_blank=True)
    capex = _float(_lookup(raw, "capex"), "capex", allow_blank=True)
    op_profit = _float(_lookup(raw, "operating_profit"), "operating_profit", allow_blank=True)
    da = _float(
        _lookup(raw, "depreciation_amortization"),
        "depreciation_amortization",
        allow_blank=True,
    )
    assert revenue is not None and net_income is not None and total_assets is not None
    assert equity is not None and ocf is not None
    if total_assets <= 0:
        raise DataCoreRawFundamentalsError(f"total_assets must be positive for {ticker}")
    if equity <= 0:
        raise DataCoreRawFundamentalsError(f"equity must be positive for {ticker}")

    return NormalizedFinancialRow(
        ticker=ticker,
        period_end=_period_end(raw, period_type=period_type),
        period_type=period_type,
        revenue=revenue,
        net_income=net_income,
        total_assets=total_assets,
        equity=equity,
        total_debt=_sum_debt(raw),
        cash=0.0 if cash is None else max(0.0, cash),
        operating_cash_flow=ocf,
        capex=0.0 if capex is None else abs(capex),
        shares_outstanding=shares,
        operating_profit=op_profit,
        depreciation_amortization=None if da is None else abs(da),
    )


def read_hose_shares(path: str | Path) -> dict[str, float]:
    source = Path(path)
    result: dict[str, float] = {}
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"ticker", "exchange", "listed_shares"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise DataCoreRawFundamentalsError(
                "security master must contain ticker, exchange and listed_shares"
            )
        for row in reader:
            if str(row.get("exchange") or "").strip().upper() != "HOSE":
                continue
            ticker = _ticker(row.get("ticker"))
            shares = _float(row.get("listed_shares"), "listed_shares")
            assert shares is not None
            if shares <= 0:
                raise DataCoreRawFundamentalsError(f"listed_shares must be positive for {ticker}")
            result[ticker] = shares
    if not result:
        raise DataCoreRawFundamentalsError("security master contains no HOSE stocks")
    return result


def _frame_records(frame: object) -> list[dict[str, object]]:
    # pandas DataFrame from the official SDK.
    if hasattr(frame, "to_dict"):
        try:
            records = frame.to_dict(orient="records")  # type: ignore[attr-defined]
        except TypeError:
            records = None
        if isinstance(records, list):
            return [dict(item) for item in records if isinstance(item, Mapping)]
    if isinstance(frame, Sequence) and not isinstance(frame, (str, bytes, bytearray)):
        return [dict(item) for item in frame if isinstance(item, Mapping)]
    raise DataCoreRawFundamentalsError("unexpected DataCore page object; expected DataFrame/records")


def acquire_dataset(
    client: DataCoreClientLike,
    dataset_code: str,
    *,
    period_type: str,
    shares_by_ticker: Mapping[str, float],
    max_pages: int = 5000,
) -> tuple[NormalizedFinancialRow, ...]:
    rows: list[NormalizedFinancialRow] = []
    try:
        pages = client.paginate(dataset_code, limit=100, max_pages=max_pages)
        for page in pages:
            for raw in _frame_records(page):
                ticker_value = _lookup(raw, "ticker")
                try:
                    ticker = _ticker(ticker_value)
                except DataCoreRawFundamentalsError:
                    continue
                if ticker not in shares_by_ticker:
                    continue
                rows.append(
                    normalize_financial_row(
                        raw,
                        period_type=period_type,
                        shares_by_ticker=shares_by_ticker,
                    )
                )
    except DataCoreRawFundamentalsError:
        raise
    except Exception as error:
        raise DataCoreRawFundamentalsError(
            f"DataCore fundamentals acquisition failed for {dataset_code}"
        ) from error
    if not rows:
        raise DataCoreRawFundamentalsError(f"DataCore returned no usable HOSE rows for {dataset_code}")
    return tuple(rows)


def reconcile_rows(
    annual: Iterable[NormalizedFinancialRow],
    quarterly: Iterable[NormalizedFinancialRow],
    *,
    expected_tickers: Iterable[str],
    minimum_annual_periods: int = 2,
) -> tuple[NormalizedFinancialRow, ...]:
    combined = [*annual, *quarterly]
    by_key: dict[tuple[str, str, str], NormalizedFinancialRow] = {}
    for row in combined:
        key = (row.ticker, row.period_end, row.period_type)
        if key in by_key and by_key[key] != row:
            raise DataCoreRawFundamentalsError(
                f"conflicting duplicate fundamental row: {row.ticker} {row.period_end} {row.period_type}"
            )
        by_key[key] = row
    expected = {_ticker(value) for value in expected_tickers}
    annual_count = {ticker: 0 for ticker in expected}
    for row in by_key.values():
        if row.ticker in annual_count and row.period_type == "ANNUAL":
            annual_count[row.ticker] += 1
    missing = sorted(ticker for ticker, count in annual_count.items() if count < minimum_annual_periods)
    if missing:
        raise DataCoreRawFundamentalsError(
            "fundamental history below StockRadar minimum annual coverage: " + ", ".join(missing[:20])
        )
    return tuple(sorted(by_key.values(), key=lambda row: (row.ticker, row.period_end, row.period_type)))


def write_fundamentals(path: str | Path, rows: Iterable[NormalizedFinancialRow]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_row())


class DataCoreAuthenticatedSession:
    """Lazy official SDK wrapper; API key exists only in process memory."""

    def __init__(self, credentials: DataCoreCredentials) -> None:
        self.credentials = credentials
        self.client: Any = None

    def __enter__(self) -> "DataCoreAuthenticatedSession":
        try:
            from datacore import Datacore  # type: ignore
        except ImportError as error:
            raise DataCoreRawFundamentalsError(
                "official DataCore Python SDK is required; install package 'datacore'"
            ) from error
        try:
            self.client = Datacore(api_key=self.credentials.api_key)
        except Exception as error:
            raise DataCoreRawFundamentalsError("DataCore client initialization failed") from error
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.client = None


def acquire_fundamentals(
    *,
    client: DataCoreClientLike,
    shares_by_ticker: Mapping[str, float],
    minimum_annual_periods: int = 2,
) -> tuple[NormalizedFinancialRow, ...]:
    annual = acquire_dataset(
        client,
        DATACORE_ANNUAL_DATASET,
        period_type="ANNUAL",
        shares_by_ticker=shares_by_ticker,
    )
    quarterly = acquire_dataset(
        client,
        DATACORE_QUARTERLY_DATASET,
        period_type="QUARTER",
        shares_by_ticker=shares_by_ticker,
    )
    return reconcile_rows(
        annual,
        quarterly,
        expected_tickers=shares_by_ticker,
        minimum_annual_periods=minimum_annual_periods,
    )
