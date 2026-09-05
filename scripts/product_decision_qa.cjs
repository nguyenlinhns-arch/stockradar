// Real browser, isolated fixtures. No production AI request, payment or email is submitted.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.STOCKRADAR_QA_URL||'http://127.0.0.1:8765';
const api='https://xamviatbxufjlpiwhebb.supabase.co';
(async()=>{
 fs.mkdirSync('artifacts/audit-20260905',{recursive:true});
 const browser=await chromium.launch({headless:true}),results=[];
 try{
  for(const width of [360,390,430,768,1440]){
   const context=await browser.newContext({viewport:{width,height:950}});
   const events=[];
   await context.route(api+'/**',async route=>{
    if(route.request().url().endsWith('/conversion-event'))events.push(route.request().postDataJSON());
    await route.fulfill({status:200,contentType:'application/json',body:'{}'});
   });
   const page=await context.newPage();await page.goto(base+'/');
   await page.waitForFunction(()=>window.StockRadarDecisionView&&window.StockRadarAnalytics);
   await page.waitForTimeout(700);
   assert.equal(await page.locator('.home-workspace .home-market-bar').isVisible(),true,'runtime transforms must preserve the data status below the hero');
   assert.match(await page.locator('.home-market-bar').innerText(),/UNAVAILABLE/);
   const nav=await page.locator('[data-nav-menu]').first().innerText();
   for(const label of ['AI StockRadar','Khuyến nghị','Hiệu quả','Theo dõi','Premium'])assert.ok(nav.includes(label));
   const at=new Date().toISOString(),day=new Date(Date.now()+7*3600000).toISOString().slice(0,10);
   const c={schema_version:'STOCKRADAR_DECISION_CARD_V1',ticker:'ZZZ',horizon:'SHORT_TERM',conclusion:'ĐẠT ĐIỂM MUA – EARLY BREAKOUT',public_action_allowed:true,
    data:{fresh:true,status:'DELAYED',as_of_date:day,updated_at:at,source_status:'VERIFIED_RELEASE',expires_at:new Date(Date.now()+3600000).toISOString()},price:50000,
    buy_zone:{low:49500,high:50500},stop_loss:47000,targets:{short_term:57000,three_to_six_months:61000,twelve_months:68000},position_pct:25,
    moving_averages:{ma10:49000,ma50:48000,ma150:46000,ma200:45000},reasons:['Khối lượng đạt điều kiện của báo cáo.','<img src=x onerror=alert(1)>'],conditions:['Luận điểm cần rà soát khi mất vùng hỗ trợ.']};
   await page.evaluate(card=>{
    const payload={scope:'ticker',tier:'FREE',decision_cards:[card],answer:'Chi tiết phương pháp và giả định của fixture.'};
    window.StockRadarDecisionView.render(document.querySelector('.sr-center-log'),payload);
    window.StockRadarAnalytics.aiSubmitted();window.StockRadarAnalytics.aiResult(payload);
   },c);
   const card=page.locator('[data-decision-ticker="ZZZ"]').first();
   assert.match(await card.innerText(),/^KẾT LUẬN: ZZZ — ĐẠT ĐIỂM MUA/);
   for(const value of ['47.000đ','57.000đ','61.000đ','68.000đ','25%'])assert.ok((await card.innerText()).includes(value));
   assert.equal(await card.locator('img').count(),0,'untrusted reasons render as text');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
   assert.ok(await card.locator('strong').first().evaluate(e=>parseFloat(getComputedStyle(e).fontSize)>=16),'decision conclusion must remain readable on mobile');
   await card.screenshot({path:`artifacts/audit-20260905/decision-${width}.png`});
   const research={...c,conclusion:'CHƯA MUA',public_action_allowed:false,data:{...c.data,status:'RESEARCH'},estimated_plan:{status:'MODEL_SCENARIO',short_term:{target:55000,stop_loss:47500,entry:50000,condition:'Kịch bản có điều kiện, chưa phải điểm mua.'},medium_term:{at_3_months:53000,at_6_months:56000},long_term:{target:60000}}};
   await page.evaluate(card=>window.StockRadarDecisionView.render(document.querySelector('.sr-center-log'),{scope:'ticker',decision_cards:[card],answer:'research fixture'}),research);
   const researchText=await page.locator('[data-decision-ticker="ZZZ"]').last().innerText();
   assert.ok(researchText.indexOf('55.000đ')<researchText.indexOf('Chưa phát hành vùng mua'),'estimated targets remain near the conclusion, explicitly labelled');
   assert.match(researchText,/độ tin cậy thấp/);
   const stale={...c,data:{...c.data,updated_at:'2020-01-01T00:00:00Z'}};
   await page.evaluate(card=>window.StockRadarDecisionView.render(document.querySelector('.sr-center-log'),{scope:'ticker',decision_cards:[card],answer:'old fixture'}),stale);
   const last=page.locator('[data-decision-ticker="ZZZ"]').last();
   assert.match(await last.innerText(),/CHƯA ĐỦ DỮ LIỆU ĐỂ RA QUYẾT ĐỊNH/);
   assert.doesNotMatch(await last.innerText(),/57\.000đ|47\.000đ/);
   await page.waitForTimeout(200);
   assert.ok(events.some(e=>e.action_name==='meaningful_report'));
   assert.ok(events.some(e=>e.action_name==='free_activation'));
   for(const e of events)for(const key of ['message','answer','history','holdings','portfolio_value','password','token','jwt'])assert.equal(key in e,false);
   results.push({width,decision:true,stale_fail_closed:true,xss_safe:true,analytics_private:true});await context.close();
  }
  for(const mode of ['paused','unavailable','ready']){
   let readiness=mode==='ready',status='PENDING',creates=0,confirms=0,verified=false;
   const context=await browser.newContext({viewport:{width:390,height:844}});
   const user={id:'11111111-1111-4111-8111-111111111111',aud:'authenticated',role:'authenticated',email:'qa@example.invalid',app_metadata:{provider:'email'},user_metadata:{}};
   const encode=x=>Buffer.from(JSON.stringify(x)).toString('base64url');
   const access=encode({alg:'HS256',typ:'JWT'})+'.'+encode({sub:user.id,aud:'authenticated',exp:Math.floor(Date.now()/1000)+3600,role:'authenticated'})+'.test-only-signature';
   const session={access_token:access,refresh_token:'test-only-refresh',token_type:'bearer',expires_at:Math.floor(Date.now()/1000)+3600,expires_in:3600,user};
   await context.addInitScript(s=>localStorage.setItem('stockradar-auth',JSON.stringify(s)),session);
   await context.route('https://img.vietqr.io/**',route=>route.fulfill({status:200,contentType:'image/svg+xml',body:'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200"><text x="10" y="30">QA fixture</text></svg>'}));
   await context.route(api+'/**',async route=>{
    const url=route.request().url();let body={};
    if(url.endsWith('/user'))body=user;
    else if(url.includes('/token'))body=session;
    else if(url.includes('get_my_stockradar_access'))body={account_tier:verified?'PAID':'FREE',account_status:'ACTIVE'};
    else if(url.includes('/profiles'))body={account_tier:verified?'PAID':'FREE',account_status:'ACTIVE'};
    else if(url.includes('get_stockradar_product_readiness_v1')){
     if(mode==='unavailable')return route.fulfill({status:503,contentType:'application/json',body:'{}'});
     body={schema_version:'STOCKRADAR_PRODUCT_READINESS_V1',checkout_ready:readiness,status:readiness?'READY':'PAUSED'};
    }else if(url.includes('create_my_checkout_request')){
     creates++;body={request_id:'fixture-request',checkout_enabled:true,status,amount_vnd:199000,payment_reference:'SR12345678',expires_at:new Date(Date.now()+1800000).toISOString(),bank_bin:'970432',bank_name:'QA Bank',account_number:'0000000000',account_name:'QA Fixture'};
    }else if(url.includes('confirm_my_checkout_request')){confirms++;status='USER_CONFIRMED';body={status};}
    else if(url.includes('get_my_checkout_request'))body={status:verified?'PAID':status};
    await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
   });
   const page=await context.newPage();await page.goto(base+'/thanh-toan/?plan=premium');
   await page.waitForFunction(()=>document.querySelector('[data-checkout-account-email]')?.textContent==='qa@example.invalid');
   if(mode==='ready'){
    await page.locator('[data-checkout-payment]').waitFor({state:'visible'});
    assert.equal(creates,1);assert.ok(await page.locator('[data-checkout-qr-image]').getAttribute('src'));
    await page.locator('[data-checkout-confirm]').click();
    await page.waitForFunction(()=>document.querySelector('[data-checkout-state]')?.textContent.includes('chờ đối soát'));
    assert.equal(confirms,1);assert.doesNotMatch(await page.locator('[data-checkout-state]').innerText(),/đã được gửi|Premium đang hoạt động/);
    readiness=false;await page.waitForFunction(()=>document.body.dataset.checkoutReady==='false',{},{timeout:12000});
    assert.equal(await page.locator('[data-checkout-payment]').isVisible(),false);
    assert.equal(await page.locator('[data-checkout-qr-image]').getAttribute('src'),null);
    verified=true;await page.waitForFunction(()=>document.querySelector('[data-checkout-state]')?.textContent.includes('Thanh toán đã được xác minh'),{},{timeout:12000});
    await page.waitForFunction(()=>document.querySelector('[data-global-account-tier]')?.textContent?.includes('Premium')||document.body.innerText.includes('Mở tài khoản Premium'),{},{timeout:12000});
   }else{
    await page.waitForTimeout(700);assert.equal(creates,0);assert.equal(confirms,0);
    assert.equal(await page.locator('[data-checkout-payment]').isVisible(),false);
    assert.equal(await page.locator('[data-checkout-qr-image]').getAttribute('src'),null);
    assert.equal(await page.locator('[data-checkout-confirm]').isDisabled(),true);
   }
   results.push({checkout:mode,fail_closed:true,verified_only:true});await context.close();
  }
 }finally{await browser.close();}
 fs.writeFileSync('artifacts/audit-20260905/product-decision-qa.json',JSON.stringify({fixture:true,results},null,2));
 console.log(JSON.stringify({fixture:true,results}));
})().catch(e=>{console.error(e);process.exitCode=1;});
