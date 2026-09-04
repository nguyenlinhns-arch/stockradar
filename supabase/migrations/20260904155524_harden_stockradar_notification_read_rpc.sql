grant update (read_at) on table public.stockradar_notifications to authenticated;

create policy stockradar_notifications_owner_update_read_at
  on public.stockradar_notifications
  for update
  to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

create or replace function public.mark_stockradar_notification_read_v1(p_notification_id uuid)
returns boolean
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_changed integer := 0;
begin
  if v_uid is null then
    raise exception 'authentication required' using errcode = '42501';
  end if;

  update public.stockradar_notifications
     set read_at = coalesce(read_at, now())
   where id = p_notification_id
     and user_id = v_uid;
  get diagnostics v_changed = row_count;
  return v_changed = 1;
end;
$$;

revoke all on function public.mark_stockradar_notification_read_v1(uuid) from public, anon;
grant execute on function public.mark_stockradar_notification_read_v1(uuid) to authenticated;
