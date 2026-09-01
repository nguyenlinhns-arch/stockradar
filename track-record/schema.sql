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

