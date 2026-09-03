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
  v_active_manifest text;
  v_active_snapshot text;
  v_report_count integer := 0;
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

  perform pg_advisory_xact_lock(hashtextextended('stockradar-api-activation', 0));

  insert into private.stock_api_approval_events(
    approval_type, manifest_ref, snapshot_id, granted, evidence_ref
  ) values (
    v_type, v_manifest, v_snapshot, p_granted, v_evidence
  ) returning id into v_id;

  if p_granted is false then
    select gate.active_manifest_ref, gate.active_snapshot_id
      into v_active_manifest, v_active_snapshot
    from private.stock_api_gate gate
    where gate.singleton is true
    for update;

    if v_active_manifest = v_manifest and v_active_snapshot = v_snapshot then
      select count(*) into v_report_count
      from private.stock_report_cache report
      where report.source_manifest_ref = v_manifest
        and report.snapshot_id = v_snapshot
        and report.expires_at > now();

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
        'DISABLE',
        v_manifest,
        v_snapshot,
        'AUTO_REVOKE:' || v_type || ':' || v_evidence,
        v_report_count
      );
    end if;
  end if;

  return v_id;
end;
$$;

revoke all on function public.record_stockradar_api_approval(text, text, text, boolean, text) from public, anon, authenticated;
grant execute on function public.record_stockradar_api_approval(text, text, text, boolean, text) to service_role;
