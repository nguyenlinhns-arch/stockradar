(() => {
  'use strict';

  const CONSENT_VERSION = '2026-09-03';

  function formMetadata() {
    const form = document.querySelector('[data-auth-signup-form]');
    if (!form) return null;

    const dailyBrief = Boolean(form.elements.email_daily_brief?.checked);
    const eventAlerts = Boolean(form.elements.email_event_alerts?.checked);
    const termsAccepted = Boolean(form.elements.terms?.checked);

    return {
      terms_accepted: termsAccepted,
      terms_version: CONSENT_VERSION,
      privacy_accepted: termsAccepted,
      privacy_version: CONSENT_VERSION,
      product_email_consent: dailyBrief || eventAlerts,
      product_email_consent_version: CONSENT_VERSION,
      product_email_daily_brief: dailyBrief,
      product_email_event_alerts: eventAlerts,
    };
  }

  function patchSupabaseClientFactory() {
    const sdk = window.supabase;
    if (!sdk || typeof sdk.createClient !== 'function' || sdk.createClient.__stockradarSignupPatched) return;

    const originalCreateClient = sdk.createClient.bind(sdk);
    const patchedCreateClient = (...args) => {
      const client = originalCreateClient(...args);
      const originalSignUp = client?.auth?.signUp?.bind(client.auth);
      if (!originalSignUp || client.auth.signUp.__stockradarSignupPatched) return client;

      const patchedSignUp = async credentials => {
        const metadata = formMetadata();
        if (!metadata) return originalSignUp(credentials);
        const originalOptions = credentials?.options || {};
        return originalSignUp({
          ...credentials,
          options: {
            ...originalOptions,
            data: {
              ...(originalOptions.data || {}),
              ...metadata,
            },
          },
        });
      };
      patchedSignUp.__stockradarSignupPatched = true;
      client.auth.signUp = patchedSignUp;
      return client;
    };

    patchedCreateClient.__stockradarSignupPatched = true;
    sdk.createClient = patchedCreateClient;
  }

  document.addEventListener('DOMContentLoaded', patchSupabaseClientFactory, { once: true });
})();
