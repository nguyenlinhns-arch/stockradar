from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA_PATH = Path(__file__).resolve().parents[2] / "track-record" / "schema.sql"


class ImmutableLedger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.connection.close()

    def initialize(self) -> None:
        self.connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        self.connection.commit()

    def append_radar(self, radar: dict[str, Any]) -> None:
        snapshot = radar["snapshot"]
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO snapshots (
                    snapshot_id, as_of, source_timestamp, exchange, source,
                    data_grade, universe_total, scanned_total, valid_total,
                    excluded_total, coverage_pct, market_regime, release_status,
                    raw_payload
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot["snapshot_id"],
                    snapshot["as_of"],
                    snapshot["source_timestamp"],
                    snapshot["exchange"],
                    snapshot["source"],
                    snapshot["data_grade"],
                    snapshot["expected_total"],
                    snapshot["scanned_count"],
                    snapshot["valid_count"],
                    snapshot["excluded_count"],
                    snapshot["universe_coverage_pct"],
                    radar["market_regime"],
                    radar["status"],
                    json.dumps(radar, ensure_ascii=False, sort_keys=True),
                ),
            )
            for item in radar["items"]:
                self.connection.execute(
                    """
                    INSERT INTO radar_entries (
                        snapshot_id, rank, ticker, score, score_coverage_pct,
                        setup, state, previous_state, state_change, current_price,
                        pivot, reason, evidence_json, is_mock
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot["snapshot_id"],
                        item["rank"],
                        item["ticker"],
                        item["score"],
                        item["score_coverage_pct"],
                        item["setup"],
                        item["state"],
                        item["previous_state"],
                        item["state_change"],
                        item["current_price"],
                        item["pivot"],
                        item["reason"],
                        json.dumps(item["evidence"], ensure_ascii=False),
                        1 if item["is_mock"] else 0,
                    ),
                )

    def append_correction(
        self,
        snapshot_id: str,
        reason: str,
        corrected_payload: dict[str, Any],
        created_at: str,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO corrections (snapshot_id, created_at, reason, corrected_payload)
                VALUES (?, ?, ?, ?)
                """,
                (snapshot_id, created_at, reason, json.dumps(corrected_payload, ensure_ascii=False)),
            )

    def append_performance_observation(
        self,
        snapshot_id: str,
        ticker: str,
        observed_at: str,
        horizon: str,
        outcome_pct: float | None,
        mae_pct: float | None,
        mfe_pct: float | None,
        r_multiple: float | None,
    ) -> None:
        with self.connection:
            self.connection.execute(
                """
                INSERT INTO performance_observations (
                    snapshot_id, ticker, observed_at, horizon, outcome_pct,
                    mae_pct, mfe_pct, r_multiple
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (snapshot_id, ticker, observed_at, horizon, outcome_pct, mae_pct, mfe_pct, r_multiple),
            )

    def snapshot_count(self) -> int:
        return int(self.connection.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])

    def fetch_public_track_record(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            """
            SELECT s.snapshot_id, s.as_of, s.market_regime, s.release_status,
                   e.rank, e.ticker, e.score, e.state, e.state_change, e.is_mock
            FROM snapshots s
            JOIN radar_entries e USING(snapshot_id)
            ORDER BY s.as_of DESC, e.rank ASC
            """
        ).fetchall()
        return [dict(row) for row in rows]

