create or replace function public.get_my_stockradar_ai_threads(p_limit integer default 30)
returns table(
  thread_id uuid,
  title text,
  last_ticker text,
  last_scope text,
  last_horizon text,
  knowledge_version text,
  created_at timestamptz,
  updated_at timestamptz,
  last_message_at timestamptz,
  message_count bigint
)
language sql
stable
security definer
set search_path = ''
as $function$
  select
    t.id as thread_id,
    t.title,
    t.last_ticker,
    t.last_scope,
    t.last_horizon,
    t.knowledge_version,
    t.created_at,
    t.updated_at,
    t.last_message_at,
    (select count(*) from public.stockradar_ai_messages m where m.thread_id = t.id) as message_count
  from public.stockradar_ai_threads t
  where t.user_id = auth.uid()
    and t.status = 'ACTIVE'
  order by t.last_message_at desc, t.updated_at desc
  limit least(greatest(coalesce(p_limit, 30), 1), 50);
$function$;

revoke all on function public.get_my_stockradar_ai_threads(integer) from public, anon;
grant execute on function public.get_my_stockradar_ai_threads(integer) to authenticated;
