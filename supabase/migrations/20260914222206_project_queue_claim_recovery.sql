-- Owner-only Project queue: use the same claimability rules for wakeup and inbox.
-- No account/route/token changes. Existing service-role-only grants are preserved.
create or replace function public.stockradar_native_probe_signal()
returns jsonb
language sql
security definer
set search_path = ''
as $function$
 select jsonb_build_object(
  'pending', exists(
   select 1
   from public.stockradar_project_questions q
   join private.stockradar_project_channels c
     on c.user_id=q.user_id and c.thread_id=q.thread_id and c.enabled
   join public.stockradar_ai_threads t
     on t.id=c.thread_id and t.user_id=c.user_id and t.status='ACTIVE'
   left join private.stockradar_project_claims cl on cl.question_id=q.id
   where q.origin='WEBSITE'
     and q.status in ('WAITING','PROCESSING')
     and (cl.question_id is null or cl.expires_at<=now())
     and exists(select 1 from private.stockradar_chatgpt_bridge_capabilities b
                where b.user_id=q.user_id and b.enabled)
  ),
  'signal_version','PENDING_BOOL_V1'
 );
$function$;

create or replace function public.read_stockradar_project_inbox(p_limit integer default 10)
returns jsonb
language sql
stable
set search_path = ''
as $function$
 select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at,x.id),'[]'::jsonb)
 from (
  select q.id,q.question,q.horizon,q.parent_id,q.status,q.origin,q.created_at,c.project_key,
         q.research_ticker,q.research_as_of_date,q.research_context_grade,q.research_context_captured_at
  from public.stockradar_project_questions q
  join private.stockradar_project_channels c
    on c.user_id=q.user_id and c.thread_id=q.thread_id and c.enabled
  join public.stockradar_ai_threads t
    on t.id=c.thread_id and t.user_id=c.user_id and t.status='ACTIVE'
  left join private.stockradar_project_claims cl on cl.question_id=q.id
  where q.origin='WEBSITE'
    and q.status in ('WAITING','PROCESSING')
    and (cl.question_id is null or cl.expires_at<=now())
  order by q.created_at,q.id
  limit least(greatest(coalesce(p_limit,10),1),20)
 ) x;
$function$;
