-- Version returned by the connected production migration registry; no owner identifiers.
create table if not exists public.stockradar_workspace_reports (
 id uuid primary key default gen_random_uuid(),
 user_id uuid not null references auth.users(id) on delete cascade,
 title text not null check (char_length(title) between 3 and 180),
 ticker text check (ticker is null or ticker ~ '^[A-Z0-9]{3}$'),
 horizon text check (horizon is null or horizon in ('SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION')),
 body text not null check (char_length(body) between 20 and 60000),
 evidence jsonb not null default '[]'::jsonb check (jsonb_typeof(evidence)='array' and jsonb_array_length(evidence)<=50),
 data_as_of timestamptz,
 status text not null default 'DRAFT' check (status in ('DRAFT','ARCHIVED')),
 source text not null default 'CHATGPT_PROJECT_WORKSPACE' check (source in ('CHATGPT_PROJECT_WORKSPACE','IMPLEMENTATION_NOTE')),
 idempotency_key text not null check (char_length(idempotency_key) between 8 and 160),
 content_hash text not null,
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now(),
 unique(user_id,idempotency_key)
);
alter table public.stockradar_workspace_reports enable row level security;
revoke all on public.stockradar_workspace_reports from public,anon,authenticated;
grant select on public.stockradar_workspace_reports to authenticated;
grant select,insert,update,delete on public.stockradar_workspace_reports to service_role;
create policy workspace_reports_owner_read on public.stockradar_workspace_reports for select to authenticated using ((select auth.uid())=user_id);
create index if not exists stockradar_workspace_reports_owner_created on public.stockradar_workspace_reports(user_id,created_at desc);
comment on table public.stockradar_workspace_reports is 'Private reviewed ChatGPT workspace reports. No public publication, trading, payment or email side effects.';
create or replace function public.save_stockradar_workspace_report(
 p_owner_id uuid,p_title text,p_body text,p_idempotency_key text,
 p_ticker text default null,p_horizon text default null,p_data_as_of timestamptz default null,
 p_evidence jsonb default '[]'::jsonb,p_source text default 'CHATGPT_PROJECT_WORKSPACE'
) returns jsonb language plpgsql security invoker set search_path='' as $fn$
declare v_id uuid; v_hash text; v_old_hash text;
begin
 if not exists(select 1 from auth.users where id=p_owner_id and email_confirmed_at is not null) then raise exception 'VERIFIED_OWNER_REQUIRED'; end if;
 if not exists(select 1 from public.stockradar_ai_user_memory where user_id=p_owner_id and preferences->'project_bridge'->>'source'='CHATGPT_PROJECT_STOCKRADAR' and preferences->'project_bridge'->>'enabled'='true') then raise exception 'WORKSPACE_NOT_LINKED'; end if;
 if p_title is null or length(trim(p_title)) not between 3 and 180 or p_body is null or length(trim(p_body)) not between 20 and 60000 then raise exception 'INVALID_REPORT_CONTENT'; end if;
 if p_idempotency_key is null or p_idempotency_key !~ '^[A-Za-z0-9_.:-]{8,160}$' then raise exception 'INVALID_IDEMPOTENCY_KEY'; end if;
 if p_body ~ '(sk-(proj-)?|sb_secret_|ghp_)[A-Za-z0-9_-]{16,}' or p_body like '%-----BEGIN%PRIVATE KEY-----%' then raise exception 'SECRET_MATERIAL_REJECTED'; end if;
 if p_evidence is null or jsonb_typeof(p_evidence)<>'array' or jsonb_array_length(p_evidence)>50 then raise exception 'INVALID_EVIDENCE'; end if;
 v_hash:=md5(jsonb_build_object('title',trim(p_title),'body',trim(p_body),'ticker',nullif(upper(trim(p_ticker)),''),'horizon',p_horizon,'data_as_of',p_data_as_of,'evidence',p_evidence,'source',p_source)::text);
 insert into public.stockradar_workspace_reports(user_id,title,body,ticker,horizon,data_as_of,evidence,source,idempotency_key,content_hash)
 values(p_owner_id,trim(p_title),trim(p_body),nullif(upper(trim(p_ticker)),''),p_horizon,p_data_as_of,p_evidence,p_source,p_idempotency_key,v_hash)
 on conflict(user_id,idempotency_key) do nothing returning id into v_id;
 if v_id is null then
  select id,content_hash into v_id,v_old_hash from public.stockradar_workspace_reports where user_id=p_owner_id and idempotency_key=p_idempotency_key;
  if v_old_hash is distinct from v_hash then raise exception 'IDEMPOTENCY_CONFLICT_REVIEW_REQUIRED'; end if;
 end if;
 return jsonb_build_object('id',v_id,'status','DRAFT','visibility','OWNER_ONLY','source',p_source,'content_hash',v_hash,'provider_called',false,'published',false,'email_sent',false);
end $fn$;
revoke all on function public.save_stockradar_workspace_report(uuid,text,text,text,text,text,timestamptz,jsonb,text) from public,anon,authenticated;
grant execute on function public.save_stockradar_workspace_report(uuid,text,text,text,text,text,timestamptz,jsonb,text) to service_role;
