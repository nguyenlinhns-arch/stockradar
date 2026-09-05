import test from 'node:test';
import assert from 'node:assert/strict';
import {actionBody,dailyBody,vietnamTime,price} from '../../supabase/functions/_shared/email-copy.ts';
test('email specifies Vietnamese date/time and exact money, without guessing missing values',()=>{
  assert.match(vietnamTime('2026-09-04T03:30:00Z'),/10:30.*04\/09\/2026.*giờ VN/);
  for(const v of [null,'','10:30','invalid','2026-09-04T10:30:00']) assert.equal(vietnamTime(v),'Chưa có thời gian xác nhận');
  assert.equal(price(20550),'20.550đ');
  for(const v of [null,'',false,0,-1,{},'bad']) assert.equal(price(v),'Chưa xác nhận');
});
test('action email uses approved prices and plain Vietnamese actions with escaping',()=>{
  const html=actionBody({previous_state:'WAIT',current_state:'BUY',reasons:['<script>bad</script>'],decision_card:{ticker:'ZZZ',reference_price:20550,buy_zone:[21000,21200],stop:19800,target:24000,risk_reward:2.25,evaluated_at:'2026-09-04T03:30:00Z',next_review:'2026-09-04T04:15:00Z',new_position_decision:'BUY',holding_decision:'HOLD'}},'https://stockradar.vn');
  for(const part of ['21.000đ – 21.200đ','19.800đ','24.000đ','2,25 lần','Theo dõi → Mua','Giữ và quan sát','11:15','&lt;script&gt;','co-phieu/?ticker=ZZZ']) assert.ok(html.includes(part),part);
  assert.doesNotMatch(html,/<script>|ACTION ALERT|Risk\/Reward|Target|Buy Zone|\[object Object\]/);
});
test('daily bulletin shows concrete approved recommendations and their confirmation times only',()=>{
  const html=dailyBody({generated_at:'2026-09-04T02:00:00Z',evaluated_at:'2026-09-04T01:30:00Z',opportunities:[{ticker:'ZZZ',publish_status:'PUBLISHED',action:'MUA',reference_price:20000,buy_zone:{low:19800,high:20100},stop_loss:18500,target:24000,confirmed_at:'2026-09-04T01:30:00Z'},{ticker:'PRIVATE',publish_status:'DRAFT',action:'MUA'}]},'https://stockradar.vn');
  assert.match(html,/ZZZ · Mua/); assert.match(html,/09:00/); assert.match(html,/08:30/); assert.match(html,/24.000đ/);
  assert.doesNotMatch(html,/PRIVATE|Watchlist|PREMIUM DAILY|\[object Object\]/);
  assert.match(dailyBody({},'https://stockradar.vn'),/Chưa có khuyến nghị mua đủ điều kiện công bố/);
});
