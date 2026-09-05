import { readableResearchFacts } from './stockradar-readable.ts';
type Data = Record<string, any>;
const obj=(v:any):Data=>v&&typeof v==='object'&&!Array.isArray(v)?v:{};
const num=(v:any):number|null=>v==null||typeof v==='boolean'||typeof v==='object'||String(v).trim()===''?null:Number.isFinite(Number(v))?Number(v):null;
const n=(v:any,d=1)=>num(v)==null?'chưa có':Number(v).toLocaleString('vi-VN',{maximumFractionDigits:d});
const money=(v:any)=>num(v)==null?'chưa có':`${n(v,0)}đ`;
const pct=(v:any)=>`${n(v)}%`;
const norm=(v:string)=>String(v||'').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d').toLowerCase();

// Historical-multiple comparisons are not time-specific forecasts. Keep the
// original internal calculation in storage, but do not expose it as a target.
export function sanitizeResearchValuation(c:Data):Data {
  const v=obj(c.valuation_detail);
  const verified=v.assumptions_verified===true && v.forecast_verified===true && typeof v.method==='string' && !!v.method.trim()
    && Object.keys(obj(v.assumptions)).length>0 && typeof v.source_ref==='string' && !!v.source_ref.trim();
  if(verified)return {...c,valuation_detail:{...v,forecast_ready:true}};
  const result={...c};
  const keys=/^(?:target(?:_|$)|fair_value(?:_|$)|base$|bear$|bull$|mos$|mos_to_|upside(?:_|$)|rr_to_base|risk_reward_to_base)/;
  for(const section of ['trade_plan','analysis','research_v7','scanner_postclose','technical_detail','fundamental_detail','fundamental_valuation','valuation_detail']) {
    result[section]={...obj(c[section])};
    for(const key of Object.keys(result[section])) if(keys.test(key))result[section][key]=null;
  }
  result.valuation_detail={...result.valuation_detail,forecast_ready:false,forecast_status:'INSUFFICIENT_VERIFIED_ASSUMPTIONS',
    method_note:'So sánh hệ số lợi nhuận và giá trị sổ sách với lịch sử; chưa phải dự báo giá cho một thời hạn cụ thể.'};
  return result;
}

export function technicalEvidence(context:Data):Data {
  const t=obj(context.technical_detail),i=obj(t.computed_indicators),facts=readableResearchFacts(context);
  const ma20=num(i.ma20??i.bollinger_middle??t.ma20),ma50=num(i.ma50??t.ma50),ma200=num(i.ma200??t.ma200);
  const ma=[['20',ma20],['50',ma50],['200',ma200]].filter(([,v])=>v!=null).map(([d,v])=>`${d} phiên: ${money(v)}`).join('; ');
  const below=[['20',ma20],['50',ma50],['200',ma200]].filter(([,v])=>v!=null&&facts.price!=null&&facts.price<Number(v)).map(([d])=>d);
  const stage=String(i.stage||t.stage||'');
  const trend=stage==='STAGE_1'?'Giá đang tạo nền, chưa xác nhận xu hướng tăng.':stage==='STAGE_2'?'Giá đang trong giai đoạn tăng theo bộ kiểm tra xu hướng.':stage==='STAGE_3'?'Cấu trúc giá đang có dấu hiệu phân phối.':stage==='STAGE_4'?'Giá đang trong giai đoạn giảm.':'Chưa xác định chắc giai đoạn giá.';
  const checks=[];
  if(typeof i.trend_template_pass==='boolean')checks.push(i.trend_template_pass?'Cấu trúc xu hướng đạt bộ kiểm tra.':'Cấu trúc xu hướng chưa đạt bộ kiểm tra.');
  if(typeof i.vcp_proxy==='boolean')checks.push(i.vcp_proxy?'Có dấu hiệu nền giá co hẹp, cần xác nhận thêm.':'Chưa có nền giá co hẹp đủ rõ.');
  if(typeof i.demand_bar==='boolean')checks.push(i.demand_bar?'Phiên gần nhất có dấu hiệu cầu tăng.':'Phiên gần nhất chưa có tín hiệu cầu tăng rõ.');
  const bands=num(t.bollinger_lower)!=null&&num(t.bollinger_upper)!=null?`Dải biến động giá: ${money(t.bollinger_lower)}–${money(t.bollinger_upper)}; đây không tự động là vùng mua.`:'';
  const cloud=t.ichimoku_state==='BELOW_KUMO'?'Giá còn dưới vùng cản của mây Ichimoku.':t.ichimoku_state==='ABOVE_KUMO'?'Giá đã ở trên vùng mây Ichimoku.':'';
  return {stage,ma20,ma50,ma200,pivot:facts.pivot,trend,summary:[trend,ma?`Giá trung bình ${ma}.`:'Chưa đủ dữ liệu đường trung bình.',below.length?`Giá hiện tại thấp hơn đường trung bình ${below.join('/')} phiên.`:'',...checks].filter(Boolean).join(' '),bands,cloud,
    invalidation: facts.pivot!=null?`Chưa có điểm mua xác nhận. Nếu có tín hiệu vượt ${money(facts.pivot)} rồi giá quay xuống dưới mốc này, phải đánh giá lại; chưa tự đặt giá cắt lỗ khi hệ thống chưa phát hành.`:'Chưa đủ dữ liệu để xác định mốc hủy tín hiệu.'};
}

export function fourLayerEvidence(context:Data):Data[] {
  const f=obj(context.fundamental_detail),v=obj(context.valuation_detail),m=obj(context.market_context),t=obj(context.technical_detail),i=obj(t.computed_indicators),s=obj(context.supply_institutional),facts=readableResearchFacts(context);
  const period=/^\d{6}$/.test(String(f.period_end||''))?` (kỳ ${String(f.period_end).slice(4)}/${String(f.period_end).slice(0,4)})`:'';
  const quality=[];
  if(num(f.roe_pct)!=null)quality.push(`Lợi nhuận trên vốn chủ sở hữu ${pct(f.roe_pct)}`);
  if(num(f.roa_pct)!=null)quality.push(`lợi nhuận trên tổng tài sản ${pct(f.roa_pct)}`);
  const growth=[];
  if(num(f.profit_growth_yoy_pct)!=null)growth.push(`Lợi nhuận sau thuế tăng ${pct(f.profit_growth_yoy_pct)} so với cùng kỳ`);
  else if(num(f.pbt_growth_yoy_pct)!=null)growth.push(`Lợi nhuận trước thuế tăng ${pct(f.pbt_growth_yoy_pct)} so với cùng kỳ`);
  if(num(f.eps_growth_yoy_pct)!=null)growth.push(`lợi nhuận mỗi cổ phiếu tăng ${pct(f.eps_growth_yoy_pct)}`);
  if(num(f.pbt_growth_3y_avg_pct)!=null)growth.push(`tăng trưởng lợi nhuận trước thuế bình quân 3 năm ${pct(f.pbt_growth_3y_avg_pct)}`);
  const growthMissing=num(f.eps_growth_yoy_pct)==null?'Thiếu tăng trưởng lợi nhuận mỗi cổ phiếu để xác nhận đầy đủ tiêu chí tăng trưởng.':'';
  const market=[/WEAK|LAGGING/.test(String(m.sector_regime))?'Ngành đang yếu; chưa có lợi thế dẫn dắt ngành.':'',m.market_regime==='PHAN_HOA_THAN_TRONG'?'Thị trường chưa tăng đồng đều giữa các nhóm cổ phiếu.':''].filter(Boolean).join(' ');
  const flow=[facts.volumeText];
  const upDown=num(i.up_down_volume_ratio20);
  if(upDown!=null)flow.push(`Trong 20 phiên, tổng khối lượng ở các phiên tăng giá bằng ${n(upDown,2)} lần các phiên giảm giá; chỉ phản ánh giao dịch, chưa xác nhận tổ chức mua vào.`);
  if(s.institutional_context_note==='DISCLOSED_OWNERSHIP_CONTEXT_ONLY'||!s.institutional_flow_verified)flow.push('Chưa có dữ liệu mua/bán của tổ chức được xác minh.');
  return [
    {key:'FOUR_M',title:'1. DOANH NGHIỆP — 4M',status:'PARTIAL',text:`${quality.length?quality.join('; ')+period+'.':'Chưa đủ số liệu sinh lời.'} Chưa có bằng chứng đầy đủ về lợi thế cạnh tranh và chất lượng quản trị.${v.forecast_ready!==true?' Chưa xác nhận được biên an toàn về giá.':''}`},
    {key:'CANSLIM',title:'2. TĂNG TRƯỞNG — CANSLIM',status:'PARTIAL',text:[growth.length?growth.join('; ')+period+'.':'Chưa đủ dữ liệu tăng trưởng.',growthMissing,market].filter(Boolean).join(' ')},
    {key:'SEPA_VCP',title:'3. KỸ THUẬT — SEPA/VCP',status:obj(t.computed_indicators).trend_template_pass===true?'TREND_CONFIRMED':'UNCONFIRMED',text:technicalEvidence(context).summary},
    {key:'VPA',title:'4. GIÁ VÀ KHỐI LƯỢNG — VPA',status:'OBSERVED',text:flow.filter(Boolean).join(' ')},
  ];
}

export function valuationExplanation(context:Data):string {
  const v=obj(context.valuation_detail),f=obj(context.fundamental_detail),bits=[];
  if(num(v.pe)!=null)bits.push(`Giá bằng ${n(v.pe,2)} lần lợi nhuận mỗi cổ phiếu${num(f.pe_median_8q_provider)!=null?`, so với mức tham chiếu của 8 quý gần nhất là ${n(f.pe_median_8q_provider,2)} lần`:''}`);
  if(num(v.pb)!=null)bits.push(`giá bằng ${n(v.pb,2)} lần giá trị sổ sách${num(f.pb_median_8q_provider)!=null?`, so với lịch sử ${n(f.pb_median_8q_provider,2)} lần`:''}`);
  if(v.forecast_ready===true)return `Phương pháp: ${v.method}. Giả định: ${JSON.stringify(v.assumptions)}. Nguồn: ${v.source_ref}. Mức cơ sở ${money(v.base??v.fair_value)}; cần đọc cùng thời hạn của dự báo.`;
  return `${bits.length?bits.join('; ')+'. ':''}${bits.length?'Đây là so sánh với lịch sử, chưa đủ để kết luận cổ phiếu rẻ.':'Chưa đủ dữ liệu định giá.'} Chưa có dự báo đã kiểm chứng để đưa mục tiêu giá 3–6 tháng hoặc 12 tháng.${context.business_bucket==='BANK'?' Với ngân hàng, còn phải kiểm tra nợ xấu, dự phòng, khả năng sinh lời và giả định tăng trưởng.':''}`;
}

export function fourHorizonEvidence(context:Data,reports:Data[]=[]):Data[] {
  const tech=technicalEvidence(context),facts=readableResearchFacts(context),v=obj(context.valuation_detail),f=obj(context.fundamental_detail);
  const growth=num(f.profit_growth_yoy_pct)!=null?`Lợi nhuận sau thuế tăng ${pct(f.profit_growth_yoy_pct)} so với cùng kỳ. `:num(f.pbt_growth_yoy_pct)!=null?`Lợi nhuận trước thuế tăng ${pct(f.pbt_growth_yoy_pct)} so với cùng kỳ. `:'';
  const roe=num(f.roe_pct)!=null?`Lợi nhuận trên vốn chủ sở hữu hiện ${pct(f.roe_pct)}. `:'';
  const longRoe=num(f.roe_ttm_avg_8q_pct)!=null?`Lợi nhuận trên vốn chủ sở hữu bình quân 8 quý ${pct(f.roe_ttm_avg_8q_pct)}. `:'';
  const rows=[
    {horizon:'SHORT_TERM',label:'Ngắn hạn',text:`${tech.trend} ${tech.ma20!=null?`Giá trung bình 20 phiên ${money(tech.ma20)}; 50 phiên ${money(tech.ma50)}.`:''} ${facts.pivot!=null?`Theo dõi mốc ${money(facts.pivot)}; chạm mốc chưa đủ để mua.`:''} ${tech.cloud} ${tech.bands} ${facts.earlyVolumeText}`},
    {horizon:'MEDIUM_TERM',label:'3–6 tháng',text:growth+(v.forecast_ready?'Đọc kịch bản tăng trưởng và định giá đã kiểm chứng, kết hợp xác nhận xu hướng.':'Theo dõi tăng trưởng lợi nhuận, sức mạnh ngành và khả năng vượt nền giá. Chưa xác nhận vùng mua hoặc mục tiêu cho thời hạn này.')},
    {horizon:'LONG_TERM',label:'12 tháng',text:roe+(v.forecast_ready?'Đối chiếu dự báo năm, chất lượng lợi nhuận và các kịch bản định giá.':'Cần dự báo lợi nhuận năm và kịch bản định giá có căn cứ. Chưa đủ cơ sở đặt mục tiêu giá 12 tháng.')},
    {horizon:'ACCUMULATION',label:'Tích sản',text:longRoe+'Ưu tiên lợi thế cạnh tranh, quản trị, sức khỏe tài chính và biên an toàn. Chưa xác nhận mức giá tích lũy; không dùng biến động vài phiên làm lý do duy nhất để bán.'},
  ];
  return rows.map(row=>{const r=reports.find(x=>x.status==='READY'&&x.ticker===context.ticker&&x.horizon===row.horizon);return {...row,status:r?'ACTION_READY':'RESEARCH_ONLY',report:r?{generated_at:r.generated_at,expires_at:r.expires_at,payload:r.payload}:null};});
}

export function frameworkText(context:Data, question=''):string {
  const layers=fourLayerEvidence(context),horizons=fourHorizonEvidence(context);
  const short=/\b(ngan gon|tom tat)\b/.test(norm(question));
  return layers.map(x=>`${x.title}: ${x.text}`).join('\n\n') + '\n\nĐỊNH GIÁ: ' + valuationExplanation(context) +
    '\n\nBỐN KHUNG ĐẦU TƯ:\n' + horizons.map(x=>`- ${x.label}: ${short?x.text.split('. ')[0]+'.':x.text}`).join('\n') +
    '\n\nĐIỀU KIỆN ĐÁNH GIÁ LẠI: '+technicalEvidence(context).invalidation;
}
