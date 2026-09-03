alter table private.stock_api_gate
  add column active_manifest_ref text,
  add column active_snapshot_id text;

alter table private.stock_api_gate
  drop constraint stock_api_gate_safe_enable;

alter table private.stock_api_gate
  add constraint stock_api_gate_safe_enable check (
    not api_enabled or (
      data_ready
      and data_rights_approved
      and compliance_approved
      and length(trim(coalesce(evidence_ref, ''))) > 0
      and length(trim(coalesce(active_manifest_ref, ''))) > 0
      and length(trim(coalesce(active_snapshot_id, ''))) > 0
    )
  );

create or replace function public.upsert_stockradar_cached_report(
  p_ticker text,
  p_horizon text,
  p_snapshot_id text,
  p_generated_at timestamptz,
  p_expires_at timestamptz,
  p_payload jsonb,
  p_source_manifest_ref text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ticker text := upper(trim(coalesce(p_ticker, '')));
  v_horizon text := upper(trim(coalesce(p_horizon, '')));
begin
  if v_ticker !~ '^[A-Z]{3}$' then
    raise exception 'invalid ticker';
  end if;
  if v_horizon not in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION') then
    raise exception 'invalid horizon';
  end if;
  if length(trim(coalesce(p_snapshot_id, ''))) = 0 then
    raise exception 'snapshot_id is required';
  end if;
  if p_generated_at is null or p_expires_at is null or p_expires_at <= p_generated_at then
    raise exception 'invalid cache time window';
  end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then
    raise exception 'payload must be a JSON object';
  end if;
  if length(trim(coalesce(p_source_manifest_ref, ''))) = 0 then
    raise exception 'source_manifest_ref is required';
  end if;

  insert into private.stock_report_cache(
    ticker, horizon, snapshot_id, generated_at, expires_at, payload, source_manifest_ref
  ) values (
    v_ticker, v_horizon, trim(p_snapshot_id), p_generated_at, p_expires_at, p_payload, trim(p_source_manifest_ref)
  )
  on conflict (ticker, horizon) do update
    set snapshot_id = excluded.snapshot_id,
        generated_at = excluded.generated_at,
        expires_at = excluded.expires_at,
        payload = excluded.payload,
        source_manifest_ref = excluded.source_manifest_ref;
end;
$$;

create or replace function public.fetch_stockradar_cached_report(
  p_ticker text,
  p_horizon text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ticker text := upper(trim(coalesce(p_ticker, '')));
  v_horizon text := upper(trim(coalesce(p_horizon, '')));
  v_gate private.stock_api_gate%rowtype;
  v_report private.stock_report_cache%rowtype;
begin
  if v_ticker !~ '^[A-Z]{3}$' then
    return jsonb_build_object('status', 'INVALID_REQUEST', 'reason', 'INVALID_TICKER');
  end if;
  if v_horizon not in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION') then
    return jsonb_build_object('status', 'INVALID_REQUEST', 'reason', 'INVALID_HORIZON');
  end if;

  select * into v_gate from private.stock_api_gate where singleton is true;
  if v_gate.api_enabled is not true then
    return jsonb_build_object('status', 'BLOCKED_DATA_GATE', 'reason', 'PRODUCTION_API_DISABLED');
  end if;

  select * into v_report
  from private.stock_report_cache
  where ticker = v_ticker and horizon = v_horizon;

  if v_report.ticker is null then
    return jsonb_build_object('status', 'NOT_FOUND', 'ticker', v_ticker, 'horizon', v_horizon);
  end if;
  if v_report.expires_at <= now() then
    return jsonb_build_object('status', 'BLOCKED_DATA_GATE', 'reason', 'REPORT_STALE', 'ticker', v_ticker, 'horizon', v_horizon);
  end if;
  if v_report.source_manifest_ref <> v_gate.active_manifest_ref
     or v_report.snapshot_id <> v_gate.active_snapshot_id then
    return jsonb_build_object(
      'status', 'BLOCKED_DATA_GATE',
      'reason', 'CACHE_MANIFEST_MISMATCH',
      'ticker', v_ticker,
      'horizon', v_horizon
    );
  end if;

  return jsonb_build_object(
    'status', 'READY',
    'ticker', v_report.ticker,
    'horizon', v_report.horizon,
    'snapshot_id', v_report.snapshot_id,
    'generated_at', v_report.generated_at,
    'expires_at', v_report.expires_at,
    'payload', v_report.payload
  );
end;
$$;

revoke all on function public.upsert_stockradar_cached_report(text, text, text, timestamptz, timestamptz, jsonb, text) from public, anon, authenticated;
grant execute on function public.upsert_stockradar_cached_report(text, text, text, timestamptz, timestamptz, jsonb, text) to service_role;

revoke all on function public.fetch_stockradar_cached_report(text, text) from public, anon, authenticated;
grant execute on function public.fetch_stockradar_cached_report(text, text) to service_role;
