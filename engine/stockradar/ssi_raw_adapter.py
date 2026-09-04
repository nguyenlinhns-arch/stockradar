from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
import csv
import os
from pathlib import Path
import time
from typing import Any, Callable, Iterable, Mapping, Protocol, Sequence
from .ticker_symbol import is_valid_hose_ticker


SSI_RAW_ADAPTER_VERSION = "STOCKRADAR_SSI_RAW_ADAPTER_V1"
SSI_SOURCE_ID = "SSI_FASTCONNECT_V3_RAW_MARKET"
REQUIRED_ENV = (
    "SSI_FASTCONNECT_CLIENT_ID",
    "SSI_FASTCONNECT_API_KEY",
    "SSI_FASTCONNECT_API_SECRET",
)


class SSIRawAdapterError(RuntimeError):
    pass


@dataclass(frozen=True)
class SSICredentials:
    client_id: str
    api_key: str
    api_secret: str

    @classmethod
    def from_env(cls) -> "SSICredentials":
        values = {name: os.environ.get(name, "").strip() for name in REQUIRED_ENV}
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise SSIRawAdapterError(
                "SSI FastConnect credentials are not configured; missing environment variable(s): "
                + ", ".join(missing)
            )
        return cls(
            client_id=values["SSI_FASTCONNECT_CLIENT_ID"],
            api_key=values["SSI_FASTCONNECT_API_KEY"],
            api_secret=values["SSI_FASTCONNECT_API_SECRET"],
        )


class MarketDataLike(Protocol):
    def get_securities_info_by_board(self, board: object) -> Sequence[object]: ...

    def get_ohlc_1day_historical(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        page: int = 1,
        size: int = 1000,
    ) -> Sequence[object]: ...

    def get_ohlc_5minute_historical(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        page: int = 1,
        size: int = 1000,
    ) -> Sequence[object]: ...


@dataclass(frozen=True)
class RawSecurity:
    ticker: str
    name: str
    exchange: str
    sector: str
    icb_code: str
    listed_shares: int | None
    first_trading_date: str

    def to_row(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "name": self.name,
            "exchange": self.exchange,
            "sector": self.sector,
            "icb_code": self.icb_code,
            "listed_shares": "" if self.listed_shares is None else self.listed_shares,
            "first_trading_date": self.first_trading_date,
        }


@dataclass(frozen=True)
class RawOHLCV:
    ticker: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    value: float | None = None

    def to_row(self) -> dict[str, object]:
        return {
            "ticker": self.ticker,
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "value": "" if self.value is None else self.value,
        }


def _get(value: object, *names: str, default: object = None) -> object:
    if isinstance(value, Mapping):
        for name in names:
            if name in value:
                return value[name]
    for name in names:
        if hasattr(value, name):
            return getattr(value, name)
    return default


def _text(value: object) -> str:
    return str(value or "").strip()


def _ticker(value: object) -> str:
    ticker = _text(value).upper()
    if not is_valid_hose_ticker(ticker):
        raise SSIRawAdapterError(f"invalid HOSE stock ticker returned by SSI: {ticker!r}")
    return ticker


def _number(value: object, field: str) -> float:
    if value is None or _text(value) == "":
        raise SSIRawAdapterError(f"SSI raw OHLCV field is blank: {field}")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise SSIRawAdapterError(f"SSI raw OHLCV field is not numeric: {field}") from error
    return result


def _optional_number(value: object) -> float | None:
    if value is None or _text(value) == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise SSIRawAdapterError("SSI optional raw numeric field is invalid") from error


def _board_text(value: object) -> str:
    raw = _text(value).upper()
    if raw.endswith(".HOSE") or raw == "HOSE":
        return "HOSE"
    return raw


def _format_sdk_date(value: date | datetime | str, *, end_of_day: bool = False) -> str:
    if isinstance(value, datetime):
        return value.strftime("%Y/%m/%d %H:%M:%S")
    if isinstance(value, date):
        suffix = "23:59:59" if end_of_day else "00:00:00"
        return value.strftime("%Y/%m/%d") + " " + suffix
    text = _text(value)
    if not text:
        raise SSIRawAdapterError("date is required")
    # Accept ISO YYYY-MM-DD and pass already-formatted SDK values through.
    if len(text) == 10 and text[4] == "-" and text[7] == "-":
        parsed = date.fromisoformat(text)
        return _format_sdk_date(parsed, end_of_day=end_of_day)
    return text


def _timestamp(value: object) -> str:
    text = _text(value)
    if not text:
        raise SSIRawAdapterError("SSI OHLCV trading_date is blank")
    return text


def _is_common_stock(info: object) -> bool:
    symbol = _text(_get(info, "symbol", "Symbol")).upper()
    if not is_valid_hose_ticker(symbol):
        return False
    # Covered warrants expose an underlying symbol; ETFs/funds on HOSE generally use
    # longer symbols. Maturity date is also a useful defensive exclusion for warrants.
    if _text(_get(info, "cw_underlying_symbol", "cwUnderlyingSymbol", "CWUnderlyingSymbol")):
        return False
    if _text(_get(info, "maturity_date", "maturityDate", "MaturityDate")):
        return False
    return True


def normalize_security(info: object) -> RawSecurity:
    board = _board_text(_get(info, "board", "Board"))
    if board != "HOSE":
        raise SSIRawAdapterError(f"SSI security is not HOSE: {board or '<blank>'}")
    ticker = _ticker(_get(info, "symbol", "Symbol"))
    sector = _text(_get(info, "icb_name", "icbName", "ICBName"))
    if not sector:
        raise SSIRawAdapterError(f"SSI raw ICB sector is missing for {ticker}")
    name = _text(_get(info, "symbol_name_vi", "symbolNameVi", "SymbolNameVi")) or ticker
    listed = _optional_number(_get(info, "listed_shares", "listedShares", "ListedShares"))
    return RawSecurity(
        ticker=ticker,
        name=name,
        exchange="HOSE",
        sector=sector,
        icb_code=_text(_get(info, "icb_code", "icbCode", "ICBCode")),
        listed_shares=int(listed) if listed is not None else None,
        first_trading_date=_text(_get(info, "first_trading_date", "firstTradingDate", "FirstTradingDate")),
    )


def normalize_ohlcv(symbol: str, item: object) -> RawOHLCV:
    requested = _ticker(symbol)
    returned = _text(_get(item, "symbol", "Symbol")).upper()
    if returned and returned != requested:
        raise SSIRawAdapterError(
            f"SSI OHLCV response symbol mismatch: requested={requested}, returned={returned}"
        )
    open_price = _number(_get(item, "open_price", "openPrice", "OpenPrice"), "open_price")
    high = _number(_get(item, "high_price", "highPrice", "HighPrice"), "high_price")
    low = _number(_get(item, "low_price", "lowPrice", "LowPrice"), "low_price")
    close = _number(_get(item, "close_price", "closePrice", "ClosePrice"), "close_price")
    volume = _number(_get(item, "volume", "Volume"), "volume")
    if min(open_price, high, low, close) <= 0:
        raise SSIRawAdapterError(f"SSI OHLCV contains non-positive price for {requested}")
    if volume < 0:
        raise SSIRawAdapterError(f"SSI OHLCV contains negative volume for {requested}")
    if high < max(open_price, close, low) or low > min(open_price, close, high):
        raise SSIRawAdapterError(f"SSI OHLCV high/low invariant failed for {requested}")
    return RawOHLCV(
        ticker=requested,
        timestamp=_timestamp(_get(item, "trading_date", "tradingDate", "TradingDate")),
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        value=_optional_number(_get(item, "value", "Value")),
    )


class SSIRawMarketAdapter:
    """Read-only SSI FastConnect market adapter.

    SSI is used only as a transport for raw security identity/ICB and OHLCV fields.
    All derived indicators, rankings and recommendations are computed downstream by
    StockRadar. The adapter deliberately does not expose SSI summary/rating fields.
    """

    def __init__(
        self,
        market_data: MarketDataLike,
        *,
        hose_board: object = "HOSE",
        retry_attempts: int = 3,
        retry_delay_seconds: float = 0.25,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if retry_attempts < 1 or retry_attempts > 5:
            raise ValueError("retry_attempts must be between 1 and 5")
        self.market_data = market_data
        self.hose_board = hose_board
        self.retry_attempts = retry_attempts
        self.retry_delay_seconds = max(0.0, retry_delay_seconds)
        self.sleeper = sleeper

    def _call(self, fn: Callable[[], Sequence[object]], label: str) -> Sequence[object]:
        last_error: Exception | None = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                return fn()
            except Exception as error:  # provider/network exception; no credentials logged
                last_error = error
                if attempt >= self.retry_attempts:
                    break
                self.sleeper(self.retry_delay_seconds * attempt)
        raise SSIRawAdapterError(f"SSI FastConnect request failed after bounded retry: {label}") from last_error

    def fetch_hose_securities(self) -> tuple[RawSecurity, ...]:
        raw = self._call(
            lambda: self.market_data.get_securities_info_by_board(self.hose_board),
            "securities_info_by_board",
        )
        securities: dict[str, RawSecurity] = {}
        for item in raw:
            if not _is_common_stock(item):
                continue
            security = normalize_security(item)
            if security.ticker in securities:
                raise SSIRawAdapterError(f"duplicate SSI HOSE security: {security.ticker}")
            securities[security.ticker] = security
        if not securities:
            raise SSIRawAdapterError("SSI returned no eligible HOSE common stocks")
        return tuple(securities[ticker] for ticker in sorted(securities))

    def _fetch_paged(
        self,
        *,
        symbol: str,
        method_name: str,
        from_date: date | datetime | str,
        to_date: date | datetime | str,
        page_size: int,
        max_pages: int,
    ) -> tuple[RawOHLCV, ...]:
        ticker = _ticker(symbol)
        if not (1 <= page_size <= 1000):
            raise ValueError("page_size must be between 1 and 1000")
        if not (1 <= max_pages <= 500):
            raise ValueError("max_pages must be between 1 and 500")
        method = getattr(self.market_data, method_name)
        start = _format_sdk_date(from_date, end_of_day=False)
        end = _format_sdk_date(to_date, end_of_day=True)
        rows: list[RawOHLCV] = []
        for page in range(1, max_pages + 1):
            batch = self._call(
                lambda page=page: method(
                    symbol=ticker,
                    from_date=start,
                    to_date=end,
                    page=page,
                    size=page_size,
                ),
                f"{method_name}:{ticker}:page={page}",
            )
            if not batch:
                break
            rows.extend(normalize_ohlcv(ticker, item) for item in batch)
            if len(batch) < page_size:
                break
        else:
            raise SSIRawAdapterError(f"SSI paging exceeded max_pages for {ticker}")
        deduped: dict[str, RawOHLCV] = {}
        for row in rows:
            if row.timestamp in deduped:
                raise SSIRawAdapterError(f"duplicate SSI OHLCV timestamp for {ticker}: {row.timestamp}")
            deduped[row.timestamp] = row
        return tuple(deduped[key] for key in sorted(deduped))

    def fetch_daily_ohlcv(
        self,
        symbol: str,
        from_date: date | datetime | str,
        to_date: date | datetime | str,
        *,
        page_size: int = 1000,
        max_pages: int = 20,
    ) -> tuple[RawOHLCV, ...]:
        return self._fetch_paged(
            symbol=symbol,
            method_name="get_ohlc_1day_historical",
            from_date=from_date,
            to_date=to_date,
            page_size=page_size,
            max_pages=max_pages,
        )

    def fetch_5m_ohlcv(
        self,
        symbol: str,
        from_date: date | datetime | str,
        to_date: date | datetime | str,
        *,
        page_size: int = 1000,
        max_pages: int = 100,
    ) -> tuple[RawOHLCV, ...]:
        return self._fetch_paged(
            symbol=symbol,
            method_name="get_ohlc_5minute_historical",
            from_date=from_date,
            to_date=to_date,
            page_size=page_size,
            max_pages=max_pages,
        )


def write_security_master(path: str | Path, rows: Iterable[RawSecurity]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ("ticker", "name", "exchange", "sector", "icb_code", "listed_shares", "first_trading_date")
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_row())


def write_ohlcv(path: str | Path, rows: Iterable[RawOHLCV]) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ("ticker", "timestamp", "open", "high", "low", "close", "volume", "value")
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_row())


class SSIAuthenticatedSession(AbstractContextManager["SSIAuthenticatedSession"]):
    """Thin lazy wrapper around SSI's official Python SDK.

    Import is intentionally lazy so the StockRadar core/test suite has no hard runtime
    dependency on the provider package. Production acquisition installs `ssi-sdk`.
    """

    def __init__(self, credentials: SSICredentials) -> None:
        self.credentials = credentials
        self._auth: Any = None
        self._data: Any = None
        self.market_data: Any = None
        self.hose_board: object = "HOSE"

    def __enter__(self) -> "SSIAuthenticatedSession":
        try:
            from ssi_sdk import Auth, Config, Data  # type: ignore
            from ssi_sdk.enums import Board  # type: ignore
        except ImportError as error:
            raise SSIRawAdapterError(
                "SSI official Python SDK is required for live acquisition; install package 'ssi-sdk'"
            ) from error
        config = Config(
            client_id=self.credentials.client_id,
            api_key=self.credentials.api_key,
            api_secret=self.credentials.api_secret,
        )
        self._auth = Auth(config)
        self._auth.__enter__()
        try:
            self._auth.authenticate()  # Market Data token: no OTP required.
            self._data = Data(self._auth)
            self._data.__enter__()
            self.market_data = self._data.market_data
            self.hose_board = Board.HOSE
            return self
        except Exception as error:
            self.__exit__(type(error), error, error.__traceback__)
            raise SSIRawAdapterError("SSI FastConnect authentication/session setup failed") from error

    def __exit__(self, exc_type, exc, tb) -> bool | None:
        try:
            if self._data is not None:
                self._data.__exit__(exc_type, exc, tb)
        finally:
            if self._auth is not None:
                self._auth.__exit__(exc_type, exc, tb)
        self.market_data = None
        return None


def acquire_market_history(
    *,
    adapter: SSIRawMarketAdapter,
    from_date: date | datetime | str,
    to_date: date | datetime | str,
    minimum_daily_bars: int = 252,
) -> tuple[tuple[RawSecurity, ...], tuple[RawOHLCV, ...]]:
    securities = adapter.fetch_hose_securities()
    all_rows: list[RawOHLCV] = []
    for security in securities:
        rows = adapter.fetch_daily_ohlcv(security.ticker, from_date, to_date)
        if len(rows) < minimum_daily_bars:
            raise SSIRawAdapterError(
                f"SSI daily OHLCV coverage below StockRadar minimum for {security.ticker}: {len(rows)}"
            )
        all_rows.extend(rows)
    return securities, tuple(all_rows)
