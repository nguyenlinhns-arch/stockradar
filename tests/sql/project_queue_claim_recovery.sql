-- Trusted, owner-scoped integration test against existing database functions.
-- All fixtures are explicitly labelled, uncommitted, and rolled back inside an
-- exception subtransaction, including on unexpected failure. No auth token is
-- fabricated and no real pending question is claimed. No IDs/tokens are emitted.
-- Execute as trusted postgres only. Do not run while a real inbox has pending work.
do $qa$
declare
 owner_id uuid; thread uuid; qid uuid; cl jsonb; r jsonb; first_token uuid;
 results jsonb := '[]'::jsonb; err text; ok boolean; n integer;
 answer_text text := 'INTERNAL ROLLBACK TEST: xác nhận đường nhận và lưu câu trả lời; không phải phân tích cổ phiếu hoặc câu hỏi thật.';
 evidence_json jsonb := '[{"kind":"TRANSACTION_ROLLBACK_TEST","live_website_inference":false}]'::jsonb;
begin
 begin
  if jsonb_array_length(public.read_stockradar_project_inbox(20))<>0
     or (public.stockradar_native_probe_signal()->>'pending')::boolean then
   raise exception 'LIVE_PENDING_WORK_PRESENT_TEST_ABORTED';
  end if;
  select c.user_id,c.thread_id into strict owner_id,thread
  from private.stockradar_project_channels c
  join public.stockradar_ai_threads t on t.id=c.thread_id and t.user_id=c.user_id and t.status='ACTIVE'
  where c.enabled and exists(select 1 from private.stockradar_chatgpt_bridge_capabilities b where b.user_id=c.user_id and b.enabled);
  insert into public.stockradar_project_questions(user_id,thread_id,client_key,question,horizon,origin)
  values(owner_id,thread,gen_random_uuid(),'INTERNAL ROLLBACK TEST: kiểm tra liên thông; không phải câu hỏi thật.','SHORT_TERM','WEBSITE') returning id into qid;

  ok:=(public.stockradar_native_probe_signal()->>'pending')::boolean and exists(select 1 from jsonb_array_elements(public.read_stockradar_project_inbox(20)) x where x->>'id'=qid::text);
  results:=results||jsonb_build_array(jsonb_build_object('test','waiting_is_visible','pass',ok));
  cl:=public.claim_stockradar_project_question(qid); first_token:=(cl->>'claim_token')::uuid;
  ok:=not (public.stockradar_native_probe_signal()->>'pending')::boolean and not exists(select 1 from jsonb_array_elements(public.read_stockradar_project_inbox(20)) x where x->>'id'=qid::text);
  results:=results||jsonb_build_array(jsonb_build_object('test','active_claim_is_excluded','pass',ok));
  ok:=false;
  begin perform public.claim_stockradar_project_question(qid); exception when others then ok:=sqlerrm='QUESTION_ALREADY_CLAIMED'; end;
  results:=results||jsonb_build_array(jsonb_build_object('test','double_claim_rejected','pass',ok));

  update private.stockradar_project_claims set expires_at=now()-interval '1 second' where question_id=qid;
  ok:=(public.stockradar_native_probe_signal()->>'pending')::boolean and exists(select 1 from jsonb_array_elements(public.read_stockradar_project_inbox(20)) x where x->>'id'=qid::text);
  results:=results||jsonb_build_array(jsonb_build_object('test','expired_claim_reappears','pass',ok));
  cl:=public.claim_stockradar_project_question(qid);
  ok:=(cl->>'claim_token')::uuid<>first_token;
  begin perform public.complete_stockradar_project_question(qid,first_token,answer_text,evidence_json); ok:=false; exception when others then ok:=ok and sqlerrm='CLAIM_NOT_VALID'; end;
  results:=results||jsonb_build_array(jsonb_build_object('test','old_token_rejected_after_reclaim','pass',ok));

  delete from private.stockradar_project_claims where question_id=qid;
  ok:=(public.stockradar_native_probe_signal()->>'pending')::boolean and exists(select 1 from jsonb_array_elements(public.read_stockradar_project_inbox(20)) x where x->>'id'=qid::text);
  results:=results||jsonb_build_array(jsonb_build_object('test','processing_without_claim_recoverable','pass',ok));
  cl:=public.claim_stockradar_project_question(qid);
  update public.stockradar_project_questions set status='WAITING' where id=qid;
  ok:=not (public.stockradar_native_probe_signal()->>'pending')::boolean and not exists(select 1 from jsonb_array_elements(public.read_stockradar_project_inbox(20)) x where x->>'id'=qid::text);
  results:=results||jsonb_build_array(jsonb_build_object('test','waiting_with_live_claim_excluded','pass',ok));
  delete from private.stockradar_project_claims where question_id=qid;
  update public.stockradar_project_questions set origin='PROJECT_VERIFICATION' where id=qid;
  ok:=not (public.stockradar_native_probe_signal()->>'pending')::boolean and not exists(select 1 from jsonb_array_elements(public.read_stockradar_project_inbox(20)) x where x->>'id'=qid::text);
  results:=results||jsonb_build_array(jsonb_build_object('test','verification_fixture_not_in_real_inbox','pass',ok));

  update public.stockradar_project_questions set origin='WEBSITE' where id=qid;
  cl:=public.claim_stockradar_project_question(qid);
  r:=public.complete_stockradar_project_question(qid,(cl->>'claim_token')::uuid,answer_text,evidence_json);
  select count(*) into n from public.stockradar_ai_messages m where m.thread_id=thread and m.metadata->>'project_question_id'=qid::text;
  ok:=r->>'status'='ANSWERED' and r->>'visibility'='OWNER_ONLY' and n=2
      and exists(select 1 from public.stockradar_project_questions where id=qid and status='ANSWERED' and answer=answer_text and evidence=evidence_json and not public_action_allowed)
      and exists(select 1 from public.stockradar_ai_messages m where m.thread_id=thread and m.metadata->>'project_question_id'=qid::text and m.role='assistant' and m.content=answer_text);
  results:=results||jsonb_build_array(jsonb_build_object('test','answer_and_thread_body_match','pass',ok));
  ok:=not (public.stockradar_native_probe_signal()->>'pending')::boolean and not exists(select 1 from jsonb_array_elements(public.read_stockradar_project_inbox(20)) x where x->>'id'=qid::text);
  results:=results||jsonb_build_array(jsonb_build_object('test','answered_is_excluded','pass',ok));
  r:=public.complete_stockradar_project_question(qid,(cl->>'claim_token')::uuid,answer_text,evidence_json);
  select count(*) into n from public.stockradar_ai_messages m where m.thread_id=thread and m.metadata->>'project_question_id'=qid::text;
  results:=results||jsonb_build_array(jsonb_build_object('test','duplicate_delivery_is_idempotent','pass',(r->>'duplicate')::boolean and n=2));
  ok:=false;
  begin perform public.complete_stockradar_project_question(qid,(cl->>'claim_token')::uuid,answer_text||' changed',evidence_json); exception when others then ok:=sqlerrm='ANSWER_ALREADY_RECORDED'; end;
  results:=results||jsonb_build_array(jsonb_build_object('test','answer_overwrite_is_rejected','pass',ok));

  insert into public.stockradar_project_questions(user_id,thread_id,client_key,question,horizon,origin)
  values(owner_id,thread,gen_random_uuid(),'INTERNAL ROLLBACK TEST: hủy câu hỏi.','SHORT_TERM','WEBSITE') returning id into qid;
  cl:=public.claim_stockradar_project_question(qid);
  update public.stockradar_project_questions set status='CANCELLED' where id=qid;
  ok:=false;
  begin perform public.complete_stockradar_project_question(qid,(cl->>'claim_token')::uuid,answer_text,evidence_json); exception when others then ok:=sqlerrm='CLAIM_EXPIRED_OR_CANCELLED'; end;
  ok:=ok and not (public.stockradar_native_probe_signal()->>'pending')::boolean;
  results:=results||jsonb_build_array(jsonb_build_object('test','cancelled_rejects_late_answer','pass',ok));

  ok:=not has_function_privilege('anon','public.stockradar_native_probe_signal()','EXECUTE')
      and not has_function_privilege('authenticated','public.stockradar_native_probe_signal()','EXECUTE')
      and not has_function_privilege('anon','public.read_stockradar_project_inbox(integer)','EXECUTE')
      and not has_function_privilege('authenticated','public.read_stockradar_project_inbox(integer)','EXECUTE');
  results:=results||jsonb_build_array(jsonb_build_object('test','browser_cannot_call_processor_functions','pass',ok));
  raise exception using errcode='P9001', message='ROLLBACK_ALL_TEST_FIXTURES';
 exception
  when sqlstate 'P9001' then null;
  when others then get stacked diagnostics err=message_text;
    results:=results||jsonb_build_array(jsonb_build_object('test','unexpected_test_error','pass',false,'error',err));
 end;
 -- PL/pgSQL variables survive the rollback; fixture writes do not.
 perform set_config('stockradar.bridge_qa_report',jsonb_build_object('tests',results,'fixture_transaction_rolled_back',true,'live_browser_test',false,'checked_at',now())::text,true);
end $qa$;
select current_setting('stockradar.bridge_qa_report')::jsonb as bridge_qa_report;
