-- Sensitive privacy operation: require a newly created authenticated session.
-- The browser re-signs in with the current password before calling delete-account;
-- the Edge Function then verifies the JWT's session_id against auth.sessions.

create or replace function public.verify_stockradar_recent_session(
  p_user_id uuid,
  p_session_id uuid,
  p_max_age_seconds integer default 300
)
returns boolean
language sql
security definer
set search_path = ''
as $$
  select case
    when p_user_id is null or p_session_id is null then false
    when p_max_age_seconds < 60 or p_max_age_seconds > 900 then false
    else exists (
      select 1
      from auth.sessions s
      where s.id = p_session_id
        and s.user_id = p_user_id
        and s.created_at is not null
        and s.created_at >= now() - make_interval(secs => p_max_age_seconds)
        and (s.not_after is null or s.not_after > now())
    )
  end;
$$;

revoke all on function public.verify_stockradar_recent_session(uuid,uuid,integer) from public, anon, authenticated;
grant execute on function public.verify_stockradar_recent_session(uuid,uuid,integer) to service_role;
