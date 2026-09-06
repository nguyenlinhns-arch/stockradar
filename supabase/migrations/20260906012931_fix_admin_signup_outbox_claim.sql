create or replace function public.claim_stockradar_admin_signup_outbox_v1(p_limit integer default 20)
returns table(
  outbox_id uuid,
  idempotency_key text,
  user_id uuid,
  recipient_email text,
  email_kind text,
  snapshot_id text,
  payload jsonb,
  expires_at timestamptz,
  decision_ref text
)
language plpgsql
security definer
set search_path to ''
as $$
begin
  if p_limit < 1 or p_limit > 100 then
    raise exception 'invalid claim limit';
  end if;

  update private.email_outbox o
     set status='FAILED', claim_started_at=null, last_error='CLAIM_TIMEOUT'
   where o.email_kind='ADMIN_FREE_SIGNUP'
     and status='PROCESSING'
     and claim_started_at < now() - interval '10 minutes';

  update private.email_outbox o
     set status='SUPPRESSED', claim_started_at=null, last_error='EXPIRED_BEFORE_SEND'
   where o.email_kind='ADMIN_FREE_SIGNUP'
     and status in ('PENDING','FAILED','PROCESSING')
     and o.expires_at <= now();

  update private.email_outbox o
     set status='SUPPRESSED', claim_started_at=null, last_error='MAX_ATTEMPTS'
   where o.email_kind='ADMIN_FREE_SIGNUP'
     and status='FAILED'
     and attempts >= 4;

  return query
  with candidates as (
    select o.id
      from private.email_outbox o
      join auth.users u on u.id=o.user_id
      cross join lateral (
        select lower(trim(c.approver_email)) as approver_email
          from private.checkout_approval_config c
         where c.singleton is true
           and nullif(trim(c.approver_email),'') is not null
         limit 1
      ) cfg
     where o.email_kind='ADMIN_FREE_SIGNUP'
       and o.status in ('PENDING','FAILED')
       and o.scheduled_at <= now()
       and o.expires_at > now()
       and o.attempts < 4
       and u.email is not null
     order by o.priority asc, o.scheduled_at asc, o.created_at asc
     for update of o skip locked
     limit p_limit
  ), claimed as (
    update private.email_outbox o
       set status='PROCESSING', attempts=attempts+1, claim_started_at=now(), last_error=null
      from candidates c
     where o.id=c.id
     returning o.*
  )
  select c.id,
         c.idempotency_key,
         c.user_id,
         cfg.approver_email,
         c.email_kind,
         c.snapshot_id,
         c.payload,
         c.expires_at,
         c.decision_ref
    from claimed c
    cross join lateral (
      select lower(trim(cc.approver_email)) as approver_email
        from private.checkout_approval_config cc
       where cc.singleton is true
         and nullif(trim(cc.approver_email),'') is not null
       limit 1
    ) cfg;
end;
$$;

revoke all on function public.claim_stockradar_admin_signup_outbox_v1(integer) from public, anon, authenticated;
grant execute on function public.claim_stockradar_admin_signup_outbox_v1(integer) to service_role;

create or replace function public.preflight_stockradar_admin_signup_outbox_v1(p_outbox_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $$
declare
  v_row private.email_outbox%rowtype;
  v_admin_email text;
begin
  if p_outbox_id is null then
    raise exception 'outbox_id required';
  end if;

  select * into v_row
    from private.email_outbox o
   where o.id=p_outbox_id
   for update;

  if v_row.id is null then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_FOUND');
  end if;
  if v_row.email_kind <> 'ADMIN_FREE_SIGNUP' then
    return jsonb_build_object('allowed',false,'reason','INVALID_EMAIL_KIND');
  end if;
  if v_row.status <> 'PROCESSING' then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_PROCESSING');
  end if;
  if v_row.expires_at <= now() then
    update private.email_outbox o
       set status='SUPPRESSED', claim_started_at=null, last_error='EXPIRED_AT_PREFLIGHT'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','EXPIRED_AT_PREFLIGHT');
  end if;

  select lower(trim(c.approver_email)) into v_admin_email
    from private.checkout_approval_config c
   where c.singleton is true
     and nullif(trim(c.approver_email),'') is not null
   limit 1;

  if v_admin_email is null then
    update private.email_outbox o
       set status='FAILED', claim_started_at=null, last_error='ADMIN_EMAIL_NOT_CONFIGURED'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','ADMIN_EMAIL_NOT_CONFIGURED');
  end if;

  return jsonb_build_object(
    'allowed',true,
    'reason',null,
    'email_kind',v_row.email_kind,
    'recipient_email',v_admin_email,
    'expires_at',v_row.expires_at,
    'payload',v_row.payload,
    'attempts',v_row.attempts
  );
end;
$$;

revoke all on function public.preflight_stockradar_admin_signup_outbox_v1(uuid) from public, anon, authenticated;
grant execute on function public.preflight_stockradar_admin_signup_outbox_v1(uuid) to service_role;


