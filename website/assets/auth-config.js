window.STOCKRADAR_AUTH_CONFIG = Object.freeze({
  provider: 'supabase',
  supabaseUrl: 'https://xamviatbxufjlpiwhebb.supabase.co',
  supabasePublishableKey: 'sb_publishable_Ne0TfBw0Iu732yrhqRcdIA_hPGxYDAK',
  configured: true,
  emailDeliveryReady: false
});
// Public measurement configuration. No access token belongs in this file.
window.STOCKRADAR_META_CONFIG = Object.freeze({enabled: false, pixelId: ''});

// The private Project/chat bridge is now route-scoped. The production homepage is
// email/report-first and must not load chat infrastructure in the background.
(() => {
  const path = String(window.location.pathname || '').toLowerCase();
  if (!/(^|\/)(ai|bao-cao-chatgpt)(\/|$)/.test(path)) return;

  const src = new URL('assets/project-live-bridge-v1.js?v=20260912-live1', document.baseURI).toString();
  if (document.readyState === 'loading') {
    document.write('<script src="' + src + '"><\/script>');
    return;
  }
  const script = document.createElement('script');
  script.src = src;
  script.async = false;
  document.head.append(script);
})();
