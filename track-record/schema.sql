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
    review_due_at TEXT,
    review_status TEXT NOT NULL DEFAULT 'PENDING' CHECK (review_status IN ('PENDING', 'DUE', 'COMPLETED', 'OVERDUE')),
    review_decision TEXT CHECK (review_decision IN ('CONTINUE', 'ADJUST', 'NO_LONGER_ELIGIBLE', 'CLOSE')),
    new_position_state TEXT NOT NULL DEFAULT 'NOT_ASSESSED',
    holding_state TEXT NOT NULL DEFAULT 'NOT_ASSESSED',
    vnindex_at_activation REAL,
    vnindex_current_or_close REAL,
    raw_payload TEXT NOT NULL,
    is_mock INTEGER NOT NULL DEFAULT 0 CHECK (is_mock IN (0, 1))
);

CREATE TABLE IF NOT EXISTS recommendation_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id),
    event_type TEXT NOT NULL CHECK (event_type IN ('WATCHED', 'WAIT_BUY', 'PUBLISHED', 'ACTIVATED', 'OBSERVED', 'SCORE_CHANGED', 'TARGET_CHANGED', 'REVIEWED', 'TARGET_REACHED', 'STOP_REACHED', 'INVALIDATED', 'EXPIRED', 'CLOSED', 'CORRECTION')),
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

CREATE TABLE IF NOT EXISTS benchmark_records (
    benchmark_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    recommendation_id TEXT NOT NULL REFERENCES recommendations(recommendation_id),
    benchmark TEXT NOT NULL DEFAULT 'VNINDEX',
    start_value REAL NOT NULL,
    current_or_close_value REAL NOT NULL,
    return_pct REAL NOT NULL,
    excess_return_pct REAL NOT NULL,
    calculated_at TEXT NOT NULL,
    UNIQUE (recommendation_id, benchmark, calculated_at)
);

CREATE TABLE IF NOT EXISTS review_schedule (
    recommendation_id TEXT PRIMARY KEY REFERENCES recommendations(recommendation_id),
    review_due_at TEXT NOT NULL,
    review_status TEXT NOT NULL CHECK (review_status IN ('PENDING', 'DUE', 'COMPLETED', 'OVERDUE')),
    reviewed_at TEXT,
    review_decision TEXT CHECK (review_decision IN ('CONTINUE', 'ADJUST', 'NO_LONGER_ELIGIBLE', 'CLOSE'))
);

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
);

CREATE TABLE IF NOT EXISTS ticker_search_log (
    search_id INTEGER PRIMARY KEY AUTOINCREMENT,
    searched_at TEXT NOT NULL,
    ticker TEXT NOT NULL,
    session_id TEXT,
    user_id TEXT,
    source TEXT NOT NULL,
    campaign TEXT,
    result_status TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_popularity (
    ticker TEXT PRIMARY KEY,
    search_count INTEGER NOT NULL DEFAULT 0,
    unique_searchers INTEGER NOT NULL DEFAULT 0,
    watchlist_count INTEGER NOT NULL DEFAULT 0,
    trial_count INTEGER NOT NULL DEFAULT 0,
    paid_count INTEGER NOT NULL DEFAULT 0,
    calculated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS monitored_tickers (
    ticker TEXT PRIMARY KEY,
    monitoring_status TEXT NOT NULL,
    last_evaluated_at TEXT,
    next_evaluation_at TEXT
);

CREATE TABLE IF NOT EXISTS ticker_subscribers (
    ticker TEXT NOT NULL REFERENCES monitored_tickers(ticker),
    user_id TEXT NOT NULL,
    subscription_tier TEXT NOT NULL CHECK (subscription_tier IN ('TRIAL', 'PAID')),
    alert_enabled INTEGER NOT NULL DEFAULT 1 CHECK (alert_enabled IN (0, 1)),
    PRIMARY KEY (ticker, user_id)
);

CREATE TABLE IF NOT EXISTS ticker_state (
    ticker TEXT PRIMARY KEY REFERENCES monitored_tickers(ticker),
    snapshot_id TEXT NOT NULL,
    state_payload TEXT NOT NULL,
    calculated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticker_events (
    ticker_event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL REFERENCES monitored_tickers(ticker),
    event_type TEXT NOT NULL,
    event_at TEXT NOT NULL,
    previous_value TEXT,
    new_value TEXT,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_jobs (
    notification_job_id TEXT PRIMARY KEY,
    ticker_event_id INTEGER NOT NULL REFERENCES ticker_events(ticker_event_id),
    audience_tier TEXT NOT NULL CHECK (audience_tier IN ('TRIAL', 'PAID')),
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'SENDING', 'SENT', 'FAILED', 'SUPPRESSED')),
    idempotency_key TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    completed_at TEXT
);

CREATE TABLE IF NOT EXISTS active_intraday_universe (
    ticker TEXT PRIMARY KEY,
    reason TEXT NOT NULL,
    recommendation_flag INTEGER NOT NULL DEFAULT 0 CHECK (recommendation_flag IN (0, 1)),
    near_trigger_flag INTEGER NOT NULL DEFAULT 0 CHECK (near_trigger_flag IN (0, 1)),
    watchlist_subscriber_count INTEGER NOT NULL DEFAULT 0,
    monitoring_priority INTEGER NOT NULL,
    active_from TEXT NOT NULL,
    active_until TEXT NOT NULL
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

CREATE TRIGGER IF NOT EXISTS immutable_ticker_events_update
BEFORE UPDATE ON ticker_events BEGIN
    SELECT RAISE(ABORT, 'ticker events are immutable');
END;

CREATE TRIGGER IF NOT EXISTS immutable_ticker_events_delete
BEFORE DELETE ON ticker_events BEGIN
    SELECT RAISE(ABORT, 'ticker events are immutable');
END;
