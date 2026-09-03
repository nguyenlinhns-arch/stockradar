create table private.billing_gate (
  singleton boolean primary key default true check (singleton),
  provider_name text,
  provider_configured boolean not null default false,
  webhook_signature_verified boolean not null default false,
  reconciliation_ready boolean not null default false,
  refund_chargeback_ready boolean not null default false,
  tax_compliance_approved boolean not null default false,
  checkout_enabled boolean not null default false,
  evidence_ref text,
  updated_at timestamptz not null default now(),
  constraint billing_gate_safe_enable check (
    not checkout_enabled or (
      provider_configured
      and webhook_signature_verified
      and reconciliation_ready
      and refund_chargeback_ready
      and tax_compliance_approved
      and length(trim(coalesce(provider_name, ''))) > 0
      and length(trim(coalesce(evidence_ref, ''))) > 0
    )
  )
);

insert into private.billing_gate (singleton)
values (true)
on conflict (singleton) do nothing;

create table private.billing_plans (
  id uuid primary key default gen_random_uuid(),
  plan_code text not null unique check (plan_code in ('ADVANCED_TEST','ADVANCED_STANDARD')),
  price_vnd integer not null check (price_vnd > 0),
  duration_days integer not null default 30 check (duration_days = 30),
  active boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table private.payment_events (
  id uuid primary key default gen_random_uuid(),
  provider_name text not null,
  provider_event_id text not null,
  user_id uuid not null references auth.users(id) on delete restrict,
  plan_id uuid not null references private.billing_plans(id) on delete restrict,
  amount_vnd integer not null check (amount_vnd > 0),
  status text not null check (status in ('PENDING','PAID','FAILED','REFUNDED','CHARGEBACK')),
  occurred_at timestamptz not null,
  verified_at timestamptz,
  raw_payload_sha256 text not null check (raw_payload_sha256 ~ '^[0-9a-f]{64}$'),
  created_at timestamptz not null default now(),
  unique (provider_name, provider_event_id)
);

create table private.subscription_grants (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete restrict,
  payment_event_id uuid not null unique references private.payment_events(id) on delete restrict,
  starts_at timestamptz not null,
  ends_at timestamptz not null,
  granted_days integer not null default 30 check (granted_days = 30),
  created_at timestamptz not null default now(),
  revoked_at timestamptz,
  revoke_reason text,
  constraint subscription_grant_window check (ends_at > starts_at)
);

create index subscription_grants_by_user
  on private.subscription_grants(user_id, ends_at desc);

create view private.current_paid_entitlements
with (security_invoker = true)
as
select
  grant_row.user_id,
  max(grant_row.ends_at) as paid_until
from private.subscription_grants grant_row
join private.payment_events payment on payment.id = grant_row.payment_event_id
where grant_row.revoked_at is null
  and payment.status = 'PAID'
  and payment.verified_at is not null
  and grant_row.starts_at <= now()
  and grant_row.ends_at > now()
group by grant_row.user_id;

alter table private.billing_gate enable row level security;
alter table private.billing_plans enable row level security;
alter table private.payment_events enable row level security;
alter table private.subscription_grants enable row level security;

revoke all on table private.billing_gate from public, anon, authenticated;
revoke all on table private.billing_plans from public, anon, authenticated;
revoke all on table private.payment_events from public, anon, authenticated;
revoke all on table private.subscription_grants from public, anon, authenticated;
revoke all on private.current_paid_entitlements from public, anon, authenticated;
