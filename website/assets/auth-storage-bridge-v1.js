(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const canonicalKey = 'stockradar-auth';
  let local = null;
  try { local = window.localStorage; } catch (_) { local = null; }

  function defaultSupabaseStorageKey() {
    try {
      const host = new URL(String(config.supabaseUrl || '')).hostname;
      const projectRef = host.split('.')[0] || '';
      return projectRef ? `sb-${projectRef}-auth-token` : '';
    } catch (_) {
      return '';
    }
  }

  const supabaseDefaultKey = defaultSupabaseStorageKey();
  if (!local || !supabaseDefaultKey || supabaseDefaultKey === canonicalKey || typeof Storage === 'undefined') return;

  const proto = Storage.prototype;
  if (proto.__stockradarAuthStorageBridgeV1) return;

  const originalGetItem = proto.getItem;
  const originalSetItem = proto.setItem;
  const originalRemoveItem = proto.removeItem;

  function mappedKey(storage, key) {
    if (storage === local && String(key) === supabaseDefaultKey) return canonicalKey;
    return key;
  }

  Object.defineProperty(proto, 'getItem', {
    configurable: true,
    writable: true,
    value(key) { return originalGetItem.call(this, mappedKey(this, key)); },
  });
  Object.defineProperty(proto, 'setItem', {
    configurable: true,
    writable: true,
    value(key, value) { return originalSetItem.call(this, mappedKey(this, key), value); },
  });
  Object.defineProperty(proto, 'removeItem', {
    configurable: true,
    writable: true,
    value(key) { return originalRemoveItem.call(this, mappedKey(this, key)); },
  });
  Object.defineProperty(proto, '__stockradarAuthStorageBridgeV1', {
    configurable: true,
    value: true,
  });

  window.STOCKRADAR_AUTH_STORAGE = Object.freeze({ canonicalKey, supabaseDefaultKey });
})();
