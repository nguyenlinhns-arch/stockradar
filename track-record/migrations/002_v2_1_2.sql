-- One-time SQLite migration from the V2 schema to V2.1.2.
-- Fresh databases must use ../schema.sql instead.
PRAGMA foreign_keys = OFF;
BEGIN IMMEDIATE;

ALTER TABLE recommendations ADD COLUMN review_due_at TEXT;
ALTER TABLE recommendations ADD COLUMN review_status TEXT NOT NULL DEFAULT 'PENDING';
ALTER TABLE recommendations ADD COLUMN review_decision TEXT;
ALTER TABLE recommendations ADD COLUMN new_position_state TEXT NOT NULL DEFAULT 'NOT_ASSESSED';
ALTER TABLE recommendations ADD COLUMN holding_state TEXT NOT NULL DEFAULT 'NOT_ASSESSED';
ALTER TABLE recommendations ADD COLUMN vnindex_at_activation REAL;
ALTER TABLE recommendations ADD COLUMN vnindex_current_or_close REAL;

ALTER TABLE recommendation_events RENAME TO recommendation_events_v2;
CREATE TABLE recommendation_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    state TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    snapshot_id TEXT,
    system_version TEXT,
    created_by TEXT NOT NULL DEFAULT 'SYSTEM',
    audit_reference TEXT,
    correction_of INTEGER REFERENCES recommendation_events(event_id),
    performance_entry_price REAL,
    observed_price REAL,
    current_return_pct REAL,
    close_price REAL,
    final_return_pct REAL,
    reason TEXT,
    payload_json TEXT NOT NULL,
    UNIQUE (recommendation_id, event_type, event_at)
);
INSERT INTO recommendation_events (
    event_id, recommendation_id, event_type, event_at, new_state, state,
    created_by, audit_reference, performance_entry_price, observed_price,
    current_return_pct, close_price, final_return_pct, reason, payload_json
)
SELECT event_id, recommendation_id, event_type, event_at, state, state,
       'MIGRATION_V2_1_2', 'MIGRATED-' || event_id, performance_entry_price,
       observed_price, current_return_pct, close_price, final_return_pct,
       reason, payload_json
FROM recommendation_events_v2;
DROP TABLE recommendation_events_v2;

CREATE TRIGGER immutable_recommendation_events_update
BEFORE UPDATE ON recommendation_events BEGIN
    SELECT RAISE(ABORT, 'recommendation events are immutable');
END;
CREATE TRIGGER immutable_recommendation_events_delete
BEFORE DELETE ON recommendation_events BEGIN
    SELECT RAISE(ABORT, 'recommendation events are immutable');
END;

CREATE TABLE review_schedule (
    recommendation_id TEXT PRIMARY KEY REFERENCES recommendations(recommendation_id),
    review_due_at TEXT NOT NULL,
    review_status TEXT NOT NULL,
    reviewed_at TEXT,
    review_decision TEXT
);
CREATE TABLE benchmark_records (
    benchmark_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id),
    benchmark TEXT NOT NULL DEFAULT 'VNINDEX',
    start_value REAL NOT NULL,
    current_or_close_value REAL NOT NULL,
    return_pct REAL NOT NULL,
    excess_return_pct REAL NOT NULL,
    calculated_at TEXT NOT NULL
);
CREATE TABLE stock_report_cache (
    ticker TEXT NOT NULL, horizon TEXT NOT NULL, report_type TEXT NOT NULL,
    snapshot_id TEXT NOT NULL, generated_at TEXT NOT NULL, expires_at TEXT NOT NULL,
    freshness TEXT NOT NULL, payload_hash TEXT NOT NULL, report_version TEXT NOT NULL,
    payload_json TEXT NOT NULL, PRIMARY KEY (ticker, horizon, report_type)
);
CREATE TABLE monitored_tickers (
    ticker TEXT PRIMARY KEY, monitoring_status TEXT NOT NULL,
    last_evaluated_at TEXT, next_evaluation_at TEXT
);
CREATE TABLE ticker_subscribers (
    ticker TEXT NOT NULL REFERENCES monitored_tickers(ticker), user_id TEXT NOT NULL,
    subscription_tier TEXT NOT NULL, alert_enabled INTEGER NOT NULL DEFAULT 1,
    PRIMARY KEY (ticker, user_id)
);
CREATE TABLE active_intraday_universe (
    ticker TEXT PRIMARY KEY, reason TEXT NOT NULL, recommendation_flag INTEGER NOT NULL DEFAULT 0,
    near_trigger_flag INTEGER NOT NULL DEFAULT 0, watchlist_subscriber_count INTEGER NOT NULL DEFAULT 0,
    monitoring_priority INTEGER NOT NULL, active_from TEXT NOT NULL, active_until TEXT NOT NULL
);

COMMIT;
PRAGMA foreign_keys = ON;
