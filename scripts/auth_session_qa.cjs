// Real browser and Supabase SDK with isolated HTTP fixtures; no production account is created.
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({headless:true});
  const results=[];
  try {
    for(const tier of ['FREE','PAID']) {
      const context=await browser.newContext();
      const user={id:'11111111-1111-4111-8111-111111111111',aud:'authenticated',role:'authenticated',email:'qa@example.invalid',email_confirmed_at:new Date().toISOString(),app_metadata:{provider:'email'},user_metadata:{}};
      const encode=x=>Buffer.from(JSON.stringify(x)).toString('base64url');
      const access=encode({alg:'HS256',typ:'JWT'})+'.'+encode({sub:user.id,aud:'authenticated',exp:Math.floor(Date.now()/1000)+3600,role:'authenticated'})+'.test-only-signature';
      const session={access_token:access,token_type:'bearer',expires_in:3600,expires_at:Math.floor(Date.now()/1000)+3600,refresh_token:'test-only-refresh-token',user};
      await context.route('https://xamviatbxufjlpiwhebb.supabase.co/**',async route=>{
        const url=new URL(route.request().url());let body={};
        if(url.pathname.endsWith('/token'))body=session;
        else if(url.pathname.endsWith('/user'))body=user;
        else if(url.pathname.includes('get_my_stockradar_access'))body={account_tier:tier,account_status:'ACTIVE',quota:{unlimited:tier==='PAID',limit:tier==='PAID'?null:10,remaining:tier==='PAID'?null:7}};
        else if(url.pathname.includes('/profiles'))body={account_tier:tier,account_status:'ACTIVE'};
        else if(url.pathname.includes('/rest/'))body=[];
        await route.fulfill({status:200,contentType:'application/json',body:JSON.stringify(body)});
      });
      const page=await context.newPage();
      await page.goto('http://127.0.0.1:8765/dang-nhap/');
      await page.locator('#login-email').fill(user.email);
      await page.locator('#login-password').fill('test-only-password-123');
      await page.locator('[data-auth-login-form] button[type=submit]').click();
      await page.waitForURL('http://127.0.0.1:8765/',{timeout:20000});
      const expected=tier==='PAID'?'premium':'free';
      await page.waitForFunction(t=>document.querySelector('[data-tier="'+t+'"]'),expected);
      if(tier==='FREE')assert.match(await page.locator('[data-tier="free"]').first().innerText(),/7\/10/);
      await page.reload();
      await page.waitForFunction(t=>document.querySelector('[data-tier="'+t+'"]'),expected);
      assert.ok(await page.evaluate(()=>Boolean(localStorage.getItem('stockradar-auth'))));
      await page.goto('http://127.0.0.1:8765/radar5/');
      await page.goto('http://127.0.0.1:8765/');
      await page.waitForFunction(t=>document.querySelector('[data-tier="'+t+'"]'),expected);
      const logout=page.locator('[data-auth-state-logout],[data-global-auth-logout],[data-auth-logout]').filter({visible:true}).first();
      await logout.click();
      await page.waitForFunction(()=>!localStorage.getItem('stockradar-auth'));
      await page.goto('http://127.0.0.1:8765/');
      await page.waitForFunction(()=>document.querySelector('[data-tier="guest"]'));
      assert.equal(await page.evaluate(()=>localStorage.getItem('sb-xamviatbxufjlpiwhebb-auth-token')),null);
      results.push({tier,login_home:true,reload:true,return_home:true,quota_persisted:true,logout:true});
      await context.close();
    }
  } finally { await browser.close(); }
  fs.writeFileSync('artifacts/auth-session-qa.json',JSON.stringify({fixture:true,results},null,2));
  console.log(JSON.stringify({fixture:true,results}));
})().catch(e=>{console.error(e);process.exitCode=1;});
