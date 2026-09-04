-- Preserve provider/payment and entitlement audit records without blocking a
-- user's right to delete their StockRadar account. Billing rows remain for
-- reconciliation but lose their direct auth.users link when the user is gone.

alter table private.payment_events
  alter column user_id drop not null;
alter table private.subscription_grants
  alter column user_id drop not null;

alter table private.payment_events
  drop constraint payment_events_user_id_fkey;
alter table private.payment_events
  add constraint payment_events_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete set null;

alter table private.subscription_grants
  drop constraint subscription_grants_user_id_fkey;
alter table private.subscription_grants
  add constraint subscription_grants_user_id_fkey
  foreign key (user_id) references auth.users(id) on delete set null;
