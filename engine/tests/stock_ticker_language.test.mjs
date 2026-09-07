import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {parseResearchQuery} from '../../supabase/functions/_shared/stockradar-query.ts';
const template=fs.readFileSync(new URL('../../scripts/templates/stock_ticker_extractor.js',import.meta.url),'utf8').trim();
const extract=new Function(template+';return extractStockTickers;')();
const cases=[
 ['Tra cứu FPT; chỉ dùng dữ liệu có nguồn và ghi rõ ngày dữ liệu.',['FPT']],
 ['TRA CỨU FPT; CHỈ DÙNG DỮ LIỆU CÓ NGUỒN VÀ GHI RÕ NGÀY DỮ LIỆU.',['FPT']],
 ['hom nay xem fpt co nen mua khong, ghi ro ngay du lieu',['FPT']],
 ['Phân tích FPT và rủi ro ngành công nghệ',['FPT']],
 ['FPT còn tiềm năng không?',['FPT']],
 ['So sánh FPT và MWG, ghi rõ rủi ro từng mã',['FPT','MWG']],
 ['so sanh fpt voi mwg',['FPT','MWG']],
 ['mua được chưa?',[]],['MUA',[]],['3–6 tháng thì sao?',[]],
 ['SEPA là gì?',[]],['VPA, VCP, EPS, ROE, FCF, DCF và RSI là gì?',[]],
 ['Tôi cần ghi chú cho dự án và chat AI',[]],
 ['tra cứu TRA',['TRA']],['TRA',['TRA']],['mã TRA có rủi ro gì?',['TRA']],
 ['$TRA và $FPT',['TRA','FPT']],['FPT FPT fpt',['FPT']],
 ['Phân tích fpt',['FPT']],['mã CAN',['CAN']],['CAN',['CAN']],
 ['Tôi cần xem FPT chứ không phải mã ghi chú',['FPT']],
 ['FPT1 không phải mã FPT',['FPT']],['đạt điều kiện chưa?',[]],
 ['FPT, xem https://example.com/api/fpt hoặc ghi chú tại abc@example.com',['FPT']],
 ['Phân tích "FPT" rồi MWG',['FPT','MWG']]
];
for(const [message,want] of cases)test('lexical ticker intent: '+message,()=>assert.deepEqual(extract(message),want));
test('all three entry points embed exactly the same canonical recognition body',()=>{
 const explicit=template.replace('function extractStockTickers(text)','function explicitTicker(text)').replace('return tickers;','return tickers[0] || "";');
 const compact=x=>x.replace(/\s+/g,'');
 for(const path of ['supabase/functions/stock-ai-chat/index.ts','website/assets/ai-center.js']){
  const source=fs.readFileSync(new URL('../../'+path,import.meta.url),'utf8');assert.ok(compact(source).includes(compact(explicit)),path);
 }
 assert.ok(fs.readFileSync(new URL('../../supabase/functions/_shared/stockradar-query.ts',import.meta.url),'utf8').includes(template));
});
test('explicit message ticker supersedes a stale client selection without creating a comparison',()=>{
 assert.deepEqual(parseResearchQuery('Phân tích MWG','FPT').tickers,['MWG']);
 assert.deepEqual(parseResearchQuery('So sánh FPT và MWG','HPG').tickers,['FPT','MWG']);
 assert.deepEqual(parseResearchQuery('Mua được chưa?','FPT').tickers,['FPT']);
});
test('sector discussion about one ticker does not become a full-universe scan',()=>{
 assert.equal(parseResearchQuery('Phân tích FPT và rủi ro ngành công nghệ').scope,'ticker');
 assert.equal(parseResearchQuery('So sánh FPT và MWG theo ngành').scope,'compare');
 for(const q of ['Top cổ phiếu ngân hàng','Quét Pocket Pivot','Cổ phiếu nào đang gần breakout?','Ngành thép'])assert.equal(parseResearchQuery(q).scope,'scan');
});
