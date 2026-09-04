create or replace function public.get_my_stockradar_email_health_v1()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_user_id uuid := auth.uid();
  v_tier text;
  v_account_status text;
  v_pref_enabled boolean := false;
  v_daily boolean := false;
  v_alerts boolean := false;
  v_post_session boolean := false;
  v_weekly boolean := false;
  v_watchlist_count integer := 0;
  v_alert_ticker_count integer := 0;
  v_delivery_ready boolean := false;
  v_last_kind text;
  v_last_status text;
  v_last_at timestamptz;
  v_suppression text;
begin
  if v_user_id is null then
    raise exception 'authentication required';
  end if;

  select p.account_tier, p.account_status
    into v_tier, v_account_status
  from public.profiles p
  where p.id = v_user_id;

  select
    coalesce(ep.enabled, false),
    coalesce(ep.daily_brief, false),
    coalesce(ep.event_alerts, false),
    coalesce(ep.post_session_digest, false),
    coalesce(ep.weekly_report, false)
  into v_pref_enabled, v_daily, v_alerts, v_post_session, v_weekly
  from public.product_email_preferences ep
  where ep.user_id = v_user_id;

  select
    count(*)::integer,
    count(*) filter (where w.alert_enabled is true)::integer
  into v_watchlist_count, v_alert_ticker_count
  from public.watchlist_items w
  where w.user_id = v_user_id
    and w.removed_at is null;

  select (
    g.provider_configured is true
    and g.sender_domain_verified is true
    and g.unsubscribe_ready is true
    and g.bounce_complaint_ready is true
    and g.compliance_approved is true
    and g.sending_enabled is true
  )
  into v_delivery_ready
  from private.email_delivery_gate g
  where g.singleton is true;

  select o.email_kind, o.status, coalesce(o.sent_at, o.created_at)
  into v_last_kind, v_last_status, v_last_at
  from private.email_outbox o
  where o.user_id = v_user_id
  order by o.created_at desc
  limit 1;

  select s.reason
  into v_suppression
  from private.email_suppressions s
  where s.user_id = v_user_id
    and s.lifted_at is null
  order by s.created_at desc
  limit 1;

  return jsonb_build_object(
    'status', 'READY',
    'account_tier', coalesce(v_tier, 'FREE'),
    'account_status', coalesce(v_account_status, 'PENDING'),
    'preference_enabled', v_pref_enabled,
    'daily_brief', v_daily,
    'event_alerts', v_alerts,
    'post_session_digest', v_post_session,
    'weekly_report', v_weekly,
    'watchlist_count', v_watchlist_count,
    'alert_ticker_count', v_alert_ticker_count,
    'delivery_system_ready', coalesce(v_delivery_ready, false),
    'last_email_kind', v_last_kind,
    'last_delivery_status', v_last_status,
    'last_email_at', v_last_at,
    'suppression_reason', v_suppression
  );
end;
$$;

revoke all on function public.get_my_stockradar_email_health_v1() from public, anon;
grant execute on function public.get_my_stockradar_email_health_v1() to authenticated;
