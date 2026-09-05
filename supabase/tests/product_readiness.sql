-- Owner connection; fixtures and quota windows never commit.
begin;
do $$
declare uid uuid:=gen_random_uuid(); r jsonb; i integer; count_allowed integer:=0;
begin
  r:=public.get_stockradar_product_readiness_v1();
  if r->>'schema_version'<>'STOCKRADAR_PRODUCT_READINESS_V1' then raise exception 'Missing readiness contract'; end if;
  if r->>'status'='PAUSED' and r->>'checkout_ready'<>'false' then raise exception 'Paused checkout opened'; end if;
  if r::text ~* 'hook_token|account_number|approver_email|secret|api_key' then raise exception 'Readiness leaked private configuration'; end if;
  if not has_function_privilege('anon','public.get_stockradar_product_readiness_v1()','execute') then raise exception 'Public readiness unavailable'; end if;
  if has_function_privilege('authenticated','private.verify_manual_checkout(uuid,text)','execute') then raise exception 'Client can self grant Premium'; end if;
  insert into auth.users(id,email) values(uid,uid::text||'@example.invalid');
  insert into public.profiles(id,account_tier,account_status) values(uid,'PAID','ACTIVE')
    on conflict(id) do update set account_tier='PAID',account_status='ACTIVE';
  for i in 1..31 loop
    r:=public.consume_stockradar_api_quota(uid,'stock_ai_burst');
    if r->>'allowed'='true' then count_allowed:=count_allowed+1; end if;
  end loop;
  if count_allowed<>30 or r->>'allowed'<>'false' then raise exception 'Technical protection missing'; end if;
  r:=public.consume_stockradar_api_quota(uid,'stock_ai');
  if r->>'allowed'<>'true' or r->>'unlimited'<>'true' then raise exception 'Burst limit changed daily Premium policy'; end if;
  update public.profiles set account_status='SUSPENDED' where id=uid;
  r:=public.consume_stockradar_api_quota(uid,'stock_ai');
  if r->>'allowed'<>'false' then raise exception 'Inactive Premium not denied'; end if;
end $$;
select 'PASS readiness metadata, no client self-grant, technical limit 30/minute, Premium daily unlimited' as result;
rollback;
