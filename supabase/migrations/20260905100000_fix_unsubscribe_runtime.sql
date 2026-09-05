-- Fix empty search_path crypto lookups and disabling the last selected email product atomically.
create or replace function public.issue_stockradar_unsubscribe_token_v1(
  p_user_id uuid,
  p_scope text,
  p_ttl_days integer default 90
)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_scope text := upper(trim(coalesce(p_scope,'')));
  v_token text;
begin
  if p_user_id is null then raise exception 'user required'; end if;
  if v_scope not in ('DAILY_BRIEF','EVENT_ALERT','POST_SESSION_DIGEST','WEEKLY_REPORT','ALL') then
    raise exception 'invalid unsubscribe scope';
  end if;
  if p_ttl_days < 1 or p_ttl_days > 365 then raise exception 'invalid token ttl'; end if;

  v_token := replace(gen_random_uuid()::text,'-','') || replace(gen_random_uuid()::text,'-','');

  update private.email_unsubscribe_tokens
     set used_at = now()
   where user_id = p_user_id and scope = v_scope and used_at is null;

  insert into private.email_unsubscribe_tokens(user_id,scope,token_hash,expires_at)
  values (p_user_id,v_scope,encode(extensions.digest(v_token,'sha256'),'hex'),now() + make_interval(days => p_ttl_days));

  return v_token;
end;
$$;

revoke all on function public.issue_stockradar_unsubscribe_token_v1(uuid,text,integer) from public, anon, authenticated;
grant execute on function public.issue_stockradar_unsubscribe_token_v1(uuid,text,integer) to service_role;

create or replace function public.apply_stockradar_unsubscribe_v1(p_token text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_row private.email_unsubscribe_tokens%rowtype;
  v_enabled boolean;
begin
  if length(trim(coalesce(p_token,''))) <> 64 then
    return jsonb_build_object('status','INVALID_TOKEN');
  end if;

  select * into v_row
  from private.email_unsubscribe_tokens t
  where t.token_hash = encode(extensions.digest(trim(p_token),'sha256'),'hex')
    and t.used_at is null
    and t.expires_at > now()
  for update;

  if v_row.id is null then
    return jsonb_build_object('status','INVALID_OR_EXPIRED');
  end if;

  if v_row.scope = 'ALL' then
    update public.product_email_preferences
       set enabled=false,daily_brief=false,event_alerts=false,post_session_digest=false,weekly_report=false,updated_at=now()
     where user_id=v_row.user_id;

    insert into private.email_suppressions(user_id,reason,source_ref,created_at,lifted_at)
    values(v_row.user_id,'UNSUBSCRIBE','ONE_CLICK_ALL',now(),null)
    on conflict (user_id) do update
      set reason='UNSUBSCRIBE',source_ref='ONE_CLICK_ALL',created_at=now(),lifted_at=null;

    insert into public.product_email_consent_events(user_id,granted,document_version,source)
    select v_row.user_id,false,g.current_consent_version,'UNSUBSCRIBE'
    from private.email_delivery_gate g where g.singleton is true;
  else
    update public.product_email_preferences
       set enabled=enabled and ((v_row.scope<>'DAILY_BRIEF' and daily_brief) or (v_row.scope<>'EVENT_ALERT' and event_alerts) or (v_row.scope<>'POST_SESSION_DIGEST' and post_session_digest) or (v_row.scope<>'WEEKLY_REPORT' and weekly_report)),
           daily_brief = case when v_row.scope='DAILY_BRIEF' then false else daily_brief end,
           event_alerts = case when v_row.scope='EVENT_ALERT' then false else event_alerts end,
           post_session_digest = case when v_row.scope='POST_SESSION_DIGEST' then false else post_session_digest end,
           weekly_report = case when v_row.scope='WEEKLY_REPORT' then false else weekly_report end,
           updated_at=now()
     where user_id=v_row.user_id;

    select (daily_brief or event_alerts or post_session_digest or weekly_report)
      into v_enabled
    from public.product_email_preferences where user_id=v_row.user_id;

    if coalesce(v_enabled,false) is false then
      update public.product_email_preferences set enabled=false,updated_at=now() where user_id=v_row.user_id;
    end if;
  end if;

  update private.email_unsubscribe_tokens set used_at=now() where id=v_row.id;
  return jsonb_build_object('status','UNSUBSCRIBED','scope',v_row.scope);
end;
$$;

revoke all on function public.apply_stockradar_unsubscribe_v1(text) from public, anon, authenticated;
grant execute on function public.apply_stockradar_unsubscribe_v1(text) to service_role;
