create table if not exists private.checkout_approval_config (
  singleton boolean primary key default true check (singleton),
  approver_email text not null,
  function_url text not null,
  hook_token text not null,
  enabled boolean not null default true,
  updated_at timestamptz not null default now()
);

alter table private.checkout_approval_config enable row level security;
revoke all on table private.checkout_approval_config from public, anon, authenticated;

create table if not exists private.checkout_approvals (
  checkout_id uuid primary key references private.checkout_requests(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  token_hash text not null unique,
  status text not null default 'PENDING' check (status in ('PENDING','APPROVED','REJECTED','EXPIRED')),
  expires_at timestamptz not null,
  sent_at timestamptz,
  decided_at timestamptz,
  email_message_id text,
  send_attempts integer not null default 0 check (send_attempts >= 0),
  last_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists checkout_approvals_status_expiry_idx
  on private.checkout_approvals(status, expires_at);
create index if not exists checkout_approvals_user_created_idx
  on private.checkout_approvals(user_id, created_at desc);

alter table private.checkout_approvals enable row level security;
revoke all on table private.checkout_approvals from public, anon, authenticated;

insert into private.checkout_approval_config (
  singleton, approver_email, function_url, hook_token, enabled
)
values (
  true,
  'nguyenlinhns@gmail.com',
  'https://xamviatbxufjlpiwhebb.supabase.co/functions/v1/checkout-approval',
  encode(gen_random_bytes(32), 'hex'),
  true
)
on conflict (singleton) do update set
  approver_email = excluded.approver_email,
  function_url = excluded.function_url,
  enabled = true,
  updated_at = now();
