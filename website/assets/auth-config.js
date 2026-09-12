window.STOCKRADAR_AUTH_CONFIG = Object.freeze({
  provider: 'supabase',
  supabaseUrl: 'https://xamviatbxufjlpiwhebb.supabase.co',
  supabasePublishableKey: 'sb_publishable_Ne0TfBw0Iu732yrhqRcdIA_hPGxYDAK',
  configured: true,
  emailDeliveryReady: false
});
// Public measurement configuration. No access token belongs in this file.
window.STOCKRADAR_META_CONFIG = Object.freeze({enabled: false, pixelId: ''});

// Load the owner-authenticated Project queue adapter before ai-center.js executes.
(() => {
  const src = new URL('assets/project-live-bridge-v1.js?v=20260912-live1', document.baseURI).toString();
  if (document.readyState === 'loading') {
    document.write(`<script src="${src}"><\/script>`);
    return;
  }
  const script = document.createElement('script');
  script.src = src;
  script.async = false;
  document.head.append(script);
})();
