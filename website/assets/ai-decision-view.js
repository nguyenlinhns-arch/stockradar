(() => {
  'use strict';
  const numeric=v=>v!=null&&v!==''&&typeof v!=='boolean'&&Number.isFinite(Number(v));
  const price=v=>numeric(v)&&Number(v)>0?`${Math.round(v).toLocaleString('vi-VN')}đ`:'Chưa đủ dữ liệu';
  const number=v=>numeric(v)?Number(v).toLocaleString('vi-VN',{maximumFractionDigits:2}):'Chưa có';
  const pct=v=>numeric(v)?`${number(v)}%`:'Chưa có';
  const date=v=>/^\d{4}-\d{2}-\d{2}$/.test(String(v))?String(v).split('-').reverse().join('/'):'Chưa xác minh';
  const time=v=>Number.isFinite(Date.parse(v))?new Date(v).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh',hour12:false}):'Chưa xác minh';
  const element=(tag,text,cls)=>{const e=document.createElement(tag);if(text!=null)e.textContent=text;if(cls)e.className=cls;return e;};
  function rows(parent,values) {
    const dl=element('dl',null,'sr-decision-grid');
    for(const [label,value] of values){const cell=element('div');cell.append(element('dt',label),element('dd',value));dl.append(cell);}
    parent.append(dl);
  }
  function details(parent,title,text) {
    const d=element('details',null,'sr-decision-details');d.append(element('summary',title),element('div',text,'sr-decision-prose'));parent.append(d);return d;
  }
  function stillFresh(data) {
    const now=Date.now(),at=Date.parse(data?.updated_at),day=Date.parse(data?.as_of_date),today=Date.parse(new Date(now+7*3600000).toISOString().slice(0,10));
    return data?.fresh===true&&Number.isFinite(at)&&now-at<=96*3600000&&at<=now+300000&&day<=today&&today-day<=96*3600000
      &&(!data.expires_at||Date.parse(data.expires_at)>now);
  }
  function render(parent,data,meta='') {
    const cards=Array.isArray(data?.decision_cards)?data.decision_cards:[];
    if(!cards.length)return false;
    const wrap=element('div',null,'sr-decision-response');wrap.dataset.decisionResponse='';
    for(const c of cards.slice(0,20)) {
      if(c.schema_version!=='STOCKRADAR_DECISION_CARD_V1')continue;
      const d=c.data||{},fresh=stillFresh(d),official=fresh&&c.public_action_allowed===true;
      const card=element('article',null,'sr-decision-card');card.dataset.decisionTicker=c.ticker;
      card.append(element('strong',`KẾT LUẬN: ${c.ticker} — ${fresh?c.conclusion:'CHƯA ĐỦ DỮ LIỆU ĐỂ RA QUYẾT ĐỊNH'}`,'sr-decision-conclusion'));
      const sourceStatus=fresh?d.status:'UNAVAILABLE';
      card.append(element('p',`${sourceStatus} · ${d.source||'StockRadar'} · ${fresh?'Nguồn còn hạn':'Nguồn chưa đủ mới'} · ${d.price_time_kind==='EOD'?'Đóng cửa':'Ngày dữ liệu'} ${date(d.as_of_date)} · Rà soát ${time(d.updated_at)} (GMT+7)`,'sr-decision-source'));
      const targets=c.targets||{},zone=c.buy_zone||{};
      rows(card,[['Giá quan sát',price(c.price)],['Khung đầu tư',({SHORT_TERM:'Ngắn hạn',MEDIUM_TERM:'3–6 tháng',LONG_TERM:'12 tháng',ACCUMULATION:'Tích sản'})[c.horizon]||'Chưa xác định']]);
      if(official)rows(card,[['Vùng mua (Buy Zone)',numeric(zone.low)&&numeric(zone.high)?`${price(zone.low)} – ${price(zone.high)}`:'Chưa xác nhận'],
        ['Tỷ trọng đề xuất',official?pct(c.position_pct):'Chưa mở vị thế mới'],['Cắt lỗ (Stop-loss)',official?price(c.stop_loss):'Chưa phát hành'],
        ['Target gần',official?price(targets.short_term):'Chưa phát hành'],['Target 3–6 tháng',official?price(targets.three_to_six_months):'Chưa phát hành'],['Target 12 tháng',official?price(targets.twelve_months):'Chưa phát hành'],
        ['Upside / Downside',official?`${pct(c.upside_pct)} / ${pct(c.downside_pct)} từ giá quan sát`:'Chưa có kế hoạch xác nhận'],['Risk/Reward',official&&numeric(c.risk_reward)?`${number(c.risk_reward)} lần`:'Chưa có kế hoạch xác nhận']]);
      const e=fresh&&!official?c.estimated_plan:null;
      if(e?.status==='MODEL_SCENARIO') {
        const model=element('section',null,'sr-decision-estimates');model.append(element('strong','Target dự kiến · kịch bản tham khảo, độ tin cậy thấp'));
        const s=e.short_term,m=e.medium_term,l=e.long_term;
        rows(model,[['Ngắn hạn',price(s?.target)],['Stop-loss ngắn hạn',s?`${price(s.stop_loss)} nếu vào ${price(s.entry)}`:'Chưa đủ dữ liệu'],
          ['3 tháng → 6 tháng',m?`${price(m.at_3_months)} → ${price(m.at_6_months)}`:'Chưa đủ dữ liệu'],['12 tháng',price(l?.target)],['Ngưỡng tích sản',price(e.accumulation?.price_ceiling)]]);
        model.append(element('p',s?.condition||'Chưa phải dự báo được kiểm chứng hoặc tín hiệu mua.'));
        const v=e.valuation_model;
        const assumptions=[v?`${v.formula}. Đầu vào ${price(v.input)}; hệ số ${number(v.multiple)} lần (${v.multiple_period}); tăng trưởng giả định ${pct(v.annual_growth_pct)}/năm từ ${v.growth_source}. Giới hạn mô hình −30% đến +20%/năm.`:'',
          s?`Stop ngắn hạn dựa trên 1,5 × ATR20 ${pct(s.atr20_pct)}, giới hạn rủi ro 5–8%; R/R kịch bản 2 lần. Không dùng stop này cho thời hạn dài hơn.`:'',e.accumulation?.condition||''].filter(Boolean).join('\n\n');
        details(model,'Căn cứ tính và giới hạn',assumptions);card.append(model);
      }
      if(!official)card.append(element('p','Chưa phát hành vùng mua, tỷ trọng và kế hoạch target/stoploss chính thức.','sr-decision-conditions'));
      const why=element('section',null,'sr-decision-why');why.append(element('strong','Vì sao?'));
      const ul=element('ul');
      for(const text of (fresh?c.reasons:c.missing||[]).slice(0,4))ul.append(element('li',String(text).split(/(?<=\.)\s+(?=[A-ZÀ-Ỹ])/).slice(0,2).join(' ')));
      why.append(ul);card.append(why);
      card.append(element('p',`Điều kiện đánh giá lại: ${(c.conditions||[]).join(' ')}`,'sr-decision-conditions'));
      const technical=details(card,'Setup, xu hướng và khối lượng',null);technical.lastElementChild.remove();
      const ma=c.moving_averages||{},vol=c.volume||{};
      rows(technical,[['Setup',c.setup||'Chưa xác nhận'],['Stage',c.stage||'Chưa xác định'],['MA10 / MA50',`${price(ma.ma10)} / ${price(ma.ma50)}`],['MA150 / MA200',`${price(ma.ma150)} / ${price(ma.ma200)}`],
        ['Pivot · mốc theo dõi',price(c.pivot)],['Khối lượng',number(vol.current)],['RVOL',`${number(vol.rvol)} lần · ${vol.mode==='EOD'?'cuối phiên':vol.mode==='INTRADAY'?'trong phiên':'chưa rõ cơ sở'}`],
        ['Vol20 / Max Down-Volume 10',`${number(vol.vol20)} / ${number(vol.max_down_volume_10)}`],['VPA',c.vpa?.assessment?.value||'Chưa xác nhận dòng tiền tổ chức'],['Thời gian kỳ vọng',c.expected_holding||'Theo khung đầu tư; chưa có mốc đạt giá xác nhận']]);
      wrap.append(card);
    }
    if(!wrap.children.length)return false;
    details(wrap,'Đọc toàn bộ phân tích 4M / CANSLIM / SEPA-VCP / VPA',data.answer||'');
    if(meta)wrap.append(element('small',meta,'sr-decision-source'));
    parent.append(wrap);
    // Keep the conclusion in view when a long answer arrives.
    parent.scrollTop=Math.max(0,wrap.offsetTop-parent.offsetTop);
    return true;
  }
  window.StockRadarDecisionView={render,stillFresh};
})();
