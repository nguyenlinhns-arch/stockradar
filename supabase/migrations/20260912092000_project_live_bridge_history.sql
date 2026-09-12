-- STOCKRADAR_PROJECT_LIVE_BRIDGE_HISTORY_V1
-- Only real WEBSITE questions are mirrored into the canonical StockRadar AI thread.
-- Verification records remain in the project queue and never pollute user chat history.

create or replace function private.sync_stockradar_project_answer_to_thread()
returns trigger
language plpgsql
security definer
set search_path to ''
as $fn$
declare
  v_scope text;
  v_ticker text;
  v_now timestamptz := now();
begin
  if new.status <> 'ANSWERED' or old.status = 'ANSWERED' or new.answer is null or new.origin <> 'WEBSITE' then
    return new;
  end if;

  if not exists (
    select 1
    from public.stockradar_ai_threads t
    where t.id = new.thread_id
      and t.user_id = new.user_id
      and t.status = 'ACTIVE'
  ) then
    return new;
  end if;

  if exists (
    select 1
    from public.stockradar_ai_messages m
    where m.thread_id = new.thread_id
      and m.metadata->>'project_question_id' = new.id::text
  ) then
    return new;
  end if;

  v_ticker := case when new.research_ticker ~ '^[A-Z0-9]{3}$' then new.research_ticker else null end;
  v_scope := case when v_ticker is not null then 'ticker' else 'conversation' end;

  insert into public.stockradar_ai_messages(
    thread_id, role, content, scope, ticker, horizon, knowledge_version, metadata, created_at
  ) values (
    new.thread_id,
    'user',
    left(new.question, 24000),
    v_scope,
    v_ticker,
    new.horizon,
    null,
    jsonb_build_object(
      'project_question_id', new.id,
      'origin', new.origin,
      'bridge', 'CHATGPT_PROJECT'
    ),
    new.created_at
  );

  insert into public.stockradar_ai_messages(
    thread_id, role, content, scope, ticker, horizon,
    answer_engine, model_status, knowledge_version, metadata, created_at
  ) values (
    new.thread_id,
    'assistant',
    left(new.answer, 24000),
    v_scope,
    v_ticker,
    new.horizon,
    'CHATGPT_PROJECT_BRIDGE',
    'MODEL_READY',
    null,
    jsonb_build_object(
      'project_question_id', new.id,
      'answer_source', 'CHATGPT_PROJECT',
      'provider_attempted', false,
      'quota_consumed', false,
      'evidence', new.evidence
    ),
    coalesce(new.answered_at, v_now)
  );

  update public.stockradar_ai_threads t
  set title = coalesce(
        t.title,
        case when v_ticker is not null
          then v_ticker || ' · ' || left(new.question, 48)
          else left(new.question, 64)
        end
      ),
      last_ticker = coalesce(v_ticker, t.last_ticker),
      last_scope = v_scope,
      last_horizon = new.horizon,
      updated_at = v_now,
      last_message_at = coalesce(new.answered_at, v_now)
  where t.id = new.thread_id
    and t.user_id = new.user_id;

  return new;
end
$fn$;

drop trigger if exists trg_stockradar_project_answer_to_thread
  on public.stockradar_project_questions;

create trigger trg_stockradar_project_answer_to_thread
after update of status on public.stockradar_project_questions
for each row
when (
  new.status = 'ANSWERED'
  and old.status is distinct from new.status
  and new.origin = 'WEBSITE'
)
execute function private.sync_stockradar_project_answer_to_thread();
