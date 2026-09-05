-- Run with a database owner connection. Every fixture is rolled back.
begin;
do $$
declare uid uuid:=gen_random_uuid(); allowed_count integer:=0; r jsonb; i integer; guest_key text:=encode(extensions.digest(gen_random_uuid()::text,'sha256'),'hex');
begin
  insert into auth.users(id,email) values(uid,uid::text||'@example.invalid');
  insert into public.profiles(id,account_tier,account_status) values(uid,'FREE','ACTIVE')
    on conflict(id) do update set account_tier='FREE',account_status='ACTIVE';
  for i in 1..11 loop
    r:=public.consume_stockradar_api_quota(uid,'stock_ai');
    if (r->>'allowed')::boolean then allowed_count:=allowed_count+1; end if;
  end loop;
  if allowed_count<>10 then raise exception 'FREE quota failed'; end if;
  update public.profiles set account_tier='PAID' where id=uid;
  for i in 1..15 loop
    r:=public.consume_stockradar_api_quota(uid,'stock_ai');
    if r->>'allowed'<>'true' or r->>'unlimited'<>'true' or r->>'remaining' is not null then
      raise exception 'PAID quota failed';
    end if;
  end loop;
  allowed_count:=0;
  for i in 1..4 loop
    r:=public.consume_stockradar_guest_ai_quota(guest_key);
    if (r->>'allowed')::boolean then allowed_count:=allowed_count+1; end if;
  end loop;
  if allowed_count<>3 then raise exception 'GUEST quota failed'; end if;
  if has_function_privilege('anon','public.query_stockradar_research(text,text,integer)','execute') then
    raise exception 'Private data query exposed';
  end if;
end $$;
select 'PASS guest 3 / free 10 / paid unlimited; private query restricted' as result;
rollback;
