// Browser integration: real status endpoint, released fixture, failed request.
// The fixture is intercepted in this local browser only and never published.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const base=process.env.STOCKRADAR_QA_URL||'http://127.0.0.1:8765';
  const out='artifacts/screenshots';fs.mkdirSync(out,{recursive:true});
  for(const width of [1440,390])for(const mode of ['live','released','unavailable']){
    const page=await browser.newPage({viewport:{width,height:1000}});
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    if(mode!=='live')await page.route('**/rest/v1/rpc/get_stockradar_recommendation_status_v1',route=>mode==='unavailable'?route.fulfill({status:503,body:'unavailable'}):route.fulfill({json:{schema_version:'STOCKRADAR_RECOMMENDATION_STATUS_V1',data_status:'READY',checked_at:new Date().toISOString(),snapshot:{as_of_date:'2026-09-04',evaluated_at:'2026-09-04T03:30:00Z'},schedule:{next_review_at:'2026-09-07T01:10:00Z'},email:{ready:true},items:[{ticker:'ZZZ',action:'MUA',publish_status:'PUBLISHED',expires_at:new Date(Date.now()+3600000).toISOString(),reference_price:20000,buy_zone:[19800,20100],stop_loss:18500,target:24000,risk_reward:2.5,confirmed_at:'2026-09-04T03:30:00Z',email_status:'QUEUED',email_scheduled_at:'2026-09-04T03:32:00Z'},{ticker:'BAD',action:'MUA',publish_status:'DRAFT',expires_at:new Date(Date.now()+3600000).toISOString()},{ticker:'OLD',action:'MUA',publish_status:'PUBLISHED',expires_at:'2020-01-01T00:00:00Z'}]}}));
    await page.goto(base,{waitUntil:'domcontentloaded'});
    await page.waitForFunction(()=>!document.querySelector('[data-home-reco-table]')?.hidden || !document.querySelector('[data-home-reco-empty] strong')?.textContent.includes('Đang kiểm tra'),null,{timeout:20000});
    if(mode==='released'){
      assert.equal(await page.locator('[data-home-reco-body] tr').count(),1);
      const text=await page.locator('[data-home-reco-body]').innerText();
      for(const part of ['ZZZ','20.000','18.500','24.000','10:30','Chờ gửi: 10:32'])assert.ok(text.includes(part),part);
      assert.equal(await page.locator('[data-home-reco-body] a').getAttribute('href'),'co-phieu/?ticker=ZZZ');
      assert.ok(!text.includes('Đã gửi'));
    }else if(mode==='unavailable'){
      assert.match(await page.locator('[data-home-reco-empty]').innerText(),/Chưa tải được/);
      assert.equal(await page.locator('[data-home-reco-body] tr').count(),0);
    }else{
      assert.match(await page.locator('[data-reco-price-date]').innerText(),/\d{2}\/\d{2}\/\d{4}/);
      assert.match(await page.locator('[data-reco-reviewed-at]').innerText(),/\d{2}:\d{2}/);
    }
    assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Page overflow');
    assert.deepEqual(errors,[]);
    await page.evaluate(()=>{const p=document.createElement('p');p.id='framework-qa';p.textContent='4M CANSLIM SEPA/VCP VPA Ichimoku';document.querySelector('[data-stockradar-ai-center]').append(p);});
    await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    assert.equal(await page.locator('#framework-qa').innerText(),'4M CANSLIM SEPA/VCP VPA Ichimoku');
    await page.locator('.reco-shell').screenshot({path:`${out}/recommendations-${width}-${mode}.png`});
    console.log(`PASS ${width}px ${mode}`);await page.close();
  }
  await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
