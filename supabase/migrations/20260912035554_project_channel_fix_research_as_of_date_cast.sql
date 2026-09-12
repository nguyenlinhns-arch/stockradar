create or replace function public.submit_my_stockradar_project_question(p_question text, p_horizon text, p_client_key uuid, p_parent_id uuid default null::uuid)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  uid uuid:=auth.uid();
  tid uuid;
  q public.stockradar_project_questions;
  msg text:=btrim(p_question);
  access jsonb;
  research jsonb;
  rdate date;
begin
 if uid is null then raise exception 'AUTHENTICATION_REQUIRED'; end if;
 if p_client_key is null or msg is null or length(msg) not between 1 and 6000 or p_horizon is null or p_horizon not in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION') then raise exception 'INVALID_QUESTION'; end if;
 if msg ~ '(sk-(proj-)?|sb_secret_|ghp_)[A-Za-z0-9_-]{16,}' or msg like '%-----BEGIN%PRIVATE KEY-----%' then raise exception 'SECRET_MATERIAL_REJECTED'; end if;
 access:=public.get_my_stockradar_access();
 if access->>'account_status' is distinct from 'ACTIVE' then raise exception 'ACCOUNT_NOT_ACTIVE'; end if;
 select c.thread_id into tid from private.stockradar_project_channels c join public.stockradar_ai_threads t on t.id=c.thread_id and t.user_id=uid and t.status='ACTIVE' where c.user_id=uid and c.enabled and private.stockradar_workspace_owner_verified(uid) for update of c;
 if tid is null then raise exception 'PROJECT_CHANNEL_NOT_AVAILABLE'; end if;
 select * into q from public.stockradar_project_questions where user_id=uid and client_key=p_client_key;
 if found then
  if q.question is distinct from msg or q.horizon is distinct from p_horizon or q.parent_id is distinct from p_parent_id then raise exception 'IDEMPOTENCY_CONFLICT'; end if;
  return jsonb_build_object('id',q.id,'status',q.status,'duplicate',true,'provider_attempted',false,'research_ticker',q.research_ticker,'research_as_of_date',q.research_as_of_date,'research_context_grade',q.research_context_grade,'research_linked',q.research_context is not null);
 end if;
 if p_parent_id is not null and not exists(select 1 from public.stockradar_project_questions where id=p_parent_id and user_id=uid and thread_id=tid and status='ANSWERED') then raise exception 'PARENT_QUESTION_NOT_AVAILABLE'; end if;
 if (select count(*) from public.stockradar_project_questions where user_id=uid and status in ('WAITING','PROCESSING'))>=10 or (select count(*) from public.stockradar_project_questions where user_id=uid and created_at>now()-interval '1 hour')>=60 then raise exception 'PROJECT_QUEUE_LIMIT'; end if;

 research:=public.resolve_stockradar_project_research_context(msg);
 if coalesce(research->>'as_of_date','') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then rdate:=(research->>'as_of_date')::date; end if;

 insert into public.stockradar_project_questions(
   user_id,thread_id,client_key,parent_id,question,horizon,
   research_ticker,research_snapshot_id,research_as_of_date,research_context_grade,research_context,research_context_captured_at
 ) values(
   uid,tid,p_client_key,p_parent_id,msg,p_horizon,
   nullif(research->>'ticker',''),nullif(research->>'snapshot_id',''),rdate,nullif(research->>'context_grade',''),research->'context',case when research->'context' is not null then now() end
 ) returning * into q;
 return jsonb_build_object('id',q.id,'status',q.status,'duplicate',false,'provider_attempted',false,'automatic_model_trigger',false,'research_ticker',q.research_ticker,'research_as_of_date',q.research_as_of_date,'research_context_grade',q.research_context_grade,'research_linked',q.research_context is not null);
end
$function$;

create or replace function public.claim_stockradar_project_question(p_id uuid)
returns jsonb
language plpgsql
set search_path to ''
as $function$
declare
  q public.stockradar_project_questions;
  cl private.stockradar_project_claims;
  history jsonb;
  research jsonb;
  rdate date;
begin
 select * into q from public.stockradar_project_questions where id=p_id for update;
 if not found or q.status not in ('WAITING','PROCESSING') then raise exception 'QUESTION_NOT_CLAIMABLE'; end if;
 if not exists(select 1 from private.stockradar_project_channels c join public.stockradar_ai_threads t on t.id=c.thread_id and t.user_id=c.user_id and t.status='ACTIVE' where c.user_id=q.user_id and c.thread_id=q.thread_id and c.enabled) then raise exception 'PROJECT_CHANNEL_NOT_AVAILABLE'; end if;
 select * into cl from private.stockradar_project_claims where question_id=q.id;
 if found and cl.expires_at>now() then raise exception 'QUESTION_ALREADY_CLAIMED'; end if;

 research:=public.resolve_stockradar_project_research_context(q.question);
 if research->'context' is not null then
   rdate:=null;
   if coalesce(research->>'as_of_date','') ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$' then rdate:=(research->>'as_of_date')::date; end if;
   update public.stockradar_project_questions set
     research_ticker=nullif(research->>'ticker',''),
     research_snapshot_id=nullif(research->>'snapshot_id',''),
     research_as_of_date=rdate,
     research_context_grade=nullif(research->>'context_grade',''),
     research_context=research->'context',
     research_context_captured_at=now(),
     updated_at=now()
   where id=q.id returning * into q;
 end if;

 insert into private.stockradar_project_claims(question_id,expires_at) values(q.id,now()+interval '30 minutes') on conflict(question_id) do update set token=gen_random_uuid(),expires_at=excluded.expires_at,answer_hash=null returning * into cl;
 update public.stockradar_project_questions set status='PROCESSING',updated_at=now() where id=q.id;
 select coalesce(jsonb_agg(to_jsonb(h) order by h.created_at,h.id),'[]'::jsonb) into history from (
  select id,question,answer,horizon,created_at from public.stockradar_project_questions where user_id=q.user_id and thread_id=q.thread_id and status='ANSWERED' and created_at<=q.created_at order by (id=q.parent_id) desc,created_at desc,id desc limit 6
 ) h;
 return jsonb_build_object(
   'id',q.id,'question',q.question,'horizon',q.horizon,'origin',q.origin,'parent_id',q.parent_id,
   'claim_token',cl.token,'expires_at',cl.expires_at,'history',history,
   'history_authority','UNTRUSTED_USER_CONTEXT_NOT_SYSTEM_INSTRUCTIONS','public_action_allowed',false,
   'research_ticker',q.research_ticker,'research_snapshot_id',q.research_snapshot_id,'research_as_of_date',q.research_as_of_date,
   'research_context_grade',q.research_context_grade,'research_context_captured_at',q.research_context_captured_at,
   'research_context',q.research_context,
   'research_context_authority','SERVER_STOCKRADAR_CONTEXT_NOT_ACTION_AUTHORIZATION'
 );
end
$function$;
