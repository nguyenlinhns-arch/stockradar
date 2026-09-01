from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from .models import Horizon


TICKER_PATTERN = re.compile(r"^[A-Z][A-Z0-9]{1,11}$")
DEFAULT_TTL = {
    Horizon.SHORT_TERM: timedelta(minutes=60),
    Horizon.MEDIUM_TERM: timedelta(hours=8),
    Horizon.LONG_TERM: timedelta(days=1),
    Horizon.ACCUMULATION: timedelta(days=7),
}


class UnsupportedTickerError(ValueError):
    pass


class AnalysisUnavailableError(RuntimeError):
    pass


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def normalize_ticker(value: str) -> str:
    ticker = re.sub(r"[^A-Z0-9]", "", str(value or "").strip().upper())
    if not TICKER_PATTERN.fullmatch(ticker):
        raise UnsupportedTickerError("Ticker format is invalid")
    return ticker


@dataclass(frozen=True)
class Security:
    ticker: str
    company_name: str
    sector: str
    exchange: str = "HOSE"
    active: bool = True

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Security":
        ticker = normalize_ticker(str(value["ticker"]))
        exchange = str(value.get("exchange", "HOSE")).upper()
        if exchange != "HOSE":
            raise ValueError("StockRadar MVP only accepts HOSE securities")
        return cls(
            ticker=ticker,
            company_name=str(value["company_name"]),
            sector=str(value.get("sector", "Chưa phân loại")),
            exchange=exchange,
            active=bool(value.get("active", True)),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ticker": self.ticker,
            "company_name": self.company_name,
            "sector": self.sector,
            "exchange": self.exchange,
            "active": self.active,
        }


class TickerMaster:
    def __init__(
        self,
        securities: Iterable[Security],
        *,
        snapshot_id: str,
        as_of: str,
        full_universe: bool,
        data_grade: str,
    ):
        self.snapshot_id = snapshot_id
        self.as_of = as_of
        self.full_universe = full_universe
        self.data_grade = data_grade
        self._items = {item.ticker: item for item in securities if item.active}
        if len(self._items) == 0:
            raise ValueError("Ticker master cannot be empty")

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "TickerMaster":
        return cls(
            (Security.from_dict(item) for item in value.get("items", [])),
            snapshot_id=str(value.get("snapshot_id", "UNKNOWN")),
            as_of=str(value.get("as_of", "")),
            full_universe=bool(value.get("full_universe", False)),
            data_grade=str(value.get("data_grade", "INSUFFICIENT")),
        )

    @classmethod
    def from_path(cls, path: str | Path) -> "TickerMaster":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    def resolve(self, value: str) -> Security:
        ticker = normalize_ticker(value)
        security = self._items.get(ticker)
        if security is None:
            raise UnsupportedTickerError(
                "Mã này hiện không thuộc phạm vi cổ phiếu HOSE mà StockRadar hỗ trợ."
            )
        return security

    def autocomplete(self, query: str, limit: int = 8) -> list[Security]:
        normalized = re.sub(r"[^A-Z0-9]", "", str(query or "").upper())
        if not normalized:
            return []
        starts = [item for item in self._items.values() if item.ticker.startswith(normalized)]
        company = [
            item for item in self._items.values()
            if normalized in item.company_name.upper() and item not in starts
        ]
        return sorted(starts, key=lambda item: item.ticker)[:limit] + sorted(
            company, key=lambda item: item.ticker
        )[: max(0, limit - len(starts))]

    def can_support_full_hose_claim(self) -> bool:
        return self.full_universe and self.data_grade == "DECISION_GRADE"

    def securities(self) -> tuple[Security, ...]:
        return tuple(self._items[key] for key in sorted(self._items))

    def to_public_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "2.1.2",
            "snapshot_id": self.snapshot_id,
            "as_of": self.as_of,
            "full_universe": self.full_universe,
            "data_grade": self.data_grade,
            "items": [item.to_dict() for item in self.securities()],
        }


@dataclass(frozen=True)
class CacheLookup:
    status: str
    payload: dict[str, Any] | None
    generated_at: str | None = None
    expires_at: str | None = None


class StockReportCache:
    """SQLite cache keyed by ticker + horizon + report type.

    The cache is a performance layer only. It cannot promote incomplete data to a
    stronger grade and it never replaces the full-universe gate used by ranking.
    """

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute(
            """
            CREATE TABLE IF NOT EXISTS stock_report_cache (
                ticker TEXT NOT NULL,
                horizon TEXT NOT NULL,
                report_type TEXT NOT NULL,
                snapshot_id TEXT NOT NULL,
                generated_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                freshness TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                report_version TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                PRIMARY KEY (ticker, horizon, report_type)
            )
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def lookup(
        self,
        ticker: str,
        horizon: Horizon,
        report_type: str = "DEEP",
        *,
        now: datetime | None = None,
    ) -> CacheLookup:
        row = self.connection.execute(
            """
            SELECT generated_at, expires_at, payload_json
            FROM stock_report_cache
            WHERE ticker = ? AND horizon = ? AND report_type = ?
            """,
            (normalize_ticker(ticker), horizon.value, report_type),
        ).fetchone()
        if row is None:
            return CacheLookup("MISS", None)
        payload = json.loads(row["payload_json"])
        current = now or utc_now()
        status = "HIT" if parse_timestamp(row["expires_at"]) > current else "STALE"
        return CacheLookup(status, payload, row["generated_at"], row["expires_at"])

    def put(
        self,
        ticker: str,
        horizon: Horizon,
        payload: dict[str, Any],
        *,
        snapshot_id: str,
        generated_at: datetime | None = None,
        ttl: timedelta | None = None,
        report_type: str = "DEEP",
        report_version: str = "2.1.2",
    ) -> CacheLookup:
        generated = generated_at or utc_now()
        expires = generated + (ttl or DEFAULT_TTL[horizon])
        serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        payload_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO stock_report_cache (
                    ticker, horizon, report_type, snapshot_id, generated_at,
                    expires_at, freshness, payload_hash, report_version, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, 'FRESH', ?, ?, ?)
                ON CONFLICT(ticker, horizon, report_type) DO UPDATE SET
                    snapshot_id = excluded.snapshot_id,
                    generated_at = excluded.generated_at,
                    expires_at = excluded.expires_at,
                    freshness = excluded.freshness,
                    payload_hash = excluded.payload_hash,
                    report_version = excluded.report_version,
                    payload_json = excluded.payload_json
                """,
                (
                    normalize_ticker(ticker), horizon.value, report_type, snapshot_id,
                    generated.isoformat(), expires.isoformat(), payload_hash,
                    report_version, serialized,
                ),
            )
        return CacheLookup("HIT", payload, generated.isoformat(), expires.isoformat())


DeepReportGenerator = Callable[[Security, Horizon], dict[str, Any]]


class TickerLookupService:
    def __init__(
        self,
        master: TickerMaster,
        cache: StockReportCache,
        *,
        quick_results: dict[str, dict[str, Any]] | None = None,
        generator: DeepReportGenerator | None = None,
    ):
        self.master = master
        self.cache = cache
        self.quick_results = quick_results or {}
        self.generator = generator

    def quick_report(self, value: str) -> dict[str, Any]:
        security = self.master.resolve(value)
        base = {
            **security.to_dict(),
            "snapshot_id": self.master.snapshot_id,
            "updated_at": self.master.as_of,
            "data_status": "INSUFFICIENT",
            "current_price": None,
            "rank": None,
            "sector_rank": None,
            "new_position_state": "CHƯA ĐỦ DỮ LIỆU",
            "holding_state": "CHƯA ĐỦ DỮ LIỆU",
        }
        base.update(self.quick_results.get(security.ticker, {}))
        return base

    def deep_report(
        self,
        value: str,
        horizon: Horizon,
        *,
        now: datetime | None = None,
    ) -> tuple[dict[str, Any], str]:
        security = self.master.resolve(value)
        cached = self.cache.lookup(security.ticker, horizon, now=now)
        if cached.status == "HIT" and cached.payload is not None:
            return cached.payload, "HIT"
        if self.generator is None:
            raise AnalysisUnavailableError(
                "Đánh giá nhanh đã sẵn sàng. Một số phần phân tích chuyên sâu hiện chưa đủ dữ liệu."
            )
        payload = self.generator(security, horizon)
        stored = self.cache.put(
            security.ticker,
            horizon,
            payload,
            snapshot_id=self.master.snapshot_id,
            generated_at=now,
        )
        return stored.payload or payload, "REFRESH" if cached.status == "STALE" else "MISS"
