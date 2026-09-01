-- StockRadar 30-day subscription reference contract.
-- No checkout or payment write is enabled on the public static website.

PRAGMA foreign_keys = ON;

CREATE TABLE plans (
  plan_id TEXT PRIMARY KEY,
  plan_code TEXT NOT NULL UNIQUE CHECK (plan_code IN ('FREE', 'ADVANCED_TEST', 'ADVANCED_STANDARD')),
  price_vnd INTEGER NOT NULL CHECK (price_vnd >= 0),
  duration_days INTEGER NOT NULL CHECK (duration_days IN (0, 30)),
  active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
  created_at TEXT NOT NULL
);

CREATE TABLE payment_events (
  payment_event_id TEXT PRIMARY KEY,
  provider_event_id TEXT NOT NULL UNIQUE,
  user_id TEXT NOT NULL,
  plan_id TEXT NOT NULL REFERENCES plans(plan_id),
  amount_vnd INTEGER NOT NULL CHECK (amount_vnd >= 0),
  status TEXT NOT NULL CHECK (status IN ('PENDING', 'PAID', 'FAILED', 'REFUNDED', 'CHARGEBACK')),
  occurred_at TEXT NOT NULL,
  verified_at TEXT,
  raw_payload_hash TEXT NOT NULL
);

CREATE TABLE subscription_grants (
  grant_id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  payment_event_id TEXT NOT NULL UNIQUE REFERENCES payment_events(payment_event_id),
  starts_at TEXT NOT NULL,
  ends_at TEXT NOT NULL,
  granted_days INTEGER NOT NULL CHECK (granted_days = 30),
  created_at TEXT NOT NULL,
  revoked_at TEXT,
  revoke_reason TEXT
);

CREATE INDEX grants_by_user ON subscription_grants(user_id, ends_at);

-- Entitlement is derived from verified, non-revoked grants. Replayed provider events
-- must not extend access twice. Refund/chargeback handling appends a revocation record;
-- it does not delete the original payment event.
