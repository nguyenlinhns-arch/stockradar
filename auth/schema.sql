-- StockRadar authentication/watchlist reference contract.
-- Not executed by GitHub Pages. Prefer a reviewed managed auth provider in production.

PRAGMA foreign_keys = ON;

CREATE TABLE users (
  user_id TEXT PRIMARY KEY,
  email_normalized TEXT NOT NULL UNIQUE,
  email_verified_at TEXT,
  account_status TEXT NOT NULL CHECK (account_status IN ('PENDING', 'ACTIVE', 'SUSPENDED', 'DELETED')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  deleted_at TEXT
);

CREATE TABLE consent_receipts (
  consent_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  purpose TEXT NOT NULL CHECK (purpose IN ('TERMS', 'PRIVACY', 'PRODUCT_EMAIL', 'MARKETING_EMAIL')),
  document_version TEXT NOT NULL,
  granted INTEGER NOT NULL CHECK (granted IN (0, 1)),
  recorded_at TEXT NOT NULL,
  withdrawn_at TEXT
);

CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  token_hash TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL,
  expires_at TEXT NOT NULL,
  revoked_at TEXT
);

CREATE TABLE watchlist_items (
  watchlist_item_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL REFERENCES users(user_id),
  ticker TEXT NOT NULL,
  horizon TEXT NOT NULL CHECK (horizon IN ('SHORT_TERM', 'MEDIUM_TERM', 'LONG_TERM', 'ACCUMULATION')),
  email_enabled INTEGER NOT NULL DEFAULT 0 CHECK (email_enabled IN (0, 1)),
  created_at TEXT NOT NULL,
  removed_at TEXT,
  UNIQUE (user_id, ticker, horizon)
);

CREATE INDEX watchlist_by_user ON watchlist_items(user_id, removed_at);

-- Never store broker passwords, OTPs, trading tokens, orders, NAV or portfolio-control credentials.
