const {chromium}=require('playwright');const assert=require('node:assert/strict');const fs=require('node:fs');
// Deliberately synthetic observations; intercepted HTTP only, never published or sent to the database.
const fixture={schema_version:'STOCKRADAR_RESEARCH_RADAR_V1',mode:'RESEARCH_SCREEN',snapshot:{as_of_date:'2026-09-04',evaluated_at:'2026-09-05T02:54:31Z'},coverage:{total:3,research_ready:2,initial_setups:1,published_buys:0},schedule:{},items:[
 {ticker:'AAA',sector:'Ngân hàng',price:25000,score:70,as_of_date:'2026-09-04',fresh:true,research_ready:true,initial_setup:false,new_buy_allowed:false,scores:{technical:80,flow:65},technical:{change_pct:0,ma20:24000,ma50:23000,ma200:22000,pivot:26000,volume:1000000,volume20:1500000}},
 {ticker:'BBB',sector:'Thực phẩm',price:20000,score:60,as_of_date:'2026-09-04',fresh:true,research_ready:true,initial_setup:true,new_buy_allowed:false,scores:{technical:70,flow:60},technical:{change_pct:1}},
 {ticker:'L10',sector:'Xây dựng',price:null,score:null,as_of_date:'2026-09-04',fresh:true,research_ready:false,initial_setup:false,new_buy_allowed:false,scores:{},technical:{}}
]};
const base=process.env.STOCKRADAR_QA_URL||'http://127.0.0.1:8765';
(async()=>{const browser=await chromium.launch();try{
 for(const width of [1440,768,390]){
  const context=await browser.newContext({viewport:{width,height:950}});
  const user={id:'11111111-1111-4111-8111-111111111111',aud:'authenticated',role:'authenticated',email:'radar-qa@example.invalid',email_confirmed_at:new Date().toISOString(),app_metadata:{},user_metadata:{}};
  const encode=x=>Buffer.from(JSON.stringify(x)).toString('base64url');const token=encode({alg:'HS256'})+'.'+encode({sub:user.id,exp:Math.floor(Date.now()/1000)+3600,role:'authenticated'})+'.test-only';
  const session={access_token:token,refresh_token:'test-only',expires_at:Math.floor(Date.now()/1000)+3600,expires_in:3600,token_type:'bearer',user};
  await context.addInitScript(s=>{localStorage.setItem('stockradar-auth',JSON.stringify(s));localStorage.setItem('stockradar-auth-migrated-v1','1');},session);
  let calls=0;
  await context.route('https://xamviatbxufjlpiwhebb.supabase.co/**',async route=>{const url=route.request().url();let body={};
   if(url.includes('/get_stockradar_radar_v1')){calls++;assert.equal(route.request().headers().authorization,'Bearer '+token);body=fixture;}
   else if(url.includes('/user'))body=user;else if(url.includes('/token'))body=session;
   else if(url.includes('get_my_stockradar_access')||url.includes('/profiles'))body={account_tier:'PAID',account_status:'ACTIVE',quota:{unlimited:true}};
   else if(url.includes('/rest/'))body=[];
   await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
  });
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/radar5/',{waitUntil:'domcontentloaded'});await page.locator('[data-lr-row]').first().waitFor();
  assert.equal(await page.locator('[data-lr-row]').count(),2);assert.match(await page.locator('[data-lr-page]').innerText(),/2 mã/);
  assert.equal(await page.locator('[data-lr-row]').first().getAttribute('data-lr-row'),'AAA');
  assert.equal(await page.locator('[data-lr-total]').innerText(),'3');assert.equal(await page.locator('[data-lr-buys]').innerText(),'0');
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
  assert.equal(await page.locator('.market-tape,.product-subnav,.v4-fallback').count(),0);
  await page.screenshot({path:`artifacts/screenshots/radar-fixture-${width}.png`,fullPage:true});
  assert(await page.locator('[data-lr-next]').isDisabled());
  await page.locator('[data-lr-search]').fill('bbb');assert.equal(await page.locator('[data-lr-row]').count(),1);
  await page.locator('[data-lr-ticker="BBB"]').click();assert(await page.locator('[data-lr-detail]').isVisible());assert.match(await page.locator('[data-lr-detail]').innerText(),/20 \/ 50 \/ 200/);
  await page.locator('[data-lr-reset]').click();await page.locator('[data-lr-filter]').selectOption('initial');assert.equal(await page.locator('[data-lr-row]').count(),1);
  await page.locator('[data-lr-filter]').selectOption('buy');assert.equal(await page.locator('[data-lr-row]').count(),0);assert.match(await page.locator('[data-lr-results]').innerText(),/Không có mã/);
  await page.locator('[data-lr-filter]').selectOption('all');await page.locator('[data-lr-search]').fill('L10');assert.equal(await page.locator('[data-lr-row="L10"]').count(),1);
  await page.locator('[data-lr-reset]').click();await page.locator('[data-lr-tab="sectors"]').click();assert((await page.locator('.lr-sector').count())>1);
  await page.locator('[data-lr-open-sector="Ngân hàng"]').click();assert.equal(await page.locator('[data-lr-sector]').inputValue(),'Ngân hàng');
  await page.locator('[data-lr-search]').fill('zzz');assert.match(await page.locator('[data-lr-results]').innerText(),/Không có mã/);
  await page.locator('[data-lr-reset]').click();await page.locator('[data-lr-refresh]').click();await page.waitForFunction(()=>!document.querySelector('[data-lr-refresh]').disabled);assert(calls>=2);
  await page.route('**/get_stockradar_radar_v1',r=>r.abort());
  await page.locator('[data-lr-refresh]').click();await page.waitForFunction(()=>!document.querySelector('[data-lr-refresh]').disabled);
  assert.equal(await page.locator('[data-lr-row]').count(),2);assert.match(await page.locator('[data-lr-message]').innerText(),/Chưa cập nhật được/);
  await page.unroute('**/get_stockradar_radar_v1');await page.locator('[data-lr-refresh]').click();await page.waitForFunction(()=>!document.querySelector('[data-lr-refresh]').disabled);
  assert(await page.locator('[data-lr-message]').isHidden());
  await page.route('**/get_stockradar_radar_v1',r=>r.fulfill({status:403,contentType:'application/json',body:'{}'}));
  await page.locator('[data-lr-refresh]').click();await page.waitForFunction(()=>!document.querySelector('[data-lr-refresh]').disabled);
  assert.equal(await page.locator('[data-lr-row]').count(),0);assert(await page.locator('[data-lr-workspace]').isHidden());
  assert.deepEqual(errors,[]);console.log(JSON.stringify({width,fixture:true,rows:3,ranked:2,filters:'PASS',sector:'PASS',refresh:'PASS'}));await context.close();
 }
 const guest=await browser.newPage();await guest.goto(base+'/radar5/',{waitUntil:'domcontentloaded'});await guest.waitForFunction(()=>document.querySelector('[data-lr-message]')?.textContent.includes('Đăng nhập để xem'));assert.equal(await guest.locator('[data-lr-row]').count(),0);console.log('Guest login state: PASS');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
