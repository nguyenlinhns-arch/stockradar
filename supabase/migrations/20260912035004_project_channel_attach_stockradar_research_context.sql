alter table public.stockradar_project_questions
  add column research_ticker text,
  add column research_snapshot_id text,
  add column research_as_of_date date,
  add column research_context_grade text,
  add column research_context jsonb,
  add column research_context_captured_at timestamptz;

alter table public.stockradar_project_questions
  add constraint stockradar_project_questions_research_ticker_check
    check (research_ticker is null or research_ticker ~ '^[A-Z0-9]{3}$'),
  add constraint stockradar_project_questions_research_context_check
    check (research_context is null or jsonb_typeof(research_context)='object'),
  add constraint stockradar_project_questions_research_context_grade_check
    check (research_context_grade is null or research_context_grade in ('RESEARCH_READY','REFERENCE_ONLY'));

create or replace function public.resolve_stockradar_project_research_context(p_question text)
returns jsonb
language plpgsql
security definer
set search_path to ''
as $function$
declare
  token text;
  candidate text;
  raw jsonb;
  compact jsonb;
begin
  if p_question is null or length(btrim(p_question))=0 then
    return jsonb_build_object('linked',false);
  end if;

  for token in
    select x
    from regexp_split_to_table(
      regexp_replace(left(p_question,8000),'[^A-Za-z0-9$#]+',' ','g'),
      E'\\s+'
    ) as x
  loop
    candidate := upper(trim(both '$#' from token));
    if length(candidate)<>3 or candidate !~ '[A-Z]' then continue; end if;
    if candidate = any(array[
      'VPA','VCP','EPS','ROE','ROA','PBT','FCF','DCF','ATR','RSI','MAC','PEG','MOS','GDP','CPI','USD','VND','ETF','NAV','IPO','API','OTP','JWT','URL','CEO','CFO','CTO','LLM','MAI',
      'CHI','CHO','GHI','TRA','SAU','TIN','RUI','MOC','MOI','TOP','MUA','BAN','GIU','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','THE','NAO','CAN','XEM','HOM','CAC','CUA','VOI','TAI','TOI','NEN','CON','HON','GAN','LAM','VAN','QUA','MOT','HAI','NAM','DAY','DAU','TEN','BAO','LAI','LUC','NOI','NHA','DON','GON','RAT','TAM','TAN','CHU','DAN','DEN','CAP','NET','DAT','TUC','TIE','COI','FOR','AND','NEW','NOW','ALL','GET','SET'
    ]) then continue; end if;

    raw := public.fetch_stockradar_ai_context(candidate);
    if coalesce(raw->>'status','') not in ('INTERNAL_RESEARCH_READY','INTERNAL_REFERENCE_READY') then
      continue;
    end if;

    compact := jsonb_strip_nulls(jsonb_build_object(
      'status',raw->>'status',
      'context_grade',raw->>'context_grade',
      'ticker',raw->>'ticker',
      'snapshot_id',raw->>'snapshot_id',
      'generated_at',raw->>'generated_at',
      'as_of_date',raw->>'as_of_date',
      'price_snapshot_status',raw->>'price_snapshot_status',
      'data_quality',raw->>'data_quality',
      'data_layer_status',raw->>'data_layer_status',
      'public_action_allowed',false,
      'sector',raw#>>'{payload,sector}',
      'business_bucket',raw#>>'{payload,business_bucket}',
      'company_type',raw#>>'{payload,company_type}',
      'volume_mode',raw#>>'{payload,volume_mode}',
      'quote',raw#>'{payload,quote}',
      'market_context',raw#>'{payload,market_context}',
      'setup',raw#>'{payload,setup}',
      'scores',raw#>'{payload,scores}',
      'risk',raw#>'{payload,risk}',
      'technical_detail',raw#>'{payload,technical_detail}',
      'fundamental_detail',raw#>'{payload,fundamental_detail}',
      'valuation_detail',raw#>'{payload,valuation_detail}',
      'fundamental_valuation',raw#>'{payload,fundamental_valuation}',
      'catalyst',raw#>'{payload,catalyst}',
      'corporate_action',raw#>'{payload,corporate_action}',
      'supply_institutional',raw#>'{payload,supply_institutional}',
      'trade_plan',raw#>'{payload,trade_plan}',
      'release',raw#>'{payload,release}',
      'research_v7',raw#>'{payload,research_v7}'
    ));

    return jsonb_build_object(
      'linked',true,
      'ticker',raw->>'ticker',
      'snapshot_id',raw->>'snapshot_id',
      'as_of_date',raw->>'as_of_date',
      'context_grade',raw->>'context_grade',
      'context',compact
    );
  end loop;

  return jsonb_build_object('linked',false);
end
$function$;

revoke all on function public.resolve_stockradar_project_research_context(text) from public, anon, authenticated;
grant execute on function public.resolve_stockradar_project_research_context(text) to service_role;

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
 if coalesce(research->>'as_of_date','') ~ '^\\d{4}-\\d{2}-\\d{2}$' then rdate:=(research->>'as_of_date')::date; end if;

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
   if coalesce(research->>'as_of_date','') ~ '^\\d{4}-\\d{2}-\\d{2}$' then rdate:=(research->>'as_of_date')::date; end if;
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

create or replace function public.read_stockradar_project_inbox(p_limit integer default 10)
returns jsonb
language sql
stable
set search_path to ''
as $function$
 select coalesce(jsonb_agg(to_jsonb(x) order by x.created_at,x.id),'[]'::jsonb) from (
 select q.id,q.question,q.horizon,q.parent_id,q.status,q.origin,q.created_at,c.project_key,
        q.research_ticker,q.research_as_of_date,q.research_context_grade,q.research_context_captured_at
 from public.stockradar_project_questions q join private.stockradar_project_channels c on c.user_id=q.user_id and c.thread_id=q.thread_id and c.enabled
 left join private.stockradar_project_claims cl on cl.question_id=q.id
 where q.status='WAITING' or (q.status='PROCESSING' and cl.expires_at<=now())
 order by q.created_at,q.id limit least(greatest(coalesce(p_limit,10),1),20)) x;
$function$;

create or replace function public.get_stockradar_project_question_status_for_owner(p_owner_id uuid, p_id uuid)
returns jsonb
language sql
stable
set search_path to ''
as $function$
 select coalesce((select jsonb_build_object(
   'id',q.id,'status',q.status,'answer_source',q.answer_source,'answered_at',q.answered_at,'public_action_allowed',q.public_action_allowed,
   'research_ticker',q.research_ticker,'research_as_of_date',q.research_as_of_date,'research_context_grade',q.research_context_grade,'research_context_captured_at',q.research_context_captured_at
 ) from public.stockradar_project_questions q where q.id=p_id and q.user_id=p_owner_id),jsonb_build_object('status','NOT_FOUND'));
$function$;