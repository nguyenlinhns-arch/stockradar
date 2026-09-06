// Isolated HTTP fixtures in Chromium: no account/email/payment is created.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true}),results=[];
 try{
  for(const plan of ['free','premium']){
   const context=await browser.newContext({viewport:{width:390,height:844}}),requests=[];
   await context.route('https://xamviatbxufjlpiwhebb.supabase.co/**',async route=>{
    const path=new URL(route.request().url()).pathname;requests.push(path);
    if(path.endsWith('/signup-link')){
     const b=route.request().postDataJSON();assert.equal(b.plan,plan);
     if(plan==='free'){assert.equal(b.product_email_daily_brief,false);assert.equal(b.product_email_event_alerts,false);}
     return route.fulfill({status:202,contentType:'application/json',body:JSON.stringify({ok:true,verification_required:true,plan})});
    }
    return route.fulfill({status:200,contentType:'application/json',body:'{}'});
   });
   const page=await context.newPage();await page.goto('http://127.0.0.1:8765/signup/?plan='+plan);
   const form=page.locator('[data-auth-signup-form]');
   await form.locator('[name=email]').fill('local@example.invalid');
   await form.locator('[name=password]').fill('test-only-password-123');
   await form.locator('[name=password_confirm]').fill('test-only-password-123');
   await form.locator('[name=terms]').check();
   await form.locator('button[type=submit]').click();
   await page.waitForFunction(()=>document.querySelector('[data-auth-signup-form] .auth-message.success')?.textContent.includes('xác minh'));
   assert.equal(await form.locator('[name=password]').inputValue(),'');
   assert.equal(await page.evaluate(()=>localStorage.getItem('stockradar-auth')),null);
   assert.ok(!requests.some(p=>p.endsWith('/token')||p.includes('create_my_checkout_request')));
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2),false);
   assert.match(page.url(),/\/signup\//);
   results.push({plan,verification_required:true,no_auto_login:true,no_checkout_or_premium_grant:true,mobile:true});
   await context.close();
  }
 } finally {await browser.close();}
 console.log(JSON.stringify({fixture:true,results}));
})().catch(e=>{console.error(e);process.exitCode=1;});
