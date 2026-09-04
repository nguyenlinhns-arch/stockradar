create or replace function public.stockradar_runtime_health_snapshot()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_research_total bigint;
  v_research_fresh bigint;
  v_research_blocked bigint;
  v_non_hose bigint;
  v_invalid_ticker bigint;
  v_public_action_rows bigint;
  v_action_ready boolean;
  v_email_ready boolean;
  v_scheduler_ready boolean;
  v_result jsonb;
begin
  select count(*),
         count(*) filter (where now() - generated_at <= interval '96 hours' and upper(coalesce(price_snapshot_status,'')) not like '%STALE%' and upper(coalesce(price_snapshot_status,'')) not like '%INVALID%' and upper(coalesce(price_snapshot_status,'')) not like '%FAILED%'),
         count(*) filter (where now() - generated_at > interval '96 hours' or upper(coalesce(price_snapshot_status,'')) like '%STALE%' or upper(coalesce(price_snapshot_status,'')) like '%INVALID%' or upper(coalesce(price_snapshot_status,'')) like '%FAILED%'),
         count(*) filter (where upper(coalesce(payload->>'exchange','HOSE')) <> 'HOSE'),
         count(*) filter (where ticker !~ '^[A-Z0-9]{3}$' or ticker !~ '[A-Z]'),
         count(*) filter (where public_action_allowed)
    into v_research_total,v_research_fresh,v_research_blocked,v_non_hose,v_invalid_ticker,v_public_action_rows
  from private.stock_research_cache;

  select coalesce(data_ready and data_rights_approved and compliance_approved and api_enabled,false)
    into v_action_ready from private.stock_api_gate where singleton;
  v_action_ready := coalesce(v_action_ready,false);

  select coalesce(provider_configured and sender_domain_verified and unsubscribe_ready and bounce_complaint_ready and compliance_approved and sending_enabled,false)
    into v_email_ready from private.email_delivery_gate where singleton;
  v_email_ready := coalesce(v_email_ready,false);

  select coalesce(scheduler_configured and scheduler_enabled,false)
    into v_scheduler_ready from private.email_worker_scheduler_gate where singleton;
  v_scheduler_ready := coalesce(v_scheduler_ready,false);

  select jsonb_build_object(
    'checked_at', now(),
    'overall_status', case
      when v_research_total = 0 then 'DEGRADED_NO_RESEARCH'
      when v_research_fresh = 0 then 'DEGRADED_RESEARCH_STALE'
      when v_non_hose > 0 then 'BLOCKED_NON_HOSE_CONTAMINATION'
      when v_public_action_rows > 0 and not v_action_ready then 'BLOCKED_PUBLIC_GATE_MISMATCH'
      when not v_action_ready or not (v_email_ready and v_scheduler_ready) then 'INTERNAL_READY_EXTERNAL_GATES_BLOCKED'
      else 'PRODUCTION_CAPABILITIES_READY'
    end,
    'capabilities', jsonb_build_object(
      'research_ai', case when v_research_total > 0 and v_research_fresh > 0 and v_non_hose = 0 and v_invalid_ticker = 0 then 'READY' else 'BLOCKED' end,
      'public_action', case when v_action_ready then 'READY' else 'BLOCKED' end,
      'email_delivery', case when v_email_ready then 'READY' else 'BLOCKED' end,
      'email_scheduler', case when v_scheduler_ready then 'READY' else 'BLOCKED' end
    ),
    'research', jsonb_build_object(
      'total_rows', v_research_total,
      'fresh_rows', v_research_fresh,
      'stale_or_blocked_rows', v_research_blocked,
      'non_hose_rows', v_non_hose,
      'invalid_ticker_rows', v_invalid_ticker,
      'public_action_rows', v_public_action_rows,
      'oldest_generated_at', (select min(generated_at) from private.stock_research_cache),
      'newest_generated_at', (select max(generated_at) from private.stock_research_cache),
      'snapshot_count', (select count(distinct snapshot_id) from private.stock_research_cache)
    ),
    'action_api_gate', coalesce((select jsonb_build_object('data_ready',data_ready,'data_rights_approved',data_rights_approved,'compliance_approved',compliance_approved,'api_enabled',api_enabled,'active_snapshot_id',active_snapshot_id,'active_manifest_ref',active_manifest_ref,'evidence_ref',evidence_ref,'updated_at',updated_at) from private.stock_api_gate where singleton),'{}'::jsonb),
    'action_runtime', jsonb_build_object('live_reports',(select count(*) from private.stock_report_cache where expires_at > now()),'expired_reports',(select count(*) from private.stock_report_cache where expires_at <= now()),'actionable_events_24h',(select count(*) from private.stock_signal_events where actionable and event_at > now()-interval '24 hours'),'notifications_24h',(select count(*) from public.stockradar_notifications where created_at > now()-interval '24 hours')),
    'email_delivery_gate', coalesce((select jsonb_build_object('provider_name',provider_name,'provider_configured',provider_configured,'sender_domain_verified',sender_domain_verified,'unsubscribe_ready',unsubscribe_ready,'bounce_complaint_ready',bounce_complaint_ready,'compliance_approved',compliance_approved,'sending_enabled',sending_enabled,'evidence_ref',evidence_ref,'updated_at',updated_at) from private.email_delivery_gate where singleton),'{}'::jsonb),
    'email_scheduler_gate', coalesce((select jsonb_build_object('scheduler_configured',scheduler_configured,'scheduler_enabled',scheduler_enabled,'evidence_ref',evidence_ref,'updated_at',updated_at) from private.email_worker_scheduler_gate where singleton),'{}'::jsonb),
    'email_outbox', jsonb_build_object('queued',(select count(*) from private.email_outbox where status='QUEUED'),'sending',(select count(*) from private.email_outbox where status='SENDING'),'sent_24h',(select count(*) from private.email_outbox where status='SENT' and sent_at > now()-interval '24 hours'),'failed_24h',(select count(*) from private.email_outbox where status='FAILED' and created_at > now()-interval '24 hours'))
  ) into v_result;
  return v_result;
end;
$function$;

revoke all on function public.stockradar_runtime_health_snapshot() from public, anon, authenticated;
grant execute on function public.stockradar_runtime_health_snapshot() to service_role;
