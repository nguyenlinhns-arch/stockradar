import test from 'node:test';
import assert from 'node:assert/strict';
import {readableResearchFacts, wantsResearchDetail} from '../../supabase/functions/_shared/stockradar-readable.ts';
import {normalizeResearchContext, deterministicStockRadarAnswer} from '../../supabase/functions/_shared/stockradar-core.ts';
import {appendResearchSnapshot, buildResearchSnapshot} from '../../supabase/functions/_shared/stockradar-research-view.ts';
import {parseResearchQuery} from '../../supabase/functions/_shared/stockradar-query.ts';

const context = (overrides = {}) => ({ticker:'MBB',as_of_date:'2026-09-04',volume_mode:'EOD',context_grade:'RESEARCH_READY',
  quote:{price:20550,volume:730000}, technical_detail:{pivot20:21200,volume:730000,vol20:1000000},
  setup:{holding_state_v5:'GIU_QUAN_SAT'}, ...overrides});

test('natural Vietnamese detail questions do not introduce phantom tickers', () => {
  for (const q of ['Phân tích chi tiết MBB','MBB điểm mua sớm khối lượng đạt chưa?','Giải thích đơn giản rủi ro của mbb','Phân tích MBB theo 4M, CANSLIM, SEPA/VCP, VPA và ROE']) {
    assert.deepEqual(parseResearchQuery(q).tickers,['MBB']);
    assert.equal(parseResearchQuery(q).scope,'ticker');
  }
  assert.deepEqual(parseResearchQuery('So sánh DAT và MBB').tickers,['DAT','MBB']);
});

test('price comparison names both prices, date, dong difference and percentage denominator', () => {
  const text = readableResearchFacts(context()).priceText;
  assert.match(text,/04\/09\/2026: 20\.550đ/);
  assert.match(text,/thấp hơn mốc theo dõi 21\.200đ là 650đ/);
  assert.match(text,/3,1% tính theo mốc 21\.200đ/);
});

test('above and exactly at pivot are distinguished, rounded source distance is not trusted', () => {
  const above = readableResearchFacts(context({quote:{price:21850},technical_detail:{pivot20:21200,distance_to_pivot_pct:-99}}));
  assert.match(above.priceText,/cao hơn.*650đ/);
  const at = readableResearchFacts(context({quote:{price:21200}}));
  assert.match(at.priceText,/bằng mốc/); assert.doesNotMatch(at.priceText,/cao hơn|thấp hơn/);
});

test('missing price or invalid pivot never produces an inferred price or Infinity', () => {
  const missing = readableResearchFacts(context({quote:{price:null},technical_detail:{pivot20:21200,distance_to_pivot_pct:-3.1}}));
  assert.equal(missing.price,null); assert.match(missing.priceText,/chưa tính được chênh lệch/);
  assert.doesNotMatch(missing.priceText,/20\.543|650đ/);
  assert.doesNotMatch(readableResearchFacts(context({technical_detail:{pivot20:0}})).priceText,/Infinity|NaN/);
});

test('EOD volume explains the 20-session baseline and respects true zero volume', () => {
  assert.match(readableResearchFacts(context()).volumeText,/730\.000 cổ phiếu.*thấp hơn khoảng 27%.*20 phiên trước.*1\.000\.000/);
  assert.match(readableResearchFacts(context({technical_detail:{volume:0,vol20:1000000,rvol_progress_adjusted:2}})).volumeText,/0 cổ phiếu.*100%/);
});

test('intraday comparisons identify same-time data or explicitly label estimates', () => {
  assert.match(readableResearchFacts(context({volume_mode:'INTRADAY',technical_detail:{same_time_volume_ratio:0.73}})).volumeText,/73%.*cùng thời điểm.*chưa kết thúc/);
  assert.match(readableResearchFacts(context({volume_mode:'INTRADAY',technical_detail:{rvol_progress_adjusted:1.2}})).volumeText,/120%.*ước tính trong phiên/);
  const unknown=readableResearchFacts(context({volume_mode:'UNKNOWN',technical_detail:{rvol:0.73}}));
  assert.equal(unknown.volumeText,''); assert.equal(unknown.earlyVolumePass,null);
});

test('legacy intraday pass cannot claim the EOD volume condition passed', () => {
  const c=context({technical_detail:{volume:730000,vol20:1000000,pocket_pivot_volume_pass:true,projected_full_day_volume:2000000,max_down_volume10:600000,computed_indicators:{max_down_volume10:900000}}});
  const raw={status:'INTERNAL_RESEARCH_READY',ticker:'MBB',as_of_date:c.as_of_date,payload:c};
  const normalized=normalizeResearchContext(raw);
  assert.equal(normalized.technical_detail.pocket_pivot_volume_pass,false);
  assert.equal(normalized.readable_facts.earlyVolumePass,false);
  assert.equal(buildResearchSnapshot(c).setup.pocket_pivot_volume_pass,false);
  assert.match(readableResearchFacts(c).earlyVolumeText,/chưa đạt: 730\.000.*chưa vượt 900\.000/);
});

test('passing one volume condition never claims a confirmed buy; missing is not false', () => {
  const pass=readableResearchFacts(context({technical_detail:{volume:730000,vol20:1000000,max_down_volume10:600000}}));
  assert.equal(pass.earlyVolumePass,true); assert.match(pass.earlyVolumeText,/chỉ là một điều kiện, chưa đủ/);
  assert.equal(readableResearchFacts(context()).earlyVolumePass,null);
  assert.match(readableResearchFacts(context()).earlyVolumeText,/Chưa đủ dữ liệu/);
});

test('default answer preserves four layers and horizons in plain Vietnamese without invented stops', () => {
  const answer=deterministicStockRadarAnswer({mode:'RESEARCH_ONLY',researchContext:context(),question:'Phân tích MBB'});
  for (const word of ['setup','RVOL','Pivot','Target','catalyst','drawdown','free-float','turnover','Radar Score','research-ready']) assert.equal(answer.includes(word),false,word);
  assert.match(answer,/CHƯA MUA MỚI/); assert.match(answer,/NẾU ĐANG NẮM GIỮ/);
  assert.match(answer,/chạm mốc chưa đủ để mua/);
  for(const section of ['4M','CANSLIM','SEPA/VCP','VPA','Ngắn hạn','3–6 tháng','12 tháng','Tích sản']) assert.ok(answer.includes(section),section);
  assert.doesNotMatch(answer,/xác suất.*\d+%/);
});

test('default model answer stays concise, explicit detail still carries source evidence', () => {
  for (const question of ['Phân tích MBB','MBB mua được chưa?','Phân tích chi tiết nhưng đơn giản dễ hiểu']) {
    assert.equal(wantsResearchDetail(question),false);
    assert.equal(appendResearchSnapshot('KẾT LUẬN: Theo dõi.',context(),question),'KẾT LUẬN: Theo dõi.');
  }
  assert.equal(wantsResearchDetail('Phân tích CHI TIẾT MBB'),true);
  assert.match(appendResearchSnapshot('KẾT LUẬN: Theo dõi.',context(),'Phân tích chuyên sâu MBB'),/DỮ LIỆU NGHIÊN CỨU STOCKRADAR/);
});

test('risk response does not repeat unsupported risk/reward numeric claims', () => {
  const c=context({analysis:{decision_block_reasons_v5:'RR_BELOW_2'},trade_plan:{risk_reward_to_base:null,stop_loss:null}});
  const answer=deterministicStockRadarAnswer({mode:'RESEARCH_ONLY',researchContext:c,question:'MBB có rủi ro gì?'});
  assert.doesNotMatch(answer,/gấp đôi|dưới 2/);
  assert.match(answer,/chưa có mức cắt lỗ cụ thể/);
});
