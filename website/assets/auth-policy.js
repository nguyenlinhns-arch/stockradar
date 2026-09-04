(() => {
  'use strict';

  const TERMS_VERSION = '2026-09-03';
  const PRIVACY_VERSION = '2026-09-04';
  if (!window.supabase || typeof window.supabase.createClient !== 'function') return;

  const originalCreateClient = window.supabase.createClient.bind(window.supabase);
  window.supabase.createClient = (...args) => {
    const client = originalCreateClient(...args);
    if (!window.StockRadarAuthClient) window.StockRadarAuthClient = client;

    if (client?.auth?.signUp && !client.auth.signUp.__stockradarWrapped) {
      const originalSignUp = client.auth.signUp.bind(client.auth);
      const wrappedSignUp = credentials => {
        const form = document.querySelector('[data-auth-signup-form]');
        const accepted = Boolean(form?.elements?.terms?.checked);
        const options = credentials?.options || {};
        const data = {
          ...(options.data || {}),
          signup_source: 'stockradar_web',
          terms_accepted: accepted,
          privacy_accepted: accepted,
          terms_version: TERMS_VERSION,
          privacy_version: PRIVACY_VERSION,
        };
        return originalSignUp({
          ...credentials,
          options: { ...options, data },
        });
      };
      wrappedSignUp.__stockradarWrapped = true;
      client.auth.signUp = wrappedSignUp;
    }
    return client;
  };
})();