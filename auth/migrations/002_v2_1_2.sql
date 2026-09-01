-- One-time migration from the V2 auth/watchlist reference schema.
BEGIN IMMEDIATE;
ALTER TABLE users ADD COLUMN account_tier TEXT NOT NULL DEFAULT 'FREE';
ALTER TABLE users ADD COLUMN trial_started_at TEXT;
ALTER TABLE users ADD COLUMN trial_expires_at TEXT;
ALTER TABLE watchlist_items ADD COLUMN owns_stock INTEGER NOT NULL DEFAULT 0;
ALTER TABLE watchlist_items ADD COLUMN alert_enabled INTEGER NOT NULL DEFAULT 0;
CREATE TABLE user_preferences (
  user_id TEXT PRIMARY KEY REFERENCES users(user_id),
  preferred_horizons TEXT NOT NULL,
  preferred_sectors TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
COMMIT;
