// Final-artifact browser test. Synthetic sessions only; no real credentials or model requests.
const {chromium}=require('playwright');const assert=require('node:assert/strict');
const base=process.env.STOCKRADAR_QA_URL||'http://127.0.0.1:8767';
(async()=>{const browser=await chromium.launch({headless:true});try{
 for(const width of [390,1440]){
  const context=await browser.newContext({viewport:{width,height:1000}});const network=[];
  await context.route('https://xamviatbxufjlpiwhebb.supabase.co/**',async r=>{network.push(r.request().url());await r.fulfill({status:200,contentType:'application/json',body:'[]'});});
  await context.addInitScript(()=>{
   window.__channelSession={user:{id:'11111111-1111-4111-8111-111111111111'},access_token:'fixture-not-a-real-token'};window.__channelRows=[];window.__channelCalls=[];window.__channelAuth=[];
   window.StockRadarAuthClient={auth:{getSession:async()=>({data:{session:window.__channelSession}}),onAuthStateChange:fn=>window.__channelAuth.push(fn)},rpc:async(name,args)=>{
    window.__channelCalls.push({name,args});if(name==='get_my_stockradar_project_channel')return {data:{available:true,automatic_model_trigger:false}};
    if(name==='submit_my_stockradar_project_question'){const row={id:'33333333-3333-4333-8333-333333333333',question:args.p_question,horizon:args.p_horizon,status:'WAITING',origin:'WEBSITE',created_at:new Date().toISOString()};window.__channelRows=[row];return {data:{id:row.id,status:row.status}};}
    return {data:{account_status:'ACTIVE',account_tier:'PAID'}};
   },from:table=>{const q={};for(const m of ['select','eq','order','limit'])q[m]=()=>q;q.then=resolve=>Promise.resolve({data:table==='stockradar_project_questions'?window.__channelRows:[],error:null}).then(resolve);return q;}};
  });
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(base+'/ai/');await page.locator('.sr-project-channel').waitFor({state:'visible'});
  assert.equal(await page.locator('.sr-center-form').isVisible(),false);await page.locator('[aria-label="Câu hỏi gửi vào dự án"]').fill('PRIVATE_OWNER_QUESTION');await page.getByRole('button',{name:'Gửi vào hàng đợi dự án'}).click();await page.locator('.sr-project-state').waitFor();assert.match(await page.locator('.sr-project-state').innerText(),/Chờ dự án xử lý/);
  await page.evaluate(()=>{const r=window.__channelRows[0];r.status='ANSWERED';r.answer='<img src=x onerror=alert(1)> PRIVATE_PROJECT_REPLY';r.answer_source='CHATGPT_PROJECT';r.answered_at=new Date().toISOString();});
  await page.locator('.sr-project-answer').waitFor({timeout:9000});assert.match(await page.locator('.sr-project-answer').innerText(),/PRIVATE_PROJECT_REPLY/);assert.equal(await page.locator('.sr-project-answer img').count(),0);
  assert.equal(await page.evaluate(()=>window.__channelCalls.filter(x=>x.name==='submit_my_stockradar_project_question').length),1);assert.ok(!network.some(x=>/stock-ai|openai\.com/.test(x)));assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
  await page.evaluate(()=>{window.__channelSession=null;window.__channelAuth.forEach(fn=>fn('SIGNED_OUT',null));});assert.equal(await page.locator('.sr-project-channel').isVisible(),false);assert.ok(!(await page.locator('body').innerText()).includes('PRIVATE_PROJECT_REPLY'));assert.deepEqual(errors,[]);await context.close();
 }
 console.log('PASS: 2 viewports, submit queue, waiting state, reply polling, no inference, XSS text rendering, owner logout isolation.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
