import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {stripTypeScriptTypes} from 'node:module';

// Real RSA signatures, local issuer/JWKS fixtures; no production token is generated.
for(const [name,workflow,audience] of [
  ['stock-research-sync','sync-stockradar-research-cache.yml','stockradar-supabase-sync'],
  ['stock-alert-orchestrator','process-stockradar-alerts.yml','stockradar-alert-orchestrator'],
]) test(`${name} trusts the exact standard workflow claim and rejects alternate identities`,async()=>{
  const keys=await crypto.subtle.generateKey({name:'RSASSA-PKCS1-v1_5',modulusLength:2048,publicExponent:new Uint8Array([1,0,1]),hash:'SHA-256'},true,['sign','verify']);
  const jwk={...await crypto.subtle.exportKey('jwk',keys.publicKey),kid:'local-test'};
  const fetch=async url=>new Response(JSON.stringify(url.endsWith('openid-configuration')?{jwks_uri:'https://token.actions.githubusercontent.com/local-jwks'}:{keys:[jwk]}));
  const source=fs.readFileSync(new URL(`../../supabase/functions/${name}/index.ts`,import.meta.url),'utf8').replace(/^import .*;\r?\n/gm,'');
  const verify=new Function('Deno','fetch','createClient',stripTypeScriptTypes(source)+';return verifyGithubOidc;')({serve(){}},fetch,()=>{});
  const now=Math.floor(Date.now()/1000),wf=`nguyenlinhns-arch/stockradar/.github/workflows/${workflow}@refs/heads/main`;
  const claims={iss:'https://token.actions.githubusercontent.com',aud:audience,repository:'nguyenlinhns-arch/stockradar',ref:'refs/heads/main',workflow_ref:wf,iat:now,nbf:now-1,exp:now+300};
  const encode=x=>Buffer.from(JSON.stringify(x)).toString('base64url');
  async function token(overrides={}){
    const data=encode({alg:'RS256',kid:'local-test'})+'.'+encode({...claims,...overrides});
    return data+'.'+Buffer.from(await crypto.subtle.sign('RSASSA-PKCS1-v1_5',keys.privateKey,new TextEncoder().encode(data))).toString('base64url');
  }
  await verify(await token());
  await verify(await token({job_workflow_ref:wf}));
  for(const override of [{workflow_ref:undefined,job_workflow_ref:wf},{workflow_ref:'wrong'},{job_workflow_ref:'other'},{repository:'fork/stockradar'},{ref:'refs/heads/feature'},{aud:'other'},{exp:now-60},{iat:now-1000}]) await assert.rejects(()=>token(override).then(verify));
  const valid=await token();await assert.rejects(()=>verify(valid.slice(0,-8)+'badbad00'));
});
