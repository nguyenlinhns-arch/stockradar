-- Canonical report fields are refreshed immediately before provider submission.
create or replace function private.stockradar_email_price_plan_v1(p_report jsonb, p_horizon text)
returns jsonb language sql immutable set search_path = '' as $$
select jsonb_build_object(
 'horizon',p_horizon,'stop',p_report->'stop_loss','stop_loss',p_report->'stop_loss',
 'target_near',p_report->'target_near','target_3_6m',p_report->'target_3_6m',
 'target_12m',p_report->'target_12m','target_price',p_report->'target_price',
 'target',case p_horizon when 'MEDIUM_TERM' then p_report->'target_3_6m'
   when 'LONG_TERM' then p_report->'target_12m' when 'ACCUMULATION' then p_report->'target_price'
   else coalesce(nullif(p_report->'target_near','null'::jsonb),p_report->'target_price') end,
 'setup',p_report->'setup','position_initial_pct',p_report->'position_initial_pct',
 'upside_pct',p_report->'upside_pct','downside_pct',p_report->'downside_pct',
 'risk_reward',coalesce(nullif(p_report->'risk_reward','null'::jsonb),p_report->'risk_reward_to_base'),
 'as_of_date',p_report->'as_of_date','source_updated_at',p_report->'source_updated_at',
 'data_freshness',p_report->'data_freshness','expected_holding_period',p_report->'expected_holding_period');
$$;
revoke all on function private.stockradar_email_price_plan_v1(jsonb,text) from public,anon,authenticated;

-- Bounded public metadata only: never expose bank details, approval tokens or identities.
create or replace function public.get_stockradar_product_readiness_v1()
returns jsonb language plpgsql stable security definer set search_path = '' as $$
declare
 s jsonb := public.get_stockradar_recommendation_status_v1();
 b private.billing_gate%rowtype; g private.stock_api_gate%rowtype;
 billing_ready boolean := false; product_ready boolean := false; mail_ready boolean := false;
begin
 select * into b from private.billing_gate where singleton;
 select * into g from private.stock_api_gate where singleton;
 billing_ready := coalesce(b.checkout_enabled and b.provider_configured
   and b.reconciliation_ready and b.refund_chargeback_ready and b.tax_compliance_approved
   and upper(b.provider_name)='MANUAL_VIETQR'
   and exists(select 1 from private.manual_checkout_config where singleton and enabled)
   and exists(select 1 from private.checkout_approval_config where singleton and enabled
     and nullif(function_url,'') is not null and nullif(hook_token,'') is not null),false);
 product_ready := coalesce(g.api_enabled and g.data_ready and g.data_rights_approved and g.compliance_approved
   and (s#>>'{snapshot,fresh}')::boolean and g.active_snapshot_id is not null and g.active_manifest_ref is not null
   and exists(select 1 from private.stock_report_cache c where c.snapshot_id=g.active_snapshot_id
     and c.source_manifest_ref=g.active_manifest_ref and c.expires_at>now()
     and c.payload->>'data_grade'='DECISION_GRADE' and c.payload->>'public_release_allowed'='true'
     and c.payload->>'data_freshness'='FRESH'),false);
 mail_ready := coalesce((s#>>'{email,ready}')::boolean,false);
 return jsonb_build_object('schema_version','STOCKRADAR_PRODUCT_READINESS_V1','checked_at',now(),
   'checkout_ready',billing_ready and product_ready and mail_ready,
   'billing_ready',billing_ready,'product_ready',product_ready,'email_ready',mail_ready,
   'status',case when billing_ready and product_ready and mail_ready then 'READY' else 'PAUSED' end);
end;
$$;
revoke all on function public.get_stockradar_product_readiness_v1() from public;
grant execute on function public.get_stockradar_product_readiness_v1() to anon,authenticated,service_role;

-- Premium remains unlimited per day; this independent technical burst limit protects inference.
insert into private.stock_api_rate_limit_policies(account_tier,bucket,requests_per_window,window_seconds,active)
values ('FREE','stock_ai_burst',30,60,true),('TRIAL','stock_ai_burst',30,60,true),('PAID','stock_ai_burst',30,60,true)
on conflict(account_tier,bucket) do update set requests_per_window=excluded.requests_per_window,
 window_seconds=excluded.window_seconds,active=true,updated_at=now();

CREATE OR REPLACE FUNCTION public.create_my_checkout_request(p_plan_code text DEFAULT 'ADVANCED_TEST'::text)
 RETURNS jsonb
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO ''
AS $function$
declare
  uid uuid := auth.uid();
  plan_row private.billing_plans%rowtype;
  gate_row private.billing_gate%rowtype;
  config_row private.manual_checkout_config%rowtype;
  request_row private.checkout_requests%rowtype;
  reference_value text;
  paid_until_value timestamptz;
begin
  if uid is null then
    raise exception 'AUTH_REQUIRED';
  end if;

  if not exists (
    select 1 from auth.users u
    where u.id = uid and u.email_confirmed_at is not null
  ) then
    raise exception 'EMAIL_VERIFICATION_REQUIRED';
  end if;

  if not exists (
    select 1 from public.profiles p
    where p.id = uid and p.account_status = 'ACTIVE'
  ) then
    raise exception 'ACCOUNT_NOT_ACTIVE';
  end if;

  select * into gate_row
  from private.billing_gate
  where singleton is true;

  select * into config_row
  from private.manual_checkout_config
  where singleton is true;

  if coalesce((public.get_stockradar_product_readiness_v1()->>'checkout_ready')::boolean,false) is not true
     or gate_row.checkout_enabled is not true
     or upper(coalesce(gate_row.provider_name, '')) <> 'MANUAL_VIETQR'
     or config_row.enabled is not true then
    raise exception 'CHECKOUT_DISABLED';
  end if;

  select * into plan_row
  from private.billing_plans
  where plan_code = upper(trim(coalesce(p_plan_code, '')))
    and active is true;

  if plan_row.id is null then
    raise exception 'PLAN_NOT_AVAILABLE';
  end if;

  update private.checkout_requests
  set status = 'EXPIRED', updated_at = now()
  where user_id = uid
    and status in ('PENDING','USER_CONFIRMED')
    and expires_at <= now();

  select * into request_row
  from private.checkout_requests
  where user_id = uid
    and plan_id = plan_row.id
    and status in ('PENDING','USER_CONFIRMED')
    and expires_at > now()
  order by created_at desc
  limit 1;

  if request_row.id is null then
    loop
      reference_value := 'SR' || to_char(now(), 'YYMMDD') || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 8));
      exit when not exists (
        select 1 from private.checkout_requests r where r.payment_reference = reference_value
      );
    end loop;

    insert into private.checkout_requests (
      user_id, plan_id, amount_vnd, payment_reference, status, expires_at
    ) values (
      uid, plan_row.id, plan_row.price_vnd, reference_value, 'PENDING', now() + interval '30 minutes'
    )
    returning * into request_row;
  end if;

  select e.paid_until into paid_until_value
  from private.current_paid_entitlements e
  where e.user_id = uid;

  return jsonb_build_object(
    'checkout_enabled', true,
    'request_id', request_row.id,
    'status', request_row.status,
    'amount_vnd', request_row.amount_vnd,
    'duration_days', plan_row.duration_days,
    'plan_code', plan_row.plan_code,
    'payment_reference', request_row.payment_reference,
    'expires_at', request_row.expires_at,
    'bank_bin', config_row.bank_bin,
    'bank_name', config_row.bank_name,
    'account_number', config_row.account_number,
    'account_name', config_row.account_name,
    'paid_until', paid_until_value
  );
end;
$function$
;

create or replace function private.enqueue_stockradar_daily_briefs_v1(p_at timestamptz default now())
returns jsonb language plpgsql security definer set search_path = '' as $$
declare
  v_local timestamp := p_at at time zone 'Asia/Ho_Chi_Minh';
  v_status jsonb; v_payload jsonb; v_key text; v_id uuid;
  v_scheduled timestamptz; v_enqueued integer := 0; r record;
begin
  if extract(isodow from v_local) not between 1 and 5 or v_local::time < time '09:00' or v_local::time >= time '09:30' then
    return jsonb_build_object('status','OUTSIDE_DAILY_WINDOW','enqueued',0);
  end if;
  perform pg_advisory_xact_lock(hashtextextended('stockradar-daily-brief-v1',0));
  v_status := public.get_stockradar_recommendation_status_v1();
  if coalesce(v_status#>>'{email,ready}','false') <> 'true' then
    return jsonb_build_object('status','EMAIL_DISABLED','enqueued',0);
  end if;
  if coalesce(v_status#>>'{snapshot,fresh}','false') <> 'true' then
    return jsonb_build_object('status','NO_FRESH_REVIEW','enqueued',0);
  end if;
  v_scheduled := (v_local::date + time '09:00') at time zone 'Asia/Ho_Chi_Minh';
  v_payload := jsonb_build_object('subject','[StockRadar] Bản tin cổ phiếu ' || to_char(v_local::date,'DD/MM/YYYY'),
    'headline',case when jsonb_array_length(v_status->'items')>0 then jsonb_array_length(v_status->'items') || ' mã được xác nhận mua' else 'Chưa có mã được xác nhận mua' end,
    'as_of_date',v_status#>'{snapshot,as_of_date}','market_session_reference',v_status#>'{snapshot,as_of_date}',
    'report_date',v_local::date,'generated_at',p_at,'evaluated_at',v_status#>'{snapshot,evaluated_at}',
    'next_review_at',v_status#>'{schedule,next_review_at}','opportunities',v_status->'items',
    'watchlist_changes','[]'::jsonb,'coverage',v_status->'coverage',
    'action_snapshot_id',(select active_snapshot_id from private.stock_api_gate where singleton),
    'action_manifest_ref',(select active_manifest_ref from private.stock_api_gate where singleton));
  for r in select e.user_id from private.product_email_eligibility e
    join auth.users u on u.id=e.user_id and u.email_confirmed_at is not null
    where e.eligible_to_send and e.daily_brief
  loop
    v_key := 'daily-v1-' || md5(r.user_id::text || '|' || v_local::date::text);
    if exists(select 1 from private.email_outbox where idempotency_key=v_key) then continue; end if;
    v_id := public.enqueue_stockradar_email_v2(r.user_id,'DAILY_BRIEF',v_key,
      v_status#>>'{snapshot,snapshot_id}',v_payload,v_scheduled,v_scheduled+interval '2 hours',30,'daily:' || v_local::date::text);
    if v_id is not null then v_enqueued := v_enqueued+1; end if;
  end loop;
  return jsonb_build_object('status','PROCESSED','enqueued',v_enqueued,'scheduled_at',v_scheduled);
end;
$$;
revoke all on function private.enqueue_stockradar_daily_briefs_v1(timestamptz) from public,anon,authenticated;
