create table private.stock_api_approval_events (
  id uuid primary key default gen_random_uuid(),
  approval_type text not null check (approval_type in ('DATA_RIGHTS','COMPLIANCE')),
  manifest_ref text not null check (manifest_ref ~ '^sha256:[0-9a-f]{64}$'),
  snapshot_id text not null check (length(trim(snapshot_id)) > 0),
  granted boolean not null,
  evidence_ref text not null check (length(trim(evidence_ref)) > 0),
  recorded_at timestamptz not null default now()
);

create index stock_api_approval_latest
  on private.stock_api_approval_events(manifest_ref, snapshot_id, approval_type, recorded_at desc, id desc);

create table private.stock_api_activation_events (
  id uuid primary key default gen_random_uuid(),
  action text not null check (action in ('ENABLE','DISABLE')),
  manifest_ref text,
  snapshot_id text,
  evidence_ref text not null check (length(trim(evidence_ref)) > 0),
  report_count integer not null default 0 check (report_count >= 0),
  recorded_at timestamptz not null default now()
);

alter table private.stock_api_approval_events enable row level security;
alter table private.stock_api_activation_events enable row level security;
revoke all on table private.stock_api_approval_events from public, anon, authenticated;
revoke all on table private.stock_api_activation_events from public, anon, authenticated;

create or replace function public.record_stockradar_api_approval(
  p_approval_type text,
  p_manifest_ref text,
  p_snapshot_id text,
  p_granted boolean,
  p_evidence_ref text
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_type text := upper(trim(coalesce(p_approval_type, '')));
  v_manifest text := lower(trim(coalesce(p_manifest_ref, '')));
  v_snapshot text := trim(coalesce(p_snapshot_id, ''));
  v_evidence text := trim(coalesce(p_evidence_ref, ''));
  v_id uuid;
begin
  if v_type not in ('DATA_RIGHTS','COMPLIANCE') then
    raise exception 'invalid approval type';
  end if;
  if v_manifest !~ '^sha256:[0-9a-f]{64}$' then
    raise exception 'invalid manifest reference';
  end if;
  if length(v_snapshot) = 0 then
    raise exception 'snapshot_id is required';
  end if;
  if length(v_evidence) = 0 then
    raise exception 'evidence_ref is required';
  end if;

  insert into private.stock_api_approval_events(
    approval_type, manifest_ref, snapshot_id, granted, evidence_ref
  ) values (
    v_type, v_manifest, v_snapshot, p_granted, v_evidence
  ) returning id into v_id;

  return v_id;
end;
$$;

create or replace function public.activate_stockradar_api(
  p_manifest_ref text,
  p_snapshot_id text,
  p_evidence_ref text
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_manifest text := lower(trim(coalesce(p_manifest_ref, '')));
  v_snapshot text := trim(coalesce(p_snapshot_id, ''));
  v_evidence text := trim(coalesce(p_evidence_ref, ''));
  v_rights boolean;
  v_compliance boolean;
  v_report_count integer;
begin
  if v_manifest !~ '^sha256:[0-9a-f]{64}$' then
    raise exception 'invalid manifest reference';
  end if;
  if length(v_snapshot) = 0 then
    raise exception 'snapshot_id is required';
  end if;
  if length(v_evidence) = 0 then
    raise exception 'activation evidence_ref is required';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('stockradar-api-activation', 0));

  select event.granted into v_rights
  from private.stock_api_approval_events event
  where event.approval_type = 'DATA_RIGHTS'
    and event.manifest_ref = v_manifest
    and event.snapshot_id = v_snapshot
  order by event.recorded_at desc, event.id desc
  limit 1;

  select event.granted into v_compliance
  from private.stock_api_approval_events event
  where event.approval_type = 'COMPLIANCE'
    and event.manifest_ref = v_manifest
    and event.snapshot_id = v_snapshot
  order by event.recorded_at desc, event.id desc
  limit 1;

  if v_rights is not true then
    raise exception 'current DATA_RIGHTS approval is required';
  end if;
  if v_compliance is not true then
    raise exception 'current COMPLIANCE approval is required';
  end if;

  select count(*) into v_report_count
  from private.stock_report_cache report
  where report.source_manifest_ref = v_manifest
    and report.snapshot_id = v_snapshot
    and report.expires_at > now();

  if v_report_count <= 0 then
    raise exception 'at least one fresh manifest-bound report is required';
  end if;

  update private.stock_api_gate
     set data_ready = true,
         data_rights_approved = true,
         compliance_approved = true,
         active_manifest_ref = v_manifest,
         active_snapshot_id = v_snapshot,
         evidence_ref = v_evidence,
         api_enabled = true,
         updated_at = now()
   where singleton is true;

  insert into private.stock_api_activation_events(
    action, manifest_ref, snapshot_id, evidence_ref, report_count
  ) values (
    'ENABLE', v_manifest, v_snapshot, v_evidence, v_report_count
  );

  return jsonb_build_object(
    'api_enabled', true,
    'manifest_ref', v_manifest,
    'snapshot_id', v_snapshot,
    'fresh_report_count', v_report_count
  );
end;
$$;

create or replace function public.deactivate_stockradar_api(
  p_evidence_ref text
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_evidence text := trim(coalesce(p_evidence_ref, ''));
  v_manifest text;
  v_snapshot text;
  v_report_count integer := 0;
begin
  if length(v_evidence) = 0 then
    raise exception 'deactivation evidence_ref is required';
  end if;

  perform pg_advisory_xact_lock(hashtextextended('stockradar-api-activation', 0));

  select active_manifest_ref, active_snapshot_id
    into v_manifest, v_snapshot
  from private.stock_api_gate
  where singleton is true
  for update;

  if v_manifest is not null and v_snapshot is not null then
    select count(*) into v_report_count
    from private.stock_report_cache report
    where report.source_manifest_ref = v_manifest
      and report.snapshot_id = v_snapshot
      and report.expires_at > now();
  end if;

  update private.stock_api_gate
     set api_enabled = false,
         data_ready = false,
         data_rights_approved = false,
         compliance_approved = false,
         active_manifest_ref = null,
         active_snapshot_id = null,
         evidence_ref = null,
         updated_at = now()
   where singleton is true;

  insert into private.stock_api_activation_events(
    action, manifest_ref, snapshot_id, evidence_ref, report_count
  ) values (
    'DISABLE', v_manifest, v_snapshot, v_evidence, v_report_count
  );
end;
$$;

revoke all on function public.record_stockradar_api_approval(text, text, text, boolean, text) from public, anon, authenticated;
revoke all on function public.activate_stockradar_api(text, text, text) from public, anon, authenticated;
revoke all on function public.deactivate_stockradar_api(text) from public, anon, authenticated;
grant execute on function public.record_stockradar_api_approval(text, text, text, boolean, text) to service_role;
grant execute on function public.activate_stockradar_api(text, text, text) to service_role;
grant execute on function public.deactivate_stockradar_api(text) to service_role;
