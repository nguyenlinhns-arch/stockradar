CREATE OR REPLACE FUNCTION public.stockradar_runtime_health_snapshot()
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path TO ''
AS $function$
declare
  v_research_total bigint; v_research_fresh bigint; v_research_blocked bigint; v_non_hose bigint; v_invalid_ticker bigint; v_public_action_rows bigint;
  v_reference_total bigint; v_reference_fresh bigint; v_reference_ready bigint; v_reference_bad bigint;
  v_action_ready boolean; v_email_ready boolean; v_scheduler_ready boolean;
  v_research_grade_ready boolean; v_ai_coverage_ready boolean; v_ai_synthesis_ready boolean;
  v_product_mode text; v_result jsonb;
begin
  select coalesce(product_mode,'AI_ONLY') into v_product_mode
  from private.stockradar_runtime_config where singleton is true;
  v_product_mode := coalesce(v_product_mode,'AI_ONLY');

  select
    count(*),
    count(*) filter(where generated_at between now()-interval '96 hours' and now()
      and as_of_date between (now() at time zone 'Asia/Ho_Chi_Minh')::date-4 and (now() at time zone 'Asia/Ho_Chi_Minh')::date
      and upper(coalesce(price_snapshot_status,'')) not like '%STALE%'
      and upper(coalesce(price_snapshot_status,'')) not like '%INVALID%'
      and upper(coalesce(price_snapshot_status,'')) not like '%FAILED%'),
    count(*) filter(where generated_at>now()
      or as_of_date>(now() at time zone 'Asia/Ho_Chi_Minh')::date
      or as_of_date<(now() at time zone 'Asia/Ho_Chi_Minh')::date-4
      or now()-generated_at>interval '96 hours'
      or upper(coalesce(price_snapshot_status,'')) like '%STALE%'
      or upper(coalesce(price_snapshot_status,'')) like '%INVALID%'
      or upper(coalesce(price_snapshot_status,'')) like '%FAILED%'),
    count(*) filter(where upper(coalesce(payload->>'exchange','HOSE'))<>'HOSE'),
    count(*) filter(where ticker !~ '^[A-Z0-9]{3}$' or ticker !~ '[A-Z]'),
    count(*) filter(where public_action_allowed)
  into v_research_total,v_research_fresh,v_research_blocked,v_non_hose,v_invalid_ticker,v_public_action_rows
  from private.stock_research_cache;

  select
    count(*),
    count(*) filter(where generated_at between now()-interval '96 hours' and now()
      and as_of_date between (now() at time zone 'Asia/Ho_Chi_Minh')::date-4 and (now() at time zone 'Asia/Ho_Chi_Minh')::date
      and upper(coalesce(price_snapshot_status,'')) not like '%STALE%'
      and upper(coalesce(price_snapshot_status,'')) not like '%INVALID%'
      and upper(coalesce(price_snapshot_status,'')) not like '%FAILED%'),
    count(*) filter(where research_ready),
    count(*) filter(where upper(coalesce(payload->>'exchange','HOSE'))<>'HOSE'
      or ticker !~ '^[A-Z0-9]{3}$' or ticker !~ '[A-Z]'
      or coalesce((payload #>> '{release,public_action_allowed}')::boolean,false) is true
      or payload #>> '{research_v7,ticker}' is distinct from ticker
      or not (payload ? 'research_v7') or not (payload ? 'quote') or not (payload ? 'setup'))
  into v_reference_total,v_reference_fresh,v_reference_ready,v_reference_bad
  from private.stock_research_reference_cache;

  -- Research grade is an internal quality classification. It may legitimately be
  -- unavailable while the full private reference context remains fresh enough for
  -- AI-only synthesis. Commercial/public release gates must not downgrade that
  -- private AI synthesis capability.
  v_research_grade_ready := v_research_total>0 and v_research_fresh>0 and v_non_hose=0 and v_invalid_ticker=0;
  v_ai_coverage_ready := v_reference_total=405 and v_reference_fresh=405 and v_reference_bad=0;
  v_ai_synthesis_ready := v_ai_coverage_ready;

  select coalesce(data_ready and data_rights_approved and compliance_approved and api_enabled,false)
    into v_action_ready from private.stock_api_gate where singleton;
  v_action_ready := coalesce(v_action_ready,false);

  select coalesce(provider_configured and sender_domain_verified and unsubscribe_ready and bounce_complaint_ready and compliance_approved and sending_enabled,false)
    into v_email_ready from private.email_delivery_gate where singleton;
  v_email_ready := coalesce(v_email_ready,false);

  select coalesce(scheduler_configured and scheduler_enabled,false)
    into v_scheduler_ready from private.email_worker_scheduler_gate where singleton;
  v_scheduler_ready := coalesce(v_scheduler_ready,false);

  v_result := jsonb_build_object(
    'checked_at',now(),
    'product_mode',v_product_mode,
    'overall_status',case
      when not v_ai_synthesis_ready then 'AI_COVERAGE_DEGRADED'
      when v_product_mode='AI_ONLY' and v_research_grade_ready then 'AI_ONLY_READY'
      when v_product_mode='AI_ONLY' and v_ai_synthesis_ready then 'AI_ONLY_REFERENCE_READY'
      when not v_research_grade_ready then 'REFERENCE_ONLY_RESEARCH_BLOCKED'
      when v_product_mode='FULL_PUBLIC' and v_research_grade_ready and v_action_ready and v_email_ready and v_scheduler_ready then 'PRODUCTION_CAPABILITIES_READY'
      else 'RESEARCH_READY_OPTIONAL_CAPABILITIES_BLOCKED'
    end,
    'capabilities',jsonb_build_object(
      'research_ai',case
        when v_research_grade_ready then 'READY_RESEARCH_GRADE'
        when v_ai_synthesis_ready then 'READY_REFERENCE_ONLY'
        else 'BLOCKED'
      end,
      'research_grade',case when v_research_grade_ready then 'RESEARCH_READY' else 'REFERENCE_ONLY' end,
      'ai_answer_coverage',case when v_ai_coverage_ready then 'READY_405_OF_405' else 'BLOCKED' end,
      'raw_redistribution',case when v_product_mode='FULL_PUBLIC' then(case when v_action_ready then 'READY' else 'BLOCKED' end)else'DISABLED_BY_DESIGN'end,
      'public_action',case when v_product_mode='FULL_PUBLIC' then(case when v_action_ready then'READY'else'BLOCKED'end)else'DISABLED_OPTIONAL'end,
      'email_delivery',case when v_email_ready then'READY'else'BLOCKED'end,
      'email_scheduler',case when v_scheduler_ready then'READY'else'BLOCKED'end
    ),
    'research',jsonb_build_object(
      'total_rows',v_research_total,
      'fresh_rows',v_research_fresh,
      'stale_or_blocked_rows',v_research_blocked,
      'non_hose_rows',v_non_hose,
      'invalid_ticker_rows',v_invalid_ticker,
      'public_action_rows',v_public_action_rows,
      'snapshot_count',(select count(distinct snapshot_id) from private.stock_research_cache)
    ),
    'ai_reference',jsonb_build_object(
      'total_rows',v_reference_total,
      'fresh_rows',v_reference_fresh,
      'research_ready_rows',v_reference_ready,
      'reference_only_rows',greatest(v_reference_total-v_reference_ready,0),
      'bad_rows',v_reference_bad,
      'snapshot_count',(select count(distinct snapshot_id) from private.stock_research_reference_cache),
      'oldest_generated_at',(select min(generated_at) from private.stock_research_reference_cache),
      'newest_generated_at',(select max(generated_at) from private.stock_research_reference_cache)
    ),
    'action_api_gate',coalesce((select jsonb_build_object(
      'data_ready',data_ready,'data_rights_approved',data_rights_approved,'compliance_approved',compliance_approved,'api_enabled',api_enabled,
      'active_snapshot_id',active_snapshot_id,'active_manifest_ref',active_manifest_ref,'evidence_ref',evidence_ref,'updated_at',updated_at
    ) from private.stock_api_gate where singleton),'{}'::jsonb),
    'email_delivery_gate',coalesce((select jsonb_build_object(
      'provider_name',provider_name,'provider_configured',provider_configured,'sender_domain_verified',sender_domain_verified,
      'unsubscribe_ready',unsubscribe_ready,'bounce_complaint_ready',bounce_complaint_ready,'compliance_approved',compliance_approved,
      'sending_enabled',sending_enabled,'evidence_ref',evidence_ref,'updated_at',updated_at
    ) from private.email_delivery_gate where singleton),'{}'::jsonb),
    'email_scheduler_gate',coalesce((select jsonb_build_object(
      'scheduler_configured',scheduler_configured,'scheduler_enabled',scheduler_enabled,'evidence_ref',evidence_ref,'updated_at',updated_at
    ) from private.email_worker_scheduler_gate where singleton),'{}'::jsonb)
  );
  return v_result;
end$function$;

revoke all on function public.stockradar_runtime_health_snapshot() from public,anon,authenticated;
grant execute on function public.stockradar_runtime_health_snapshot() to service_role;
