(()=>{
'use strict';
const siteUrl=p=>new URL(String(p||'').replace(/^\/+/,''),document.baseURI).toString();
function normalizeCommercialNav(){
  document.querySelectorAll('[data-nav-menu]').forEach(nav=>{
    nav.querySelectorAll('a').forEach(link=>{
      const href=String(link.getAttribute('href')||'').replace(/^\.\//,'');
      if(/^hom-nay\//.test(href)) link.remove();
    });
    if(![...nav.querySelectorAll('a')].some(link=>/dang-ky\//.test(String(link.getAttribute('href')||'')))){
      const link=document.createElement('a');
      link.href=siteUrl('dang-ky/');
      link.textContent='Gói';
      link.setAttribute('data-commercial-plans-link','1');
      nav.append(link);
    }
  });
}
function normalizeCommercialChrome(){
  document.querySelectorAll('.header-register-cta').forEach(l=>{l.href=siteUrl('dang-ky/?plan=free');l.textContent='Bắt đầu miễn phí';l.setAttribute('aria-label','Bắt đầu với StockRadar Free')});
  document.querySelectorAll('.conversion-mobile-cta,.mobile-newsletter-bar').forEach(n=>n.remove());
  normalizeCommercialNav();
}
function mount(){normalizeCommercialChrome();setTimeout(normalizeCommercialChrome,50);setTimeout(normalizeCommercialChrome,500)}
document.readyState==='loading'?document.addEventListener('DOMContentLoaded',mount,{once:true}):mount();
})();
