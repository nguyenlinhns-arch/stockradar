create or replace function public.stockradar_runtime_health_snapshot()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_result jsonb;
begin
  select jsonb_build_object(
    'checked_at', now(),
    'overall_status', case
      when (select count(*) from private.stock_research_cache) = 0 then 'DEGRADED_NO_RESEARCH'
      when (select count(*) from private.stock_research_cache where now() - generated_at <= interval '96 hours' and upper(coalesce(price_snapshot_status,'')) not like '%STALE%' and upper(coalesce(price_snapshot_status,'')) not like '%INVALID%' and upper(coalesce(price_snapshot_status,'')) not like '%FAILED%') = 0 then 'DEGRADED_RESEARCH_STALE'
      when (select count(*) from private.stock_research_cache where upper(coalesce(payload->>'exchange','HOSE')) <> 'HOSE') > 0 then 'BLOCKED_NON_HOSE_CONTAMINATION'
      when (select count(*) from private.stock_research_cache where public_action_allowed) > 0
           and not coalesce((select data_ready and data_rights_approved and compliance_approved and api_enabled from private.stock_api_gate where singleton), false)
        then 'BLOCKED_PUBLIC_GATE_MISMATCH'
      else 'INTERNAL_RESEARCH_HEALTHY'
    end,
    'research', jsonb_build_object(
      'total_rows', (select count(*) from private.stock_research_cache),
      'fresh_rows', (select count(*) from private.stock_research_cache where now() - generated_at <= interval '96 hours' and upper(coalesce(price_snapshot_status,'')) not like '%STALE%' and upper(coalesce(price_snapshot_status,'')) not like '%INVALID%' and upper(coalesce(price_snapshot_status,'')) not like '%FAILED%'),
      'stale_or_blocked_rows', (select count(*) from private.stock_research_cache where now() - generated_at > interval '96 hours' or upper(coalesce(price_snapshot_status,'')) like '%STALE%' or upper(coalesce(price_snapshot_status,'')) like '%INVALID%' or upper(coalesce(price_snapshot_status,'')) like '%FAILED%'),
      'non_hose_rows', (select count(*) from private.stock_research_cache where upper(coalesce(payload->>'exchange','HOSE')) <> 'HOSE'),
      'invalid_ticker_rows', (select count(*) from private.stock_research_cache where ticker !~ '^[A-Z0-9]{3}$' or ticker !~ '[A-Z]'),
      'public_action_rows', (select count(*) from private.stock_research_cache where public_action_allowed),
      'oldest_generated_at', (select min(generated_at) from private.stock_research_cache),
      'newest_generated_at', (select max(generated_at) from private.stock_research_cache),
      'snapshot_count', (select count(distinct snapshot_id) from private.stock_research_cache)
    ),
    'action_api_gate', coalesce((select jsonb_build_object(
      'data_ready', data_ready,
      'data_rights_approved', data_rights_approved,
      'compliance_approved', compliance_approved,
      'api_enabled', api_enabled,
      'active_snapshot_id', active_snapshot_id,
      'active_manifest_ref', active_manifest_ref,
      'evidence_ref', evidence_ref,
      'updated_at', updated_at
    ) from private.stock_api_gate where singleton), '{}'::jsonb),
    'action_runtime', jsonb_build_object(
      'live_reports', (select count(*) from private.stock_report_cache where expires_at > now()),
      'expired_reports', (select count(*) from private.stock_report_cache where expires_at <= now()),
      'actionable_events_24h', (select count(*) from private.stock_signal_events where actionable and event_at > now() - interval '24 hours'),
      'notifications_24h', (select count(*) from public.stockradar_notifications where created_at > now() - interval '24 hours')
    ),
    'email_delivery_gate', coalesce((select jsonb_build_object(
      'provider_name', provider_name,
      'provider_configured', provider_configured,
      'sender_domain_verified', sender_domain_verified,
      'unsubscribe_ready', unsubscribe_ready,
      'bounce_complaint_ready', bounce_complaint_ready,
      'compliance_approved', compliance_approved,
      'sending_enabled', sending_enabled,
      'evidence_ref', evidence_ref,
      'updated_at', updated_at
    ) from private.email_delivery_gate where singleton), '{}'::jsonb),
    'email_scheduler_gate', coalesce((select jsonb_build_object(
      'scheduler_configured', scheduler_configured,
      'scheduler_enabled', scheduler_enabled,
      'evidence_ref', evidence_ref,
      'updated_at', updated_at
    ) from private.email_worker_scheduler_gate where singleton), '{}'::jsonb),
    'email_outbox', jsonb_build_object(
      'queued', (select count(*) from private.email_outbox where status = 'QUEUED'),
      'sending', (select count(*) from private.email_outbox where status = 'SENDING'),
      'sent_24h', (select count(*) from private.email_outbox where status = 'SENT' and sent_at > now() - interval '24 hours'),
      'failed_24h', (select count(*) from private.email_outbox where status = 'FAILED' and created_at > now() - interval '24 hours')
    )
  ) into v_result;

  return v_result;
end;
$function$;

revoke all on function public.stockradar_runtime_health_snapshot() from public, anon, authenticated;
grant execute on function public.stockradar_runtime_health_snapshot() to service_role;
