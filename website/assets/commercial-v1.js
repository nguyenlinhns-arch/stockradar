(()=>{
'use strict';
const siteUrl=p=>new URL(String(p||'').replace(/^\/+/,''),document.baseURI).toString();
function normalizeCommercialChrome(){
  document.querySelectorAll('.header-register-cta').forEach(l=>{l.href=siteUrl('dang-ky/?plan=free');l.textContent='Bắt đầu miễn phí';l.setAttribute('aria-label','Bắt đầu với StockRadar Free')});
  document.querySelectorAll('.conversion-mobile-cta,.mobile-newsletter-bar').forEach(n=>n.remove())
}
function mount(){normalizeCommercialChrome();setTimeout(normalizeCommercialChrome,50);setTimeout(normalizeCommercialChrome,500)}
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',mount,{once:true}):mount();
})();
