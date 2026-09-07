-- Run only in a controlled connected database session; all test records roll back.
begin;
do $s$ begin
 perform set_config('request.jwt.claims',(select jsonb_build_object('sub',user_id,'role','authenticated')::text from private.stockradar_project_channels where enabled),true);
 perform set_config('stockradar.test_key',gen_random_uuid()::text,true);
end $s$;
set local role authenticated;
do $owner$ declare a jsonb;b jsonb;begin
 if not (public.get_my_stockradar_project_channel()->>'available')::boolean then raise exception 'OWNER_LINK_FAILED';end if;
 a:=public.submit_my_stockradar_project_question('Kiểm thử hàng đợi riêng — sẽ rollback','SHORT_TERM',current_setting('stockradar.test_key')::uuid);
 b:=public.submit_my_stockradar_project_question('Kiểm thử hàng đợi riêng — sẽ rollback','SHORT_TERM',current_setting('stockradar.test_key')::uuid);
 if a->>'id'<>b->>'id' or b->>'duplicate'<>'true' then raise exception 'IDEMPOTENCY_FAILED';end if;
 perform set_config('stockradar.test_id',a->>'id',true);
 begin perform public.submit_my_stockradar_project_question('Nội dung khác','SHORT_TERM',current_setting('stockradar.test_key')::uuid);raise exception 'CONFLICT_NOT_REJECTED';exception when others then if sqlerrm<>'IDEMPOTENCY_CONFLICT' then raise;end if;end;
 begin update public.stockradar_project_questions set answer='FORGED' where id=(a->>'id')::uuid;raise exception 'BROWSER_WRITE_NOT_BLOCKED';exception when insufficient_privilege then null;end;
 if (select count(*) from public.stockradar_project_questions where id=(a->>'id')::uuid)<>1 then raise exception 'OWNER_READ_FAILED';end if;
end $owner$;
reset role;set local role service_role;
do $processor$ declare a jsonb;b jsonb;key uuid;begin
 a:=public.claim_stockradar_project_question(current_setting('stockradar.test_id')::uuid);key:=(a->>'claim_token')::uuid;
 begin perform public.claim_stockradar_project_question(current_setting('stockradar.test_id')::uuid);raise exception 'DUPLICATE_CLAIM_ALLOWED';exception when others then if sqlerrm<>'QUESTION_ALREADY_CLAIMED' then raise;end if;end;
 begin perform public.complete_stockradar_project_question(current_setting('stockradar.test_id')::uuid,gen_random_uuid(),'Câu trả lời sai khóa nhận việc.');raise exception 'WRONG_TOKEN_ACCEPTED';exception when others then if sqlerrm<>'CLAIM_NOT_VALID' then raise;end if;end;
 a:=public.complete_stockradar_project_question(current_setting('stockradar.test_id')::uuid,key,'Câu trả lời kiểm thử từ Project — sẽ rollback.');
 b:=public.complete_stockradar_project_question(current_setting('stockradar.test_id')::uuid,key,'Câu trả lời kiểm thử từ Project — sẽ rollback.');
 if a->>'status'<>'ANSWERED' or b->>'duplicate'<>'true' then raise exception 'COMPLETE_FAILED';end if;
 begin perform public.complete_stockradar_project_question(current_setting('stockradar.test_id')::uuid,key,'Câu trả lời khác, không được ghi đè.');raise exception 'ANSWER_OVERWRITE_ACCEPTED';exception when others then if sqlerrm<>'ANSWER_ALREADY_RECORDED' then raise;end if;end;
end $processor$;
reset role;set local role authenticated;
do $parent$ declare r jsonb;begin r:=public.submit_my_stockradar_project_question('Hỏi tiếp câu đã trả lời','MEDIUM_TERM',gen_random_uuid(),current_setting('stockradar.test_id')::uuid);perform set_config('stockradar.cancel_id',r->>'id',true);end $parent$;
reset role;set local role service_role;
do $c$ declare r jsonb;begin r:=public.claim_stockradar_project_question(current_setting('stockradar.cancel_id')::uuid);perform set_config('stockradar.cancel_token',r->>'claim_token',true);end $c$;
reset role;set local role authenticated;
select public.cancel_my_stockradar_project_question(current_setting('stockradar.cancel_id')::uuid)->>'status' as cancel_test;
reset role;set local role service_role;
do $late$ begin begin perform public.complete_stockradar_project_question(current_setting('stockradar.cancel_id')::uuid,current_setting('stockradar.cancel_token')::uuid,'Câu trả lời đến sau khi hủy không được ghi.');raise exception 'CANCELLED_ANSWER_ACCEPTED';exception when others then if sqlerrm<>'CLAIM_NOT_VALID' then raise;end if;end;end $late$;
reset role;
do $other$ begin perform set_config('request.jwt.claims','{"sub":"22222222-2222-4222-8222-222222222222","role":"authenticated"}',true);end $other$;
set local role authenticated;
do $deny$ begin
 if exists(select 1 from public.stockradar_project_questions where id=current_setting('stockradar.test_id')::uuid) then raise exception 'CROSS_ACCOUNT_LEAK';end if;
 if public.get_my_stockradar_project_channel()->>'available'<>'false' then raise exception 'UNLINKED_ACCESS';end if;
 begin perform public.cancel_my_stockradar_project_question(current_setting('stockradar.test_id')::uuid);raise exception 'CROSS_OWNER_CANCEL';exception when others then if sqlerrm<>'QUESTION_NOT_FOUND' then raise;end if;end;
 begin perform public.read_stockradar_project_inbox();raise exception 'BROWSER_PROCESSOR_ACCESS';exception when insufficient_privilege then null;end;
end $deny$;
rollback;
select 'PASS: privilege-level queue tests; all fixtures rolled back' as result;
