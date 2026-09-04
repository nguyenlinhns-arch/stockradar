create or replace function public.record_stockradar_email_delivery_event_v1(
  p_provider_name text,
  p_provider_event_id text,
  p_provider_message_id text,
  p_event_type text,
  p_event_at timestamp with time zone,
  p_payload_digest text,
  p_event_meta jsonb default '{}'::jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $function$
declare
  v_event_type text := lower(trim(coalesce(p_event_type,'')));
  v_outbox_id uuid;
  v_user_id uuid;
  v_reason text;
  v_inserted integer := 0;
begin
  if v_event_type not in (
    'email.sent','email.delivered','email.delivery_delayed','email.bounced','email.complained',
    'email.opened','email.clicked','email.failed','email.scheduled','email.suppressed'
  ) then
    raise exception 'unsupported delivery event';
  end if;
  if length(trim(coalesce(p_provider_event_id,''))) = 0 then
    raise exception 'provider event id required';
  end if;
  if p_event_at is null then
    raise exception 'event_at required';
  end if;
  if length(trim(coalesce(p_payload_digest,''))) < 32 then
    raise exception 'payload digest required';
  end if;

  select o.id, o.user_id
    into v_outbox_id, v_user_id
  from private.email_outbox o
  where o.provider_message_id = nullif(trim(coalesce(p_provider_message_id,'')),'')
  order by o.created_at desc
  limit 1;

  insert into private.email_delivery_events(
    provider_name,provider_event_id,provider_message_id,outbox_id,event_type,event_at,payload_digest,event_meta
  ) values (
    upper(trim(p_provider_name)),trim(p_provider_event_id),nullif(trim(coalesce(p_provider_message_id,'')),''),
    v_outbox_id,v_event_type,p_event_at,lower(trim(p_payload_digest)),coalesce(p_event_meta,'{}'::jsonb)
  )
  on conflict(provider_name,provider_event_id) do nothing;
  get diagnostics v_inserted = row_count;

  if v_inserted = 0 then
    return jsonb_build_object('status','DUPLICATE','outbox_id',v_outbox_id);
  end if;

  if v_user_id is not null and v_event_type in ('email.bounced','email.complained','email.suppressed') then
    v_reason := case
      when v_event_type = 'email.complained' then 'COMPLAINT'
      when v_event_type = 'email.bounced' then 'BOUNCE'
      else 'ADMIN'
    end;
    insert into private.email_suppressions(user_id,reason,source_ref,created_at,lifted_at)
    values(v_user_id,v_reason,'PROVIDER_WEBHOOK:'||left(trim(p_provider_event_id),200),now(),null)
    on conflict(user_id) do update
      set reason=excluded.reason,source_ref=excluded.source_ref,created_at=now(),lifted_at=null;
    update public.product_email_preferences
       set enabled=false,updated_at=now()
     where user_id=v_user_id;
  end if;

  return jsonb_build_object('status','RECORDED','outbox_id',v_outbox_id);
end;
$function$;

revoke all on function public.record_stockradar_email_delivery_event_v1(text,text,text,text,timestamp with time zone,text,jsonb) from public, anon, authenticated;
grant execute on function public.record_stockradar_email_delivery_event_v1(text,text,text,text,timestamp with time zone,text,jsonb) to service_role;
