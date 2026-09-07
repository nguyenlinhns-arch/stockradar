-- Production registry version. Keep the main writer SECURITY INVOKER; expose no auth rows.
create or replace function private.stockradar_workspace_owner_verified(p_owner_id uuid)
returns boolean language sql stable security definer set search_path='' as $f$
 select exists(select 1 from auth.users where id=p_owner_id and email_confirmed_at is not null);
$f$;
revoke all on function private.stockradar_workspace_owner_verified(uuid) from public,anon,authenticated;
grant usage on schema private to service_role;
grant execute on function private.stockradar_workspace_owner_verified(uuid) to service_role;
comment on function private.stockradar_workspace_owner_verified(uuid) is 'Restricted boolean lookup for the trusted report writer; no auth table rows or credentials are returned.';
do $patch$
declare definition text;
begin
 select pg_get_functiondef('public.save_stockradar_workspace_report(uuid,text,text,text,text,text,timestamptz,jsonb,text)'::regprocedure) into definition;
 if position('if not exists(select 1 from auth.users where id=p_owner_id and email_confirmed_at is not null)' in definition)=0 then raise exception 'WORKSPACE_WRITER_SOURCE_DRIFT'; end if;
 definition:=replace(definition,'if not exists(select 1 from auth.users where id=p_owner_id and email_confirmed_at is not null)','if not private.stockradar_workspace_owner_verified(p_owner_id)');
 execute definition;
end $patch$;
