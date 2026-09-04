-- Final fail-closed preflight immediately before a provider send.
-- This closes the race where delivery/consent/suppression changes after an outbox row was claimed.

create or replace function public.preflight_stockradar_email_outbox_v1(p_outbox_id uuid)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_row private.email_outbox%rowtype;
  v_elig private.product_email_eligibility%rowtype;
  v_verified boolean := false;
  v_allowed boolean := false;
  v_reason text := 'NOT_ELIGIBLE';
begin
  if p_outbox_id is null then raise exception 'outbox_id required'; end if;

  select * into v_row
  from private.email_outbox o
  where o.id = p_outbox_id
  for update;

  if v_row.id is null then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_FOUND');
  end if;
  if v_row.status <> 'PROCESSING' then
    return jsonb_build_object('allowed',false,'reason','OUTBOX_NOT_PROCESSING');
  end if;
  if v_row.expires_at <= now() then
    update private.email_outbox
       set status='SUPPRESSED',claim_started_at=null,last_error='EXPIRED_AT_PREFLIGHT'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','EXPIRED_AT_PREFLIGHT');
  end if;

  select (u.email_confirmed_at is not null and u.email is not null)
    into v_verified
  from auth.users u where u.id=v_row.user_id;
  if v_verified is not true then
    update private.email_outbox
       set status='SUPPRESSED',claim_started_at=null,last_error='EMAIL_NOT_VERIFIED_AT_PREFLIGHT'
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason','EMAIL_NOT_VERIFIED_AT_PREFLIGHT');
  end if;

  select * into v_elig
  from private.product_email_eligibility e
  where e.user_id=v_row.user_id;

  if v_elig.user_id is null then
    v_reason := 'NO_EMAIL_PREFERENCE_AT_PREFLIGHT';
  elsif v_row.email_kind='DAILY_BRIEF' and v_elig.eligible_to_send and v_elig.daily_brief then
    v_allowed := true;
  elsif v_row.email_kind='EVENT_ALERT' and v_elig.eligible_for_premium and v_elig.event_alerts then
    v_allowed := true;
  elsif v_row.email_kind='POST_SESSION_DIGEST' and v_elig.eligible_for_premium and v_elig.post_session_digest then
    v_allowed := true;
  elsif v_row.email_kind='WEEKLY_REPORT' and v_elig.eligible_for_premium and v_elig.weekly_report then
    v_allowed := true;
  elsif v_elig.suppression_reason is not null then
    v_reason := 'SUPPRESSED_AT_PREFLIGHT_' || v_elig.suppression_reason;
  elsif v_elig.sending_enabled is not true then
    v_reason := 'DELIVERY_DISABLED_AT_PREFLIGHT';
  elsif v_elig.latest_consent_granted is not true then
    v_reason := 'CONSENT_REVOKED_AT_PREFLIGHT';
  else
    v_reason := 'ENTITLEMENT_CHANGED_AT_PREFLIGHT';
  end if;

  if v_allowed is not true then
    update private.email_outbox
       set status='SUPPRESSED',claim_started_at=null,last_error=v_reason
     where id=v_row.id;
    return jsonb_build_object('allowed',false,'reason',v_reason);
  end if;

  return jsonb_build_object(
    'allowed',true,
    'reason',null,
    'email_kind',v_row.email_kind,
    'expires_at',v_row.expires_at,
    'attempts',v_row.attempts
  );
end;
$$;

revoke all on function public.preflight_stockradar_email_outbox_v1(uuid) from public,anon,authenticated;
grant execute on function public.preflight_stockradar_email_outbox_v1(uuid) to service_role;
