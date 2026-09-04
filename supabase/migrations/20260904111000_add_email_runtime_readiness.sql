-- Private, service-role-only operational readiness report for StockRadar product email.
-- No recipient PII or provider secret is returned.

create or replace function public.get_stockradar_email_runtime_readiness_v1()
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_gate private.email_delivery_gate%rowtype;
  v_sched private.email_worker_scheduler_gate%rowtype;
  v_provider text;
  v_provider_ok boolean := false;
  v_domain_ok boolean := false;
  v_unsub_ok boolean := false;
  v_bounce_ok boolean := false;
  v_compliance_ok boolean := false;
  v_cron_active boolean := false;
  v_cron_schedule text;
  v_pending integer := 0;
  v_processing integer := 0;
  v_failed integer := 0;
  v_suppressed integer := 0;
  v_sent integer := 0;
  v_stale_processing integer := 0;
  v_last_error text;
  v_last_error_at timestamptz;
  v_approvals integer := 0;
  v_activations integer := 0;
  v_delivery_events integer := 0;
  v_blockers text[] := '{}'::text[];
  v_ready_to_activate boolean := false;
  v_ready_to_send boolean := false;
begin
  select * into v_gate from private.email_delivery_gate where singleton is true;
  select * into v_sched from private.email_worker_scheduler_gate where singleton is true;

  v_provider := nullif(upper(trim(coalesce(v_gate.provider_name,''))), '');
  if v_provider is null then
    select upper(trim(e.provider_name)) into v_provider
    from private.email_delivery_approval_events e
    order by e.recorded_at desc, e.id desc
    limit 1;
  end if;

  if v_provider is not null then
    select coalesce((select e.granted from private.email_delivery_approval_events e where upper(e.provider_name)=v_provider and e.approval_type='PROVIDER_CONFIG' order by e.recorded_at desc,e.id desc limit 1),false) into v_provider_ok;
    select coalesce((select e.granted from private.email_delivery_approval_events e where upper(e.provider_name)=v_provider and e.approval_type='SENDER_DOMAIN' order by e.recorded_at desc,e.id desc limit 1),false) into v_domain_ok;
    select coalesce((select e.granted from private.email_delivery_approval_events e where upper(e.provider_name)=v_provider and e.approval_type='UNSUBSCRIBE' order by e.recorded_at desc,e.id desc limit 1),false) into v_unsub_ok;
    select coalesce((select e.granted from private.email_delivery_approval_events e where upper(e.provider_name)=v_provider and e.approval_type='BOUNCE_COMPLAINT' order by e.recorded_at desc,e.id desc limit 1),false) into v_bounce_ok;
    select coalesce((select e.granted from private.email_delivery_approval_events e where upper(e.provider_name)=v_provider and e.approval_type='COMPLIANCE' order by e.recorded_at desc,e.id desc limit 1),false) into v_compliance_ok;
  end if;

  select coalesce(j.active,false), j.schedule
    into v_cron_active, v_cron_schedule
  from cron.job j
  where j.jobname='stockradar-email-worker-drain-v1'
  limit 1;

  select
    count(*) filter(where o.status='PENDING')::integer,
    count(*) filter(where o.status='PROCESSING')::integer,
    count(*) filter(where o.status='FAILED')::integer,
    count(*) filter(where o.status='SUPPRESSED')::integer,
    count(*) filter(where o.status='SENT')::integer,
    count(*) filter(where o.status='PROCESSING' and o.claim_started_at < now()-interval '10 minutes')::integer
  into v_pending,v_processing,v_failed,v_suppressed,v_sent,v_stale_processing
  from private.email_outbox o;

  select o.last_error, coalesce(o.sent_at,o.claim_started_at,o.created_at)
    into v_last_error,v_last_error_at
  from private.email_outbox o
  where o.last_error is not null
  order by coalesce(o.claim_started_at,o.created_at) desc
  limit 1;

  select count(*)::integer into v_approvals from private.email_delivery_approval_events;
  select count(*)::integer into v_activations from private.email_delivery_activation_events;
  select count(*)::integer into v_delivery_events from private.email_delivery_events;

  if v_provider is null then v_blockers := array_append(v_blockers,'PROVIDER_NOT_SELECTED'); end if;
  if v_provider is not null and v_provider_ok is not true then v_blockers := array_append(v_blockers,'PROVIDER_CONFIG_APPROVAL_MISSING'); end if;
  if v_provider is not null and v_domain_ok is not true then v_blockers := array_append(v_blockers,'SENDER_DOMAIN_APPROVAL_MISSING'); end if;
  if v_provider is not null and v_unsub_ok is not true then v_blockers := array_append(v_blockers,'UNSUBSCRIBE_APPROVAL_MISSING'); end if;
  if v_provider is not null and v_bounce_ok is not true then v_blockers := array_append(v_blockers,'BOUNCE_COMPLAINT_APPROVAL_MISSING'); end if;
  if v_provider is not null and v_compliance_ok is not true then v_blockers := array_append(v_blockers,'COMPLIANCE_APPROVAL_MISSING'); end if;
  if length(trim(coalesce(v_gate.current_consent_version,'')))=0 then v_blockers := array_append(v_blockers,'CONSENT_VERSION_MISSING'); end if;
  if v_sched.singleton is null or v_sched.scheduler_configured is not true then v_blockers := array_append(v_blockers,'SCHEDULER_NOT_CONFIGURED'); end if;
  if v_cron_active is not true then v_blockers := array_append(v_blockers,'CRON_NOT_ACTIVE'); end if;
  if coalesce(v_cron_schedule,'') <> '*/2 2-11 * * 1-5' then v_blockers := array_append(v_blockers,'CRON_SCHEDULE_MISMATCH'); end if;
  if v_stale_processing > 0 then v_blockers := array_append(v_blockers,'STALE_PROCESSING_OUTBOX'); end if;
  if v_gate.sending_enabled is true and v_sched.scheduler_enabled is not true then v_blockers := array_append(v_blockers,'SCHEDULER_DISABLED_WHILE_SENDING'); end if;

  v_ready_to_activate := cardinality(v_blockers)=0;
  v_ready_to_send := v_ready_to_activate and v_gate.sending_enabled is true and v_sched.scheduler_enabled is true;

  return jsonb_build_object(
    'status','READY',
    'candidate_provider',v_provider,
    'ready_to_activate',v_ready_to_activate,
    'ready_to_send_now',v_ready_to_send,
    'blockers',to_jsonb(v_blockers),
    'approvals',jsonb_build_object(
      'provider_config',v_provider_ok,
      'sender_domain',v_domain_ok,
      'unsubscribe',v_unsub_ok,
      'bounce_complaint',v_bounce_ok,
      'compliance',v_compliance_ok,
      'event_count',v_approvals
    ),
    'delivery_gate',jsonb_build_object(
      'sending_enabled',coalesce(v_gate.sending_enabled,false),
      'provider_configured',coalesce(v_gate.provider_configured,false),
      'sender_domain_verified',coalesce(v_gate.sender_domain_verified,false),
      'unsubscribe_ready',coalesce(v_gate.unsubscribe_ready,false),
      'bounce_complaint_ready',coalesce(v_gate.bounce_complaint_ready,false),
      'compliance_approved',coalesce(v_gate.compliance_approved,false),
      'current_consent_version',v_gate.current_consent_version,
      'evidence_ref',v_gate.evidence_ref
    ),
    'scheduler',jsonb_build_object(
      'configured',coalesce(v_sched.scheduler_configured,false),
      'enabled',coalesce(v_sched.scheduler_enabled,false),
      'cron_active',v_cron_active,
      'cron_schedule',v_cron_schedule,
      'evidence_ref',v_sched.evidence_ref
    ),
    'outbox',jsonb_build_object(
      'pending',v_pending,
      'processing',v_processing,
      'failed',v_failed,
      'suppressed',v_suppressed,
      'sent',v_sent,
      'stale_processing',v_stale_processing,
      'last_error',v_last_error,
      'last_error_at',v_last_error_at
    ),
    'audit',jsonb_build_object(
      'activation_events',v_activations,
      'delivery_events',v_delivery_events
    ),
    'generated_at',now()
  );
end;
$$;

revoke all on function public.get_stockradar_email_runtime_readiness_v1() from public,anon,authenticated;
grant execute on function public.get_stockradar_email_runtime_readiness_v1() to service_role;
