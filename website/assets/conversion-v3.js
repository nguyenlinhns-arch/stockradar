(() => {
  'use strict';
  if (window.StockRadarAnalytics?.schemaVersion === 2) return;
  const UTM = ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'];
  const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  const memory = new Map();
  const ALIASES = {home_view:'landing_view',signup_start:'signup_started',signup_submit:'signup_submitted',signup_complete:'signup_completed',pricing_view:'premium_view',pro_view:'premium_view',pro_page_view:'premium_view',signup_premium_view:'premium_view',checkout_created:'checkout_started',checkout_start:'checkout_started',premium_preview_view:'premium_view'};
  const EVENTS = new Set(['landing_view','ai_question_started','ai_result_success','ai_result_failed','ai_guest_first_result','guest_free_cta_impression','guest_free_cta_click','signup_view','signup_started','signup_submitted','signup_verification_requested','signup_completed','login_success','return_to_ai_after_registration','premium_view','checkout_view','checkout_started','payment_submitted','ticker_lookup_submit','stock_report_view','premium_sample_view','performance_proof_view','conversion_click','free_activation','meaningful_report','meaningful_return_d1','meaningful_return_d7','email_cta_landing']);
  const ACTIONS = new Set(['signup_verification_requested','payment_submitted','checkout_created','ai_interaction','meaningful_report','free_activation','meaningful_return_d1','meaningful_return_d7','email_cta_landing','hero_ai','free','premium']);
  const HORIZONS = new Set(['SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION']);
  const safeTicker = v => /^[A-Z0-9]{3}$/.test(String(v||'')) && /[A-Z]/.test(v) && !['BTC','ETH','USD'].includes(v) ? v : null;
  const tier = v => ['PAID','TRIAL','PREMIUM'].includes(String(v).toUpperCase()) ? 'PREMIUM' : String(v).toUpperCase()==='FREE' ? 'FREE' : 'GUEST';
  const uid = () => globalThis.crypto?.randomUUID?.() || 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g,c=>{const r=Math.floor(Math.random()*16);return(c==='x'?r:(r&3)|8).toString(16);});
  function read(k,p=false) {try{return(p?localStorage:sessionStorage).getItem(k)||memory.get(k)||'';}catch(_){return memory.get(k)||'';}}
  function save(k,v,p=false) {memory.set(k,String(v));try{(p?localStorage:sessionStorage).setItem(k,String(v));}catch(_){}}
  function once(k,p=false) {if(read(k,p))return false;save(k,'1',p);return true;}
  function safeCampaign(v) {
    const s=typeof v==='string'?v.trim():'';
    return s.length<=120 && /^[\p{L}\p{N} _.,+-]+$/u.test(s) && !/(?:eyJ|sk-|sb_[a-z]+_|Bearer|https?)/i.test(s) ? s : '';
  }
  function safeTouch(value,withClick=false) {
    const v=value&&typeof value==='object'?value:{},out={source:['facebook','instagram','organic','direct','other'].includes(v.source)?v.source:'direct'};
    for(const k of UTM){const s=safeCampaign(v[k]);if(s)out[k]=s;}
    if(withClick&&/^[A-Za-z0-9_-]{10,512}$/.test(v.fbclid||''))out.fbclid=v.fbclid;
    if(Number.isFinite(v.at)&&v.at<=Date.now())out.at=v.at;
    return out;
  }
  function attribution() {
    const params=new URLSearchParams(window.location.search),current={};
    for(const k of UTM){const s=safeCampaign(params.get(k));if(s)current[k]=s;}
    const click=params.get('fbclid');if(/^[A-Za-z0-9_-]{10,512}$/.test(click||''))current.fbclid=click;
    let host='';try{host=new URL(document.referrer).hostname.toLowerCase();}catch(_){}
    const internal=!host||host===window.location.hostname||/(?:^|\.)supabase\.(?:co|com)$/.test(host),src=String(current.utm_source||'').toLowerCase();
    current.source=/^(instagram|ig)$/.test(src)||/(?:^|\.)instagram\.com$/.test(host)?'instagram'
      : /^(facebook|fb|meta)$/.test(src)||current.fbclid||/(?:^|\.)facebook\.com$/.test(host)?'facebook'
      : /(?:^|\.)(google\.[a-z.]+|bing\.com|duckduckgo\.com)$/.test(host)||current.utm_medium==='organic'?'organic':src||!internal?'other':'direct';
    current.at=Date.now();let old={};try{old=JSON.parse(read('sr_attribution_v2',true)||'{}');}catch(_){}
    const fresh=old.first?.at>Date.now()-30*86400000&&old.first.at<=Date.now(),explicit=UTM.some(k=>current[k])||current.fbclid||!internal;
    const result={first:fresh?safeTouch(old.first,true):current,last:fresh&&!explicit?safeTouch(old.last,true):current};
    save('sr_attribution_v2',JSON.stringify(result),true);return result;
  }
  const touches=attribution();let sid=read('sr_conversion_session_v2');
  if(!UUID.test(sid)){sid=uid();save('sr_conversion_session_v2',sid);}
  function plan(){return(document.querySelector('input[name="selected_plan"]:checked')?.value||new URLSearchParams(window.location.search).get('plan'))==='premium'?'PREMIUM':'FREE';}
  function path(){const p=String(window.location.pathname||'/');return /^\/[a-zA-Z0-9_/-]{0,150}$/.test(p)?p:'/';}
  function endpoint(){const base=window.STOCKRADAR_AUTH_CONFIG?.supabaseUrl||'https://xamviatbxufjlpiwhebb.supabase.co';return `${String(base).replace(/\/$/,'')}/functions/v1/conversion-event`;}
  function modelStatus(d){if(typeof d?.model_status==='string')return d.model_status;if(d?.mode==='METHOD_ONLY')return'MODEL_NOT_CALLED';if(/CREDIT|BALANCE|INSUFFICIENT_QUOTA|CIRCUIT_OPEN/.test(d?.reason||''))return'MODEL_CREDIT_BLOCKED';return d?.status==='READY'&&String(d?.answer_engine||'').startsWith('MODEL_')?'MODEL_READY':'MODEL_ERROR';}
  function successfulResult(d){return d?.status==='READY'&&modelStatus(d)==='MODEL_READY'&&typeof d.answer==='string'&&d.answer.trim().length>0;}

  // Optional SDK: no advanced matching, DOM auto-configuration, or custom identity data.
  const meta={status:'META_PIXEL_ID_NOT_CONFIGURED',loaded:false};
  function pixel(){
    const c=window.STOCKRADAR_META_CONFIG||{};
    if(!c.enabled||!/^\d{5,25}$/.test(String(c.pixelId||'')))return false;
    if(/bot\b|crawler|spider|Headless|facebookexternalhit|preview|slurp/i.test(navigator.userAgent||'')){meta.status='BOT_EXCLUDED';return false;}
    if(navigator.globalPrivacyControl===true||navigator.doNotTrack==='1'){meta.status='PRIVACY_OPT_OUT';return false;}
    const safeNavigation=url=>!url.hash.includes('=')&&/^\/[a-zA-Z0-9_/-]*$/.test(url.pathname)&&[...url.searchParams].every(([k,v])=>
      UTM.includes(k)?safeCampaign(v)===v&&v.length>0:k==='fbclid'?/^[A-Za-z0-9_-]{10,512}$/.test(v):k==='plan'?['free','premium'].includes(v):k==='ticker'?!!safeTicker(v):['verified','signed_out'].includes(k)?v==='1':false);
    // Auth owns callback URLs. Never let the SDK inspect a credential-bearing navigation.
    if(!safeNavigation(new URL(window.location.href))){meta.status='SENSITIVE_NAVIGATION_SKIPPED';return false;}
    try{if(document.referrer&&!safeNavigation(new URL(document.referrer))){meta.status='SENSITIVE_REFERRER_SKIPPED';return false;}}catch(_){return false;}
    if(meta.loaded)return true;if(window.fbq){meta.status='EXTERNAL_PIXEL_OWNER';return false;}
    const fbq=function(){if(fbq.callMethod)fbq.callMethod.apply(fbq,arguments);else if(fbq.queue.length<20)fbq.queue.push(arguments);};
    fbq.queue=[];fbq.loaded=true;fbq.version='2.0';fbq.push=fbq;window.fbq=fbq;window._fbq=fbq;
    fbq('set','autoConfig',false,String(c.pixelId));fbq('init',String(c.pixelId));
    const script=document.createElement('script');script.async=true;script.src='https://connect.facebook.net/en_US/fbevents.js';script.referrerPolicy='no-referrer';
    script.onerror=()=>{meta.status='PIXEL_SCRIPT_BLOCKED';fbq.queue.length=0;fbq.callMethod=()=>{};};script.onload=()=>{meta.status='BROWSER_PIXEL_LOADED_UNVERIFIED';};
    document.head.append(script);meta.loaded=true;meta.status='BROWSER_PIXEL_QUEUED';return true;
  }
  function sendMeta(event,d){
    if(!pixel())return;const id={eventID:d.event_id};
    if(event==='page_view')window.fbq('track','PageView',{},id);
    if(event==='ai_question_started')window.fbq('trackCustom','AIQuestion',{tier:d.tier,...(d.ticker?{ticker:d.ticker}:{}),horizon:d.horizon,source_page:d.source_path},id);
    if(event==='signup_started')window.fbq('trackCustom','StartRegistration',{registration_type:d.plan_interest.toLowerCase()},id);
    if(event==='signup_completed'&&once('sr_meta_registration:'+d.event_id,true))window.fbq('track','CompleteRegistration',{
      content_name:d.plan_interest==='PREMIUM'?'StockRadar Premium registration':'StockRadar Free',registration_type:d.plan_interest.toLowerCase(),source:touches.first.source,
      ...Object.fromEntries(UTM.filter(k=>touches.first[k]).map(k=>[k,touches.first[k]])),
    },id);
  }
  function emit(name,extra={},options={}){
    const event=ALIASES[name]||name;if(!EVENTS.has(event))return null;
    if(event==='signup_completed'&&options.registrationReceipt!==true)return null;
    const defaults={landing_view:'landing:'+path(),premium_view:'premium-view',signup_started:'signup-start:'+flowId(),signup_verification_requested:'verification:'+flowId(),checkout_started:'checkout:'+path(),payment_submitted:'payment:'+path()};
    const id=UUID.test(extra.event_id||'')?extra.event_id:uid(),dedupe=options.once||defaults[event]||'';
    if(dedupe&&!once('sr_event:'+dedupe,options.persistent))return null;
    const data={schema_version:'STOCKRADAR_FUNNEL_V2',event_name:event,event_id:id,source_path:path(),session_id:sid,tier:tier(extra.tier),ticker:safeTicker(extra.ticker),horizon:HORIZONS.has(extra.horizon)?extra.horizon:'SHORT_TERM',plan_interest:extra.plan_interest==='PREMIUM'?'PREMIUM':plan(),first_touch:safeTouch(touches.first),last_touch:safeTouch(touches.last),action_name:ACTIONS.has(extra.action_name)?extra.action_name:null,model_status:['MODEL_READY','MODEL_NOT_CALLED','MODEL_CREDIT_BLOCKED','MODEL_TIMEOUT','MODEL_ERROR'].includes(extra.model_status)?extra.model_status:null};
    if(event==='login_success'&&!extra.tier)data.tier=null;
    window.dataLayer=window.dataLayer||[];window.dataLayer.push({event,...data});
    // Completion is already stored atomically by signup-link; the browser never inserts it again.
    if(event!=='signup_completed')try{fetch(endpoint(),{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data),credentials: 'omit',cache:'no-store',keepalive: true}).catch(()=>{});}catch(_){}
    try{sendMeta(event,data);}catch(_){meta.status='PIXEL_ERROR';}return id;
  }
  function flowId(){const k='sr_registration_flow:'+plan();let id=read(k);if(!UUID.test(id)){id=uid();save(k,id);}return id;}
  const api={schemaVersion:2,track:emit,modelStatus,successfulResult,meta,
    attribution:()=>({first:safeTouch(touches.first,true),last:safeTouch(touches.last,true)}),
    registrationContext:()=>({flow_id:flowId(),session_id:sid,first_touch:safeTouch(touches.first),last_touch:safeTouch(touches.last)}),
    signupStarted(){emit('signup_started',{}, {once:'signup-start:'+flowId()});},
    signupSubmitted(){emit('signup_submitted');},
    signupVerificationRequested(){emit('signup_verification_requested',{action_name:'signup_verification_requested'},{once:'verification:'+flowId()});},
    signupAccepted(d){api.signupVerificationRequested();if(d?.registration_created!==true||!UUID.test(d?.event_id||''))return false;save('sr_registered_return',d.event_id,true);emit('signup_completed',{event_id:d.event_id,plan_interest:d.plan==='premium'?'PREMIUM':'FREE'},{once:'registered:'+d.event_id,persistent:true,registrationReceipt:true});return true;},
    loginSuccess(t){emit('login_success',{tier:t});},
    returnedToAI(t){const id=read('sr_registered_return',true);if(tier(t)!=='GUEST'&&UUID.test(id))emit('return_to_ai_after_registration',{tier:t},{once:'registered-return:'+id,persistent:true});},
    guestCta(kind,t){if(tier(t)!=='GUEST')return false;if(kind==='first'){if(!once('sr_guest_first_result_v2',true))return false;emit('ai_guest_first_result',{tier:'GUEST'});}else if(!once('sr_guest_cta_v2:'+kind+':'+Math.floor((Date.now()+7*3600000)/86400000),true))return false;emit('guest_free_cta_impression',{tier:'GUEST'});return true;},
    guestCtaClick(){emit('guest_free_cta_click',{tier:'GUEST'});},
    aiSubmitted(e={}){emit('ai_question_started',{...e,action_name:'ai_interaction'});},
    aiFailed(d={}){emit('ai_result_failed',{tier:d.tier,model_status:modelStatus(d)});},
    aiResult(d){
      if(!successfulResult(d)){api.aiFailed(d);return false;}
      emit('ai_result_success',{tier:d.tier,ticker:d.scope==='ticker'?d.ticker:null,model_status:modelStatus(d)});
      const c=d.scope==='ticker'&&d.decision_cards?.length===1?d.decision_cards[0]:null;
      if(c&&window.StockRadarDecisionView?.stillFresh(c.data)&&['RESEARCH','DELAYED'].includes(c.data.status)&&['RESEARCH_READY','VERIFIED_RELEASE'].includes(c.data.source_status)){
        emit('meaningful_report',{ticker:c.ticker,action_name:'meaningful_report'},{once:'meaningful:'+c.ticker});
        if(tier(d.tier)==='FREE'){
          const k='sr_meaningful_activation_day_v1',today=Math.floor((Date.now()+7*3600000)/86400000),saved=read(k,true),first=saved===''?null:Number(saved);
          if(first===null||!Number.isInteger(first)||first>today){save(k,today,true);emit('free_activation',{action_name:'free_activation'},{once:'free_activation'});}
          else if([1,7].includes(today-first))emit('meaningful_return_d'+(today-first),{action_name:'meaningful_return_d'+(today-first)},{once:'return:'+today,persistent:true});
        }
      }return true;
    },
    paymentSubmitted(){emit('payment_submitted',{action_name:'payment_submitted',plan_interest:'PREMIUM'},{once:'payment:'+path()});},
    checkoutCreated(){emit('checkout_started',{action_name:'checkout_created',plan_interest:'PREMIUM'},{once:'checkout:'+path()});},
  };
  window.StockRadarAnalytics=api;
  function init(){
    const p=path(),proposition=document.body?.dataset?.proposition;
    if (['facebook','instagram'].includes(touches.last.source)) document.documentElement?.classList?.add('facebook-entry');
    if(p==='/'||proposition==='organic')emit('landing_view');
    try{sendMeta('page_view',{event_id:uid()});}catch(_){}
    if(p.endsWith('/signup/'))emit('signup_view',{}, {once:'signup-view:'+flowId()});
    if(proposition==='plans')emit('premium_view',{}, {once:'premium-view'});
    if(proposition==='checkout')emit('checkout_view',{}, {once:'checkout-view'});
    if(proposition==='stock-report')emit('stock_report_view',{}, {once:'report:'+p});
    if(proposition==='premium-sample')emit('premium_sample_view',{}, {once:'sample:'+p});
    if(proposition==='performance')emit('performance_proof_view',{}, {once:'performance'});
    if(touches.last.utm_source==='stockradar_email'&&['action_alert','daily_brief'].includes(touches.last.utm_campaign))emit('email_cta_landing',{action_name:'email_cta_landing'},{once:'email-landing:'+p});
    document.querySelectorAll('[data-auth-signup-form]').forEach(f=>{f.addEventListener('focusin',api.signupStarted,{once:true});f.addEventListener('input',api.signupStarted,{once:true});});
    document.querySelectorAll('[data-stock-search-form]').forEach(f=>f.addEventListener('submit',()=>{const t=safeTicker(String(f.elements?.ticker?.value||'').toUpperCase());if(t)emit('ticker_lookup_submit',{ticker:t});}));
    document.querySelectorAll('[data-conversion-action]').forEach(el=>el.addEventListener('click',()=>emit('conversion_click',{action_name:el.getAttribute('data-conversion-action')})));
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
})();
