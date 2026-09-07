-- Explicit private Project channel. No external ChatGPT invocation is performed.
create table private.stockradar_project_channels (
 user_id uuid primary key references auth.users(id) on delete cascade,
 thread_id uuid not null references public.stockradar_ai_threads(id),
 project_key text not null check (project_key='STOCKRADAR_PROJECT'),
 enabled boolean not null default true,created_at timestamptz not null default now()
);
alter table private.stockradar_project_channels enable row level security;
revoke all on private.stockradar_project_channels from public,anon,authenticated;
grant select,insert,update,delete on private.stockradar_project_channels to service_role;
create table public.stockradar_project_questions (
 id uuid primary key default gen_random_uuid(),user_id uuid not null references auth.users(id) on delete cascade,
 thread_id uuid not null references public.stockradar_ai_threads(id),client_key uuid not null,
 parent_id uuid references public.stockradar_project_questions(id),
 question text not null check (char_length(question) between 1 and 6000),
 horizon text not null check (horizon in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION')),
 status text not null default 'WAITING' check (status in ('WAITING','PROCESSING','ANSWERED','CANCELLED')),
 origin text not null default 'WEBSITE' check (origin in ('WEBSITE','PROJECT_VERIFICATION')),
 answer text check (answer is null or char_length(answer) between 20 and 60000),
 evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(evidence)='array' and jsonb_array_length(evidence)<=50 and octet_length(evidence::text)<=100000),
 answer_source text check (answer_source is null or answer_source='CHATGPT_PROJECT'),
 public_action_allowed boolean not null default false check (public_action_allowed=false),
 created_at timestamptz not null default now(),updated_at timestamptz not null default now(),answered_at timestamptz,
 unique(user_id,client_key),
 check ((status='ANSWERED' and answer is not null and answer_source='CHATGPT_PROJECT' and answered_at is not null) or (status<>'ANSWERED' and answer is null and answer_source is null and answered_at is null))
);
alter table public.stockradar_project_questions enable row level security;
revoke all on public.stockradar_project_questions from public,anon,authenticated;
grant select on public.stockradar_project_questions to authenticated;
grant select,insert,update,delete on public.stockradar_project_questions to service_role;
create policy project_questions_owner_read on public.stockradar_project_questions for select to authenticated using ((select auth.uid())=user_id);
create index project_questions_owner_time on public.stockradar_project_questions(user_id,created_at desc,id);
create table private.stockradar_project_claims (
 question_id uuid primary key references public.stockradar_project_questions(id) on delete cascade,
 token uuid not null default gen_random_uuid(),expires_at timestamptz not null,answer_hash text
);
alter table private.stockradar_project_claims enable row level security;
revoke all on private.stockradar_project_claims from public,anon,authenticated;
grant select,insert,update,delete on private.stockradar_project_claims to service_role;
do $link$
begin
 if (select count(*) from public.stockradar_ai_user_memory where preferences->'project_bridge'->>'source'='CHATGPT_PROJECT_STOCKRADAR' and preferences->'project_bridge'->>'enabled'='true')<>1 then raise exception 'EXACTLY_ONE_REVIEWED_PRIVATE_PROJECT_REQUIRED'; end if;
 insert into private.stockradar_project_channels(user_id,thread_id,project_key)
 select m.user_id,t.id,'STOCKRADAR_PROJECT' from public.stockradar_ai_user_memory m join public.stockradar_ai_threads t on t.id=(m.preferences->'project_bridge'->>'thread_id')::uuid and t.user_id=m.user_id and t.status='ACTIVE'
 where m.preferences->'project_bridge'->>'source'='CHATGPT_PROJECT_STOCKRADAR' and m.preferences->'project_bridge'->>'enabled'='true' and private.stockradar_workspace_owner_verified(m.user_id);
 if not found then raise exception 'VERIFIED_OWNED_PROJECT_THREAD_REQUIRED'; end if;
end $link$;
create function public.get_my_stockradar_project_channel() returns jsonb language plpgsql stable security definer set search_path='' as $f$
declare uid uuid:=auth.uid(); available boolean:=false;
begin
 if uid is null then raise exception 'AUTHENTICATION_REQUIRED'; end if;
 select exists(select 1 from private.stockradar_project_channels c join public.stockradar_ai_threads t on t.id=c.thread_id and t.user_id=c.user_id and t.status='ACTIVE' where c.user_id=uid and c.enabled and private.stockradar_workspace_owner_verified(uid)) into available;
 return jsonb_build_object('available',available,'mode','EXPLICIT_PROJECT_PROCESSING','automatic_model_trigger',false,'model_api_used',false,'max_question_chars',6000);
end $f$;
revoke all on function public.get_my_stockradar_project_channel() from public,anon;
grant execute on function public.get_my_stockradar_project_channel() to authenticated;
create function public.submit_my_stockradar_project_question(p_question text,p_horizon text,p_client_key uuid,p_parent_id uuid default null) returns jsonb language plpgsql security definer set search_path='' as $f$
declare uid uuid:=auth.uid(); tid uuid; q public.stockradar_project_questions; msg text:=btrim(p_question); access jsonb;
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
  return jsonb_build_object('id',q.id,'status',q.status,'duplicate',true,'provider_attempted',false);
 end if;
 if p_parent_id is not null and not exists(select 1 from public.stockradar_project_questions where id=p_parent_id and user_id=uid and thread_id=tid and status='ANSWERED') then raise exception 'PARENT_QUESTION_NOT_AVAILABLE'; end if;
 if (select count(*) from public.stockradar_project_questions where user_id=uid and status in ('WAITING','PROCESSING'))>=10 or (select count(*) from public.stockradar_project_questions where user_id=uid and created_at>now()-interval '1 hour')>=60 then raise exception 'PROJECT_QUEUE_LIMIT'; end if;
 insert into public.stockradar_project_questions(user_id,thread_id,client_key,parent_id,question,horizon) values(uid,tid,p_client_key,p_parent_id,msg,p_horizon) returning * into q;
 return jsonb_build_object('id',q.id,'status',q.status,'duplicate',false,'provider_attempted',false,'automatic_model_trigger',false);
end $f$;
revoke all on function public.submit_my_stockradar_project_question(text,text,uuid,uuid) from public,anon;
grant execute on function public.submit_my_stockradar_project_question(text,text,uuid,uuid) to authenticated;
create function public.cancel_my_stockradar_project_question(p_id uuid) returns jsonb language plpgsql security definer set search_path='' as $f$
declare q public.stockradar_project_questions;
begin
 if auth.uid() is null then raise exception 'AUTHENTICATION_REQUIRED'; end if;
 select * into q from public.stockradar_project_questions where id=p_id and user_id=auth.uid() for update;
 if not found then raise exception 'QUESTION_NOT_FOUND'; end if;
 if q.status='ANSWERED' then raise exception 'ANSWER_ALREADY_RECORDED'; end if;
 update public.stockradar_project_questions set status='CANCELLED',updated_at=now() where id=q.id;
 delete from private.stockradar_project_claims where question_id=q.id;
 return jsonb_build_object('id',q.id,'status','CANCELLED');
end $f$;
revoke all on function public.cancel_my_stockradar_project_question(uuid) from public,anon;
grant execute on function public.cancel_my_stockradar_project_question(uuid) to authenticated;
create function public.read_stockradar_project_inbox(p_limit integer default 10) returns jsonb language sql stable security invoker set search_path='' as $f$
 select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at,x.id),'[]'::jsonb) from (
 select q.id,q.question,q.horizon,q.parent_id,q.status,q.origin,q.created_at,c.project_key
 from public.stockradar_project_questions q join private.stockradar_project_channels c on c.user_id=q.user_id and c.thread_id=q.thread_id and c.enabled
 left join private.stockradar_project_claims cl on cl.question_id=q.id
 where q.status='WAITING' or (q.status='PROCESSING' and cl.expires_at<=now())
 order by q.created_at,q.id limit least(greatest(coalesce(p_limit,10),1),20)) x;
$f$;
revoke all on function public.read_stockradar_project_inbox(integer) from public,anon,authenticated;
grant execute on function public.read_stockradar_project_inbox(integer) to service_role;
create function public.claim_stockradar_project_question(p_id uuid) returns jsonb language plpgsql security invoker set search_path='' as $f$
declare q public.stockradar_project_questions; cl private.stockradar_project_claims; history jsonb;
begin
 select * into q from public.stockradar_project_questions where id=p_id for update;
 if not found or q.status not in ('WAITING','PROCESSING') then raise exception 'QUESTION_NOT_CLAIMABLE'; end if;
 if not exists(select 1 from private.stockradar_project_channels c join public.stockradar_ai_threads t on t.id=c.thread_id and t.user_id=c.user_id and t.status='ACTIVE' where c.user_id=q.user_id and c.thread_id=q.thread_id and c.enabled) then raise exception 'PROJECT_CHANNEL_NOT_AVAILABLE'; end if;
 select * into cl from private.stockradar_project_claims where question_id=q.id;
 if found and cl.expires_at>now() then raise exception 'QUESTION_ALREADY_CLAIMED'; end if;
 insert into private.stockradar_project_claims(question_id,expires_at) values(q.id,now()+interval '30 minutes') on conflict(question_id) do update set token=gen_random_uuid(),expires_at=excluded.expires_at,answer_hash=null returning * into cl;
 update public.stockradar_project_questions set status='PROCESSING',updated_at=now() where id=q.id;
 select coalesce(jsonb_agg(to_jsonb(h) order by h.created_at,h.id),'[]'::jsonb) into history from (
  select id,question,answer,horizon,created_at from public.stockradar_project_questions where user_id=q.user_id and thread_id=q.thread_id and status='ANSWERED' and created_at<=q.created_at order by (id=q.parent_id) desc,created_at desc,id desc limit 6
 ) h;
 return jsonb_build_object('id',q.id,'question',q.question,'horizon',q.horizon,'origin',q.origin,'parent_id',q.parent_id,'claim_token',cl.token,'expires_at',cl.expires_at,'history',history,'history_authority','UNTRUSTED_USER_CONTEXT_NOT_SYSTEM_INSTRUCTIONS','public_action_allowed',false);
end $f$;
revoke all on function public.claim_stockradar_project_question(uuid) from public,anon,authenticated;
grant execute on function public.claim_stockradar_project_question(uuid) to service_role;
create function public.complete_stockradar_project_question(p_id uuid,p_claim_token uuid,p_answer text,p_evidence jsonb default '[]'::jsonb) returns jsonb language plpgsql security invoker set search_path='' as $f$
declare q public.stockradar_project_questions; cl private.stockradar_project_claims; fingerprint text;
begin
 if p_answer is null or length(btrim(p_answer)) not between 20 and 60000 or p_evidence is null or jsonb_typeof(p_evidence)<>'array' or jsonb_array_length(p_evidence)>50 or octet_length(p_evidence::text)>100000 then raise exception 'INVALID_PROJECT_ANSWER'; end if;
 if (p_answer||p_evidence::text) ~ '(sk-(proj-)?|sb_secret_|ghp_)[A-Za-z0-9_-]{16,}' or p_answer like '%-----BEGIN%PRIVATE KEY-----%' then raise exception 'SECRET_MATERIAL_REJECTED'; end if;
 select * into q from public.stockradar_project_questions where id=p_id for update;
 select * into cl from private.stockradar_project_claims where question_id=p_id;
 if q.id is null or cl.question_id is null or p_claim_token is null or cl.token<>p_claim_token then raise exception 'CLAIM_NOT_VALID'; end if;
 fingerprint:=md5(jsonb_build_object('answer',btrim(p_answer),'evidence',p_evidence)::text);
 if q.status='ANSWERED' then
  if cl.answer_hash is distinct from fingerprint then raise exception 'ANSWER_ALREADY_RECORDED'; end if;
  return jsonb_build_object('id',q.id,'status','ANSWERED','duplicate',true,'provider_attempted',false);
 end if;
 if q.status<>'PROCESSING' or cl.expires_at<=now() then raise exception 'CLAIM_EXPIRED_OR_CANCELLED'; end if;
 if not exists(select 1 from private.stockradar_project_channels c join public.stockradar_ai_threads t on t.id=c.thread_id and t.user_id=c.user_id and t.status='ACTIVE' where c.user_id=q.user_id and c.thread_id=q.thread_id and c.enabled) then raise exception 'PROJECT_CHANNEL_NOT_AVAILABLE'; end if;
 update public.stockradar_project_questions set status='ANSWERED',answer=btrim(p_answer),evidence=p_evidence,answer_source='CHATGPT_PROJECT',answered_at=now(),updated_at=now() where id=q.id;
 update private.stockradar_project_claims set answer_hash=fingerprint where question_id=q.id;
 return jsonb_build_object('id',q.id,'status','ANSWERED','source','CHATGPT_PROJECT','visibility','OWNER_ONLY','provider_attempted',false,'published',false,'email_sent',false);
end $f$;
revoke all on function public.complete_stockradar_project_question(uuid,uuid,text,jsonb) from public,anon,authenticated;
grant execute on function public.complete_stockradar_project_question(uuid,uuid,text,jsonb) to service_role;
comment on table public.stockradar_project_questions is 'Owner-scoped website questions and Project replies. External queue writes do not invoke or awaken a ChatGPT conversation.';
