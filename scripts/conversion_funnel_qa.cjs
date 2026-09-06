// Isolated browser/HTTP fixtures. Never sends test events to Meta or creates a real account.
const {chromium,webkit}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const base=process.env.STOCKRADAR_QA_URL||'http://127.0.0.1:8765';
const api='https://xamviatbxufjlpiwhebb.supabase.co';
const receipt={ok:true,verification_required:true,registration_created:true,event_id:'12345678-1111-4111-8111-123456789012',plan:'free'};
const android='Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36';
const iphone='Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1';
const cases=[{name:'Facebook Android UA / Chromium',ua:android+' [FB_IAB/FB4A;FBAV/480.0.0.0]',width:360},
 {name:'Instagram iPhone UA / Chromium',ua:iphone+' Instagram 345.0.0.0',width:390},
 {name:'Chrome Android UA / Chromium',ua:android,width:430},
 {name:'iPhone UA / WebKit',ua:iphone,width:390,engine:'webkit'},
 {name:process.platform==='win32'?'Edge Desktop':'Desktop Chromium',channel:process.platform==='win32'?'msedge':undefined,width:1280}];
async function fixtures(context,{pixel='enabled',tier='GUEST',model='MODEL_READY',remaining=2,firstSeen=false}={}){
 const events=[],calls=[],errors=[];let rejected=false;
 const user={id:'11111111-1111-4111-8111-111111111111',aud:'authenticated',role:'authenticated',email:'qa@example.invalid',email_confirmed_at:new Date().toISOString(),app_metadata:{provider:'email'},user_metadata:{}};
 const enc=x=>Buffer.from(JSON.stringify(x)).toString('base64url');
 const token=enc({alg:'HS256',typ:'JWT'})+'.'+enc({sub:user.id,aud:'authenticated',role:'authenticated',exp:Math.floor(Date.now()/1000)+3600})+'.fixture';
 const session={access_token:token,refresh_token:'fixture-refresh',expires_in:3600,expires_at:Math.floor(Date.now()/1000)+3600,token_type:'bearer',user};
 if(tier!=='GUEST')await context.addInitScript(s=>localStorage.setItem('stockradar-auth',JSON.stringify(s)),session);
 if(firstSeen)await context.addInitScript(()=>localStorage.setItem('sr_guest_first_result_v2','1'));
 await context.route('**/assets/auth-config.js*',route=>route.fulfill({status:200,contentType:'application/javascript',body:fs.readFileSync('.pages-site/assets/auth-config.js','utf8')+`\nwindow.STOCKRADAR_META_CONFIG={enabled:${pixel!=='absent'},pixelId:'123456789012345'};`}));
 await context.route('https://connect.facebook.net/**',route=>pixel==='blocked'?route.abort('blockedbyclient'):route.fulfill({status:200,contentType:'application/javascript',body:'/* SDK fixture only: leave the fbq queue observable. */'}));
 await context.route('https://www.facebook.com/**',route=>route.abort());
 await context.route(api+'/**',async route=>{
  const headers={'access-control-allow-origin':base,'access-control-allow-headers':'authorization, apikey, content-type, x-client-info, x-supabase-api-version','access-control-allow-methods':'GET, POST, OPTIONS','access-control-allow-credentials':'true'};
  if(route.request().method()==='OPTIONS')return route.fulfill({status:204,headers});
  const p=new URL(route.request().url()).pathname;calls.push(p);let body={};
  if(p.endsWith('/conversion-event')){events.push(route.request().postDataJSON());body={accepted:true,recorded:false};}
  else if(p.endsWith('/signup-link')){const b=route.request().postDataJSON();assert.equal(b.plan,'free');assert.equal(b.product_email_daily_brief,false);assert.equal(b.product_email_event_alerts,false);assert.equal(b.measurement.first_touch.source,'facebook');return route.fulfill({status:rejected?409:202,headers,contentType:'application/json',body:JSON.stringify(rejected?{ok:false}:receipt)});}
  else if(p.endsWith('/stock-ai-guest')||p.endsWith('/stock-ai'))body={status:model==='MODEL_READY'?'READY':'READY_FALLBACK',model_status:model,model_notice:model==='MODEL_READY'?null:'Mô hình AI đang tạm gián đoạn do hạn mức dịch vụ.',tier,scope:'ticker',ticker:'FPT',answer_engine:model==='MODEL_READY'?'MODEL_STOCKRADAR':'STOCKRADAR_CORE',answer:'Nội dung phản hồi của mô hình trong kiểm thử cục bộ.',quota:{limit:tier==='GUEST'?3:10,remaining:tier==='GUEST'?remaining:8}};
  else if(p.endsWith('/token'))body=session;
  else if(p.endsWith('/user'))body=user;
  else if(p.includes('get_my_stockradar_access'))body={account_tier:tier==='PREMIUM'?'PAID':'FREE',account_status:'ACTIVE',quota:{remaining:8,limit:10}};
  else if(p.includes('/profiles'))body={account_tier:tier==='PREMIUM'?'PAID':'FREE',account_status:'ACTIVE'};
  else if(p.includes('/rest/'))body=[];
  if(p.endsWith('/stock-ai')&&tier==='GUEST'){body.tier='FREE';body.quota={limit:10,remaining:8};}
  await route.fulfill({status:200,headers,contentType:'application/json',body:JSON.stringify(body)});
 });
 return {events,calls,errors,session,reject:v=>rejected=v};
}
const meta=page=>page.evaluate(()=>Array.from(window.fbq?.queue||[],a=>Array.from(a)));
const count=(rows,name)=>rows.filter(e=>e[1]===name).length;
async function ask(page){await page.locator('.sr-center-form textarea').fill('Phân tích FPT');await page.locator('.sr-center-send').click();await page.locator('.sr-center-send:not([disabled])').waitFor();}
async function fill(form){await form.locator('[name=email]').fill('local@example.invalid');await form.locator('[name=password]').fill('Fixture-only-123!');await form.locator('[name=password_confirm]').fill('Fixture-only-123!');await form.locator('[name=terms]').check();}
(async()=>{
 const results=[];fs.mkdirSync('artifacts/funnel',{recursive:true});
 for(const spec of cases){
  const browser=await (spec.engine==='webkit'?webkit:chromium).launch({headless:true,channel:spec.channel});
  try{
   const context=await browser.newContext({viewport:{width:spec.width,height:844},userAgent:spec.ua||'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0',isMobile:spec.width<600,hasTouch:spec.width<600});
   const h=await fixtures(context),page=await context.newPage();page.on('pageerror',e=>h.errors.push({surface:spec.name,message:e.message,stack:e.stack,path:new URL(page.url()).pathname}));
   await page.goto(base+'/?utm_source=facebook&utm_campaign=free_launch&fbclid=Abcde_123456789');
   await page.waitForFunction(()=>window.StockRadarAnalytics&&document.querySelector('.sr-center-form textarea'));
   const input=page.locator('.sr-center-form textarea');assert.ok((await input.boundingBox()).y<844,'AI input should be on the first screen');
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
   if(spec.width<600){await input.fill('FPT');await input.press('Enter');assert.ok((await input.inputValue()).includes('\n'));assert.equal(h.calls.filter(p=>p.endsWith('/stock-ai-guest')).length,0);}
   await ask(page);await page.locator('[data-guest-free-cta="first"]').waitFor();
   assert.equal(count(await meta(page),'AIQuestion'),1);assert.ok(await page.locator('.sr-center-log').isVisible());
   await page.screenshot({path:`artifacts/funnel/home-${spec.width}-${spec.engine||'chromium'}.png`,fullPage:true});
   await page.locator('[data-guest-free-cta] a').click();await page.waitForURL(base+'/signup/?plan=free');assert.ok(h.events.some(e=>e.event_name==='guest_free_cta_click'));await page.waitForLoadState('networkidle');await page.goBack();
   await page.waitForLoadState('networkidle');await page.reload();await ask(page);assert.equal(await page.locator('[data-guest-free-cta]').count(),0,'reload must not reset first CTA');
   // The first CTA remains discoverable through browser back/forward; follow the canonical destination.
   await page.goto(base+'/signup/?plan=free');await page.waitForFunction(()=>document.documentElement.dataset.signupPlan==='free');
   const form=page.locator('[data-auth-signup-form]');assert.equal(await form.locator('[name=company]').isVisible(),false);assert.equal(await form.locator('.signup-email-options').isVisible(),false);assert.equal(await form.locator('.signup-plan-selector').isVisible(),false);
   assert.match(await page.locator('h1').innerText(),/Free/);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
   await form.locator('button[type=submit]').click();assert.equal(count(await meta(page),'CompleteRegistration'),0);assert.equal(h.calls.filter(p=>p.endsWith('/signup-link')).length,0);
   await fill(form);h.reject(true);await form.locator('button[type=submit]').click();await form.locator('.auth-message.error').waitFor();assert.equal(count(await meta(page),'CompleteRegistration'),0);
   await fill(form);h.reject(false);await form.locator('button[type=submit]').click();await form.locator('.auth-message.success').waitFor();
   assert.equal(count(await meta(page),'StartRegistration'),1);assert.equal(count(await meta(page),'CompleteRegistration'),1);
   await page.evaluate(r=>window.StockRadarAnalytics.signupAccepted(r),receipt);assert.equal(count(await meta(page),'CompleteRegistration'),1);
   assert.ok(await page.locator('[data-signup-after-verification]').isVisible());await page.screenshot({path:`artifacts/funnel/signup-${spec.width}-${spec.engine||'chromium'}.png`});
   assert.doesNotMatch(JSON.stringify([...h.events,...await meta(page)]),/local@|Fixture-only|Abcde_123456789|Phân tích FPT/);
   await page.goBack();await page.goForward();assert.equal((await page.evaluate(()=>window.StockRadarAnalytics.attribution())).first.utm_campaign,'free_launch');
   await page.goto(base+'/dang-nhap/?verified=1');await page.locator('#login-email').fill('local@example.invalid');await page.locator('#login-password').fill('Fixture-only-123!');await page.locator('[data-auth-login-form] button[type=submit]').click();await page.waitForURL(base+'/');await page.waitForFunction(()=>document.querySelector('[data-tier="free"]'));
   await page.waitForLoadState('networkidle');await page.reload();await page.waitForFunction(()=>document.querySelector('[data-tier="free"]'));assert.equal(await page.locator('[data-guest-free-cta]').count(),0);assert.ok(await page.evaluate(()=>localStorage.getItem('stockradar-auth')));
   await ask(page);await page.waitForLoadState('networkidle');assert.equal(h.events.filter(e=>e.event_name==='return_to_ai_after_registration').length,1);assert.equal(await page.locator('[data-guest-free-cta]').count(),0);
   assert.deepEqual(h.errors,[]);results.push({surface:spec.name,width:spec.width,fixture:true,first_screen:true,cta_dedupe:true,free_form:true,meta_completion_once:true,back_forward:true,login_reload:true,physical_device:false});await context.close();
  }finally{await browser.close();}
 }
 const browser=await chromium.launch({headless:true});
 try{
  for(const options of [{pixel:'absent'},{pixel:'blocked'},{tier:'FREE'},{tier:'PREMIUM'},{model:'MODEL_CREDIT_BLOCKED'},{remaining:1,firstSeen:true},{remaining:0,firstSeen:true}]){
   const context=await browser.newContext({viewport:{width:390,height:844}}),h=await fixtures(context,options),page=await context.newPage();await page.goto(base+'/');await ask(page);
   if(options.tier||options.model)assert.equal(await page.locator('[data-guest-free-cta]').count(),0);
   if(options.model)assert.equal(h.events.filter(e=>e.event_name==='ai_result_success').length,0);
   if(options.remaining===1)assert.ok(await page.locator('[data-guest-free-cta="last"]').isVisible());
   if(options.remaining===0)assert.ok(await page.locator('[data-guest-free-cta="exhausted"]').isVisible());
   assert.ok(await page.locator('.sr-center-send').isEnabled());results.push({...options,fixture:true,functional:true});await context.close();
  }
  // Email opens in a different browser with no PKCE verifier: clear login fallback, no loop.
  const context=await browser.newContext(),h=await fixtures(context,{pixel:'enabled'}),page=await context.newPage();
  await context.route(api+'/auth/v1/token**',route=>route.fulfill({status:400,contentType:'application/json',body:'{"error":"invalid_grant"}'}));
  await page.goto(base+'/?code=fixture-cross-browser-code');await page.waitForURL('**/dang-nhap/?callback=login_required');assert.match(await page.locator('[data-auth-message]').first().innerText(),/trình duyệt này/);assert.equal(count(await meta(page),'CompleteRegistration'),0);results.push({cross_browser_callback_fixture:true,clear_login_fallback:true});await context.close();
  const verified=await browser.newContext(),v=await fixtures(verified),vp=await verified.newPage();
  const hash=new URLSearchParams({access_token:v.session.access_token,refresh_token:v.session.refresh_token,expires_in:'3600',token_type:'bearer',type:'signup'});
  await vp.goto(base+'/#'+hash);await vp.waitForFunction(()=>document.querySelector('[data-tier="free"]'));
  assert.ok(await vp.evaluate(()=>localStorage.getItem('stockradar-auth')));assert.equal(new URL(vp.url()).hash,'');assert.equal(count(await meta(vp),'CompleteRegistration'),0);
  await vp.reload();await vp.waitForFunction(()=>document.querySelector('[data-tier="free"]'));results.push({email_callback_fixture:true,free_session_restored:true,reload:true});await verified.close();
 }finally{await browser.close();}
 fs.writeFileSync('artifacts/funnel/browser-qa.json',JSON.stringify({results,meta_events_manager_verified:false,physical_devices_verified:false},null,2));console.log(JSON.stringify({passed:results.length,results}));
})().catch(e=>{console.error(e);process.exitCode=1;});
