-- Cover foreign keys used by email and billing workflows.
-- Applied to production via Supabase migration 20260904040702.

create index if not exists email_outbox_user_id_idx
  on private.email_outbox (user_id);

create index if not exists email_subscription_intents_verified_user_id_idx
  on private.email_subscription_intents (verified_user_id);

create index if not exists payment_events_plan_id_idx
  on private.payment_events (plan_id);

create index if not exists payment_events_user_id_idx
  on private.payment_events (user_id);
