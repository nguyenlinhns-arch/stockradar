PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS snapshots (
    snapshot_id TEXT PRIMARY KEY,
    as_of TEXT NOT NULL,
    source_timestamp TEXT NOT NULL,
    exchange TEXT NOT NULL CHECK (exchange = 'HOSE'),
    source TEXT NOT NULL,
    data_grade TEXT NOT NULL,
    universe_total INTEGER NOT NULL,
    scanned_total INTEGER NOT NULL,
    valid_total INTEGER NOT NULL,
    excluded_total INTEGER NOT NULL,
    coverage_pct REAL NOT NULL,
    market_regime TEXT NOT NULL,
    release_status TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS radar_entries (
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    rank INTEGER NOT NULL CHECK (rank >= 1),
    ticker TEXT NOT NULL,
    score REAL NOT NULL CHECK (score >= 0 AND score <= 100),
    score_coverage_pct REAL NOT NULL CHECK (score_coverage_pct >= 0 AND score_coverage_pct <= 100),
    setup TEXT NOT NULL,
    state TEXT NOT NULL,
    previous_state TEXT,
    state_change TEXT NOT NULL,
    current_price REAL,
    pivot REAL,
    reason TEXT NOT NULL,
    evidence_json TEXT NOT NULL,
    is_mock INTEGER NOT NULL DEFAULT 0 CHECK (is_mock IN (0, 1)),
    PRIMARY KEY (snapshot_id, ticker),
    UNIQUE (snapshot_id, rank)
);

CREATE TABLE IF NOT EXISTS corrections (
    correction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    created_at TEXT NOT NULL,
    reason TEXT NOT NULL,
    corrected_payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS performance_observations (
    observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    horizon TEXT NOT NULL,
    outcome_pct REAL,
    mae_pct REAL,
    mfe_pct REAL,
    r_multiple REAL,
    FOREIGN KEY (snapshot_id, ticker) REFERENCES radar_entries(snapshot_id, ticker)
);

CREATE TABLE IF NOT EXISTS state_changes (
    change_id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    ticker TEXT NOT NULL,
    changed_at TEXT NOT NULL,
    from_state TEXT NOT NULL,
    to_state TEXT NOT NULL,
    reason TEXT NOT NULL,
    UNIQUE (snapshot_id, ticker, from_state, to_state)
);

CREATE TABLE IF NOT EXISTS recommendations (
    recommendation_id TEXT PRIMARY KEY,
    snapshot_id TEXT NOT NULL REFERENCES snapshots(snapshot_id),
    ticker TEXT NOT NULL,
    horizon TEXT NOT NULL,
    publication_timestamp TEXT NOT NULL,
    recommended_buy_low REAL,
    recommended_buy_high REAL,
    price_at_publication REAL,
    generated_at TEXT NOT NULL,
    published_at TEXT NOT NULL,
    system_version TEXT NOT NULL,
    score_version TEXT NOT NULL,
    publish_status TEXT NOT NULL,
    record_mode TEXT NOT NULL CHECK (record_mode IN ('BACKTEST', 'SHADOW', 'LIVE_PUBLISHED')),
    data_grade TEXT NOT NULL,
    raw_payload TEXT NOT NULL,
    is_mock INTEGER NOT NULL DEFAULT 0 CHECK (is_mock IN (0, 1))
);

CREATE TABLE IF NOT EXISTS recommendation_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('PUBLISHED', 'ACTIVATED', 'OBSERVED', 'TARGET_REACHED', 'STOP_REACHED', 'INVALIDATED', 'EXPIRED', 'CLOSED', 'CORRECTION')),
    event_at TEXT NOT NULL,
    state TEXT NOT NULL,
    performance_entry_price REAL,
    observed_price REAL,
    current_return_pct REAL,
    close_price REAL,
    final_return_pct REAL,
    reason TEXT,
    payload_json TEXT NOT NULL,
    UNIQUE (recommendation_id, event_type, event_at)
);

CREATE TABLE IF NOT EXISTS corporate_actions (
    action_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    action_type TEXT NOT NULL,
    effective_at TEXT NOT NULL,
    price_factor REAL NOT NULL DEFAULT 1,
    cash_per_share REAL NOT NULL DEFAULT 0,
    source_ref TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0 CHECK (resolved IN (0, 1)),
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS benchmark_observations (
    benchmark_observation_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id),
    observed_at TEXT NOT NULL,
    benchmark_code TEXT NOT NULL,
    benchmark_return_pct REAL NOT NULL,
    stock_return_pct REAL NOT NULL,
    excess_return_pct REAL NOT NULL,
    UNIQUE (recommendation_id, observed_at, benchmark_code)
);

CREATE TABLE IF NOT EXISTS manual_overrides (
    override_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id),
    created_at TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS immutable_snapshots_update
BEFORE UPDATE ON snapshots BEGIN
    SELECT RAISE(ABORT, 'snapshots are immutable; append a correction');
END;

CREATE TRIGGER IF NOT EXISTS immutable_snapshots_delete
BEFORE DELETE ON snapshots BEGIN
    SELECT RAISE(ABORT, 'snapshots are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_entries_update
BEFORE UPDATE ON radar_entries BEGIN
    SELECT RAISE(ABORT, 'radar entries are immutable; append a correction');
END;

CREATE TRIGGER IF NOT EXISTS immutable_entries_delete
BEFORE DELETE ON radar_entries BEGIN
    SELECT RAISE(ABORT, 'radar entries are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_state_changes_update
BEFORE UPDATE ON state_changes BEGIN
    SELECT RAISE(ABORT, 'state changes are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_state_changes_delete
BEFORE DELETE ON state_changes BEGIN
    SELECT RAISE(ABORT, 'state changes are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_recommendations_update
BEFORE UPDATE ON recommendations BEGIN
    SELECT RAISE(ABORT, 'recommendations are immutable; append an event or correction');
END;

CREATE TRIGGER IF NOT EXISTS immutable_recommendations_delete
BEFORE DELETE ON recommendations BEGIN
    SELECT RAISE(ABORT, 'recommendations are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_recommendation_events_update
BEFORE UPDATE ON recommendation_events BEGIN
    SELECT RAISE(ABORT, 'recommendation events are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_recommendation_events_delete
BEFORE DELETE ON recommendation_events BEGIN
    SELECT RAISE(ABORT, 'recommendation events are immutable');
END;
