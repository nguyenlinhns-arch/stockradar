// PROJECT_AUTORESUME_ROUTING_V1
// PROJECT_CHAT_CONTINUITY_V2
// PRIVATE_PROJECT_BRIDGE_V1
(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const STORAGE_KEY = 'stockradar-auth';
  const THREAD_KEY = 'stockradar_ai_thread_id_v1';
  const MAX_GUEST_HISTORY = 6;
  const STOPWORDS = new Set([
    'MUA','BAN','GIU','CHO','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','DANG','THE','NAO','CAN','XEM','MAI','HOM','TIE','THEO','TOP','CAC','CUA','VOI','TAI',
    'VPA','VCP','EPS','ROE','ROA','PBT','FCF','DCF','ATR'
  ]);
  const state = {
    client: null,
    sending: false,
    history: [],
    tier: 'GUEST',
    quota: null,
    threadId: '',
    accountId: '',
    accountEpoch: 0,
    historySequence: 0,
    listSequence: 0,
    hydrating: false,
    ui: {}
  };

  function node(tag, className, text = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function loadThreadId(userId) {
    if (!/^[0-9a-f-]{36}$/i.test(String(userId || ''))) return '';
    try {
      const value = localStorage.getItem(`${THREAD_KEY}:${userId}`) || '';
      return /^[0-9a-f-]{36}$/i.test(value) ? value : '';
    } catch (_) { return ''; }
  }

  function saveThreadId(value) {
    if (!state.accountId) { state.threadId = ''; return; }
    state.threadId = /^[0-9a-f-]{36}$/i.test(String(value || '')) ? String(value) : '';
    try {
      const key = `${THREAD_KEY}:${state.accountId}`;
      if (state.threadId) localStorage.setItem(key, state.threadId);
      else localStorage.removeItem(key);
    } catch (_) {}
  }

  function bindAccount(session) {
    const userId = String(session?.user?.id || '');
    if (userId === state.accountId) return false;
    state.accountId = userId;
    state.accountEpoch += 1;
    state.historySequence += 1;
    state.listSequence += 1;
    state.hydrating = false;
    state.history = [];
    state.quota = null;
    state.threadId = loadThreadId(userId);
    // The old key had no owner. Recover from owned server history, not this pointer.
    try { localStorage.removeItem(THREAD_KEY); } catch (_) {}
    if (state.ui.projectResume) state.ui.projectResume.hidden = true;
    if (state.ui.continuity) state.ui.continuity.textContent = userId ? 'Đang mở hội thoại của tài khoản…' : 'Guest · ngữ cảnh tạm thời';
    state.ui.threadList?.replaceChildren();
    if (state.ui.log) showIntro(state.ui.log,Boolean(userId));
    return true;
  }

  async function sameAccount(session, epoch) {
    try {
      const current = await authSession();
      const userId = String(session?.user?.id || '');
      return state.accountEpoch === epoch && state.accountId === userId && String(current?.user?.id || '') === userId;
    } catch (_) { return false; }
  }

  function renderProjectMeta(data) {
    const bridge = data?.project_bridge;
    if (state.ui.projectResume) {
      state.ui.projectResume.hidden = !state.accountId || bridge?.available !== true;
      state.ui.projectResume.title = bridge?.available ? 'Mở hội thoại có ngữ cảnh đã chuyển từ dự án. Không tự đọc mọi tin nhắn mới trong ChatGPT.' : '';
    }
    if (state.ui.continuity) {
      const linked = bridge?.available === true && bridge.thread_id === state.threadId;
      state.ui.continuity.textContent = linked ? 'Hội thoại dự án đã mở' : state.accountId ? 'Đã lưu ngữ cảnh theo tài khoản' : 'Guest · ngữ cảnh tạm thời';
      state.ui.continuity.title = linked ? `Bản ngữ cảnh: ${String(bridge.version || '')}. Lưu hội thoại không đồng nghĩa mô hình AI đã phản hồi thành công.` : '';
    }
  }

  function validTicker(value) {
    const ticker = String(value || '').trim().toUpperCase();
    return /^[A-Z0-9]{3}$/.test(ticker) && /[A-Z]/.test(ticker);
  }

  function explicitTicker(text) {
    // Canonical lexical extractor, embedded identically in browser/chat/research.
    // This recognizes mentions only: listing, venue and data gates remain server-side.
    const raw = String(text || '').normalize('NFC').slice(0,8000);
    const masked = raw
      .replace(/https?:\/\/\S+|\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi, s => ' '.repeat(s.length))
      .replace(/\btra\s+(?:cứu|cuu)(?=\s|$|[.,:;!?])/giu, s => ' '.repeat(s.length));
    const technical = new Set(['VPA','VCP','EPS','ROE','ROA','PBT','FCF','DCF','ATR','RSI','MAC','PEG','MOS','GDP','CPI','USD','VND','ETF','NAV','IPO','API','OTP','JWT','URL','CEO','CFO','CTO','LLM','MAI']);
    const words = new Set(['CHI','CHO','GHI','TRA','SAU','TIN','RUI','MOC','MOI','TOP','MUA','BAN','GIU','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','THE','NAO','CAN','XEM','HOM','CAC','CUA','VOI','TAI','TOI','NEN','CON','HON','GAN','LAM','VAN','QUA','MOT','HAI','NAM','DAY','DAU','TEN','BAO','LAI','LUC','NOI','NHA','DON','GON','RAT','TAM','TAN','CHU','DAN','DEN','CAP','NET','DAT','TUC','TIE','COI','GI','FOR','AND','THE','NEW','NOW','ALL','GET','SET']);
    const tokens = masked.matchAll(/(?<![\p{L}\p{N}_])([$#]?)([A-Za-z0-9]{3})(?![\p{L}\p{N}_])/gu);
    const tickers = [];
    for (const match of tokens) {
      const ticker = match[2].toUpperCase();
      if (!/[A-Z]/.test(ticker) || technical.has(ticker)) continue;
      const prefix = masked.slice(0,match.index);
      const stockCue = /(?:\bmã|\bma|cổ phiếu|co phieu|\bticker|\bsymbol)\s*[:=]?\s*$/iu.test(prefix);
      const namedCue = match[2] === ticker && (/(?:phân tích|phan tich|so sánh|so sanh|kiểm tra|kiem tra|đánh giá|danh gia)\s*[:=]?\s*$/iu.test(prefix) || (tickers.length > 0 && /(?:\bvà|\bva|\bvới|\bvoi|\bvs|[,/])\s*$/iu.test(prefix)));
      const standalone = masked.trim() === match[0] && match[2] === ticker;
      const command = /^(MUA|BAN|GIU|CHO|GHI|TOP|SAO|KHI|NEU|HAY|TOI|XEM|CAC|CUA|VOI|NAY|ROI|RUI|CHI|THE|FOR|AND|ALL|GET|SET)$/.test(ticker);
      if (command && !match[1]) continue;
      if (words.has(ticker) && !match[1] && !stockCue && !namedCue && !standalone) continue;
      if (!tickers.includes(ticker)) tickers.push(ticker);
      if (tickers.length === 4) break;
    }
    return tickers[0] || "";
  }

  function horizonFromText(text) {
    const value = String(text || '').toLowerCase();
    if (/(tích sản|tich san|2\s*[-–]\s*5\s*năm)/.test(value)) return 'ACCUMULATION';
    if (/(12\s*tháng|12\s*thang|6\s*[-–]\s*18\s*tháng|dài hạn|dai han)/.test(value)) return 'LONG_TERM';
    if (/(3\s*[-–]\s*6\s*tháng|1\s*[-–]\s*6\s*tháng|trung hạn|trung han|6\s*tháng|6\s*thang)/.test(value)) return 'MEDIUM_TERM';
    return '';
  }

  function portfolioIntent(text) {
    return /(danh mục|danh muc|watchlist|mã tôi|ma toi|cổ phiếu của tôi|co phieu cua toi|đang sở hữu|dang so huu|mã đang giữ|ma dang giu|hôm nay.*(làm gì|lam gi|chú ý|chu y)|mã nào|ma nao)/i.test(String(text || ''));
  }

  function guestId() {
    const key = 'stockradar_guest_ai_id_v1';
    let value = '';
    try { value = localStorage.getItem(key) || ''; } catch (_) {}
    if (/^[A-Za-z0-9._:-]{20,128}$/.test(value)) return value;
    const uuid = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
    value = `sr-guest-${uuid}`;
    try { localStorage.setItem(key, value); } catch (_) {}
    return value;
  }

  function normalizeTier(value) {
    const tier = String(value || '').trim().toUpperCase();
    if (tier === 'PAID' || tier === 'TRIAL' || tier === 'PREMIUM') return 'PREMIUM';
    if (tier === 'FREE') return 'FREE';
    return 'GUEST';
  }

  function loadSupabaseLibrary() {
    if (window.supabase?.createClient) return Promise.resolve();
    if (window.__stockradarSupabaseLoading) return window.__stockradarSupabaseLoading;
    window.__stockradarSupabaseLoading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.95.0';
      script.async = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Không tải được lớp tài khoản.'));
      document.head.append(script);
    });
    return window.__stockradarSupabaseLoading;
  }

  async function authClient() {
    if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey) return null;
    await loadSupabaseLibrary();
    if (state.client) return state.client;
    if (window.StockRadarAuthClient) {
      state.client = window.StockRadarAuthClient;
      return state.client;
    }
    state.client = window.supabase.createClient(config.supabaseUrl, config.supabasePublishableKey, {
      auth: {
        persistSession: true,
        autoRefreshToken: true,
        detectSessionInUrl: true,
        storageKey: STORAGE_KEY
      }
    });
    window.StockRadarAuthClient = state.client;
    return state.client;
  }

  async function authSession() {
    const client = await authClient();
    if (!client) return null;
    const { data, error } = await client.auth.getSession();
    if (error) throw error;
    return data?.session || null;
  }

  async function currentAccountTier() {
    const session = await authSession();
    bindAccount(session);
    const epoch = state.accountEpoch;
    const user = session?.user;
    if (!user) return { session: null, tier: 'GUEST' };
    let tier = 'FREE';
    const { data: profile, error } = await state.client.rpc('get_my_stockradar_access');
    if (!(await sameAccount(session,epoch))) throw new Error('ACCOUNT_CHANGED');
    if (error) throw error;
    state.quota = profile?.quota || null;
    const active = String(profile?.account_status || '').toUpperCase() === 'ACTIVE';
    if (active) tier = normalizeTier(profile?.account_tier) === 'PREMIUM' ? 'PREMIUM' : 'FREE';
    return { session, tier };
  }

  function addMessage(log, role, text, meta = '') {
    const wrap = node('div', `sr-center-message sr-center-${role}`);
    wrap.append(node('div', 'sr-center-bubble', text));
    if (meta) wrap.append(node('small', 'sr-center-meta', meta));
    log.append(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function showIntro(log, authenticated = false) {
    if (!authenticated && state.ui.projectResume) state.ui.projectResume.hidden = true;
    log.replaceChildren();
    addMessage(log, 'assistant', authenticated
      ? 'Đây là cuộc trò chuyện phân tích của bạn. Hãy hỏi một mã HOSE, rồi hỏi tiếp tự nhiên như “mua được chưa?”, “3–6 tháng thì sao?”, “rủi ro chính?” hoặc chuyển sang mã khác. StockRadar sẽ giữ ngữ cảnh của cuộc trò chuyện này.'
      : 'Hỏi tôi về một mã HOSE. Guest có 3 câu/ngày; tạo tài khoản Free để có 10 câu/ngày và lưu lại từng cuộc trò chuyện.');
  }

  function addAction(log, text, href, label) {
    const wrap = node('div', 'sr-center-message sr-center-assistant');
    wrap.append(node('div', 'sr-center-bubble', text));
    const link = node('a', 'sr-center-inline-cta', label);
    link.href = href;
    wrap.append(link);
    log.append(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function guestFreeCta(log, kind = 'first') {
    if (state.tier !== 'GUEST' || !window.StockRadarAnalytics?.guestCta(kind, state.tier)) return;
    log.parentElement.querySelectorAll('[data-guest-free-cta]').forEach(el => el.remove());
    const card = node('aside', 'sr-guest-free-cta');
    card.dataset.guestFreeCta = kind;
    card.append(node('strong', '', kind === 'exhausted' ? 'Bạn đã dùng hết 3 lượt Guest hôm nay.' : kind === 'last' ? 'Bạn còn 1 lượt Guest hôm nay.' : 'Muốn hỏi tiếp và lưu cuộc trò chuyện?'));
    card.append(node('p', '', 'Tạo tài khoản Free để dùng StockRadar AI 10 câu/ngày và mở lại lịch sử phân tích trên mọi thiết bị.'));
    card.append(node('small', '', '0đ · Không cần thẻ · Chỉ cần email'));
    const link = node('a', 'button button-primary', 'Đăng ký Free');
    link.href = new URL('signup/?plan=free', document.baseURI).toString();
    link.addEventListener('click', () => window.StockRadarAnalytics?.guestCtaClick());
    card.append(link);
    log.after(card);
  }

  function sourceMeta(data) {
    const bits = [];
    const source = data?.source || {};
    const quota = data?.quota || {};
    if (data?.mode === 'ACTION_READY') bits.push('Tín hiệu đã xác nhận');
    else if (data?.mode === 'RESEARCH_ONLY') bits.push('Dữ liệu nghiên cứu hiện hành');
    else if (data?.mode === 'KNOWLEDGE_ONLY') bits.push('Kiến thức StockRadar');
    else if (data?.mode === 'METHOD_ONLY') bits.push('Giải thích phương pháp');
    if (source.generated_at) {
      try { bits.push(`Dữ liệu ${new Date(source.generated_at).toLocaleString('vi-VN')}`); } catch (_) {}
    }
    if (data?.knowledge_version) bits.push(String(data.knowledge_version));
    if (data?.conversation_persisted) bits.push('Đã lưu hội thoại');
    const tier = normalizeTier(data?.tier);
    if (tier === 'GUEST') bits.push(quota.remaining != null ? `Khách · còn ${quota.remaining}/3 câu hôm nay` : 'Khách · tối đa 3 câu/ngày');
    else if (tier === 'FREE') bits.push(quota.remaining != null ? `Free · còn ${quota.remaining}/10 câu hôm nay` : 'Free · tối đa 10 câu/ngày');
    else if (tier === 'PREMIUM') bits.push('Premium · hỏi không giới hạn');
    return bits.join(' · ');
  }

  function updatePlan(status, data = null, fallbackTier = 'GUEST') {
    if (!status) return;
    const tier = data?.tier ? normalizeTier(data.tier) : normalizeTier(fallbackTier);
    state.tier = tier;
    if (tier !== 'GUEST') document.querySelectorAll('[data-guest-free-cta]').forEach(el => el.remove());
    if (tier === 'GUEST') {
      const remaining = data?.quota?.remaining;
      status.textContent = remaining == null ? 'KHÁCH · 3 CÂU / NGÀY' : `KHÁCH · CÒN ${remaining}/3 CÂU HÔM NAY`;
      status.dataset.tier = 'guest';
    } else if (tier === 'FREE') {
      const remaining = data?.quota?.remaining;
      status.textContent = remaining == null ? 'FREE · 10 CÂU / NGÀY' : `FREE · CÒN ${remaining}/10 CÂU HÔM NAY`;
      status.dataset.tier = 'free';
    } else {
      status.textContent = 'PREMIUM · AI KHÔNG GIỚI HẠN · EMAIL CẢNH BÁO';
      status.dataset.tier = 'paid';
    }
  }

  function freshnessNotice(data) {
    if (data?.mode !== 'METHOD_ONLY') return '';
    return 'Chưa đủ dữ liệu hiện tại để xác nhận hành động mua/bán. StockRadar vẫn có thể giải thích phương pháp và phần dữ liệu đang có.';
  }

  async function callAuthenticated(session, payload) {
    const url = `${String(config.supabaseUrl).replace(/\/$/, '')}/functions/v1/stock-ai-chat`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': config.supabasePublishableKey,
        'Authorization': `Bearer ${session.access_token}`
      },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(40000)
    });
    let data = {};
    try { data = await response.json(); } catch (_) {}
    return { response, data };
  }

  async function hydrateHistory(session, log, requestedThreadId = state.threadId, recoverMissing = false) {
    if (!session?.access_token) return false;
    const epoch = state.accountEpoch, sequence = ++state.historySequence;
    state.hydrating = true;
    try {
      if (!(await sameAccount(session,epoch))) return false;
      let {response,data} = await callAuthenticated(session,{operation: 'history',thread_id:requestedThreadId || null});
      if (sequence !== state.historySequence || !(await sameAccount(session,epoch))) return false;
      // Only implicit startup restoration may recover a removed/legacy thread.
      // An explicit sidebar selection is never silently replaced with another chat.
      if (recoverMissing && requestedThreadId && [400,404].includes(response.status) && ['THREAD_NOT_FOUND','INVALID_THREAD_ID'].includes(data.reason)) {
        saveThreadId('');
        ({response,data} = await callAuthenticated(session,{operation: 'history',thread_id:null}));
      }
      if (!response.ok || sequence !== state.historySequence || !(await sameAccount(session,epoch))) return false;
      const current = await authSession();
      if (!current?.user?.id || current.user.id !== session.user?.id || epoch !== state.accountEpoch || sequence !== state.historySequence) return false;
      if (!/^[0-9a-f-]{36}$/i.test(String(data.thread_id || ''))) return false;
      saveThreadId(data.thread_id);
      renderProjectMeta(data);
      const messages = Array.isArray(data.messages) ? data.messages : [];
      // Signed-in history lives on the server. Never put it in the Guest buffer.
      state.history = [];
      if (!messages.length) { showIntro(log,true); return true; }
      log.replaceChildren();
      messages.forEach(item => addMessage(log,item.role === 'user' ? 'user' : 'assistant',String(item.content || ''),item.scope === 'project_handoff' ? 'Bản tóm tắt chuyển từ dự án · không phải tin nhắn nguyên văn' : ''));
      return true;
    } finally {
      if (sequence === state.historySequence) state.hydrating = false;
    }
  }

  async function resumeProject(session, log) {
    const epoch = state.accountEpoch;
    if (!(await sameAccount(session,epoch))) return false;
    const {response,data} = await callAuthenticated(session,{operation:'resume_project'});
    if (!(await sameAccount(session,epoch))) return false;
    if (!response.ok || !data.thread_id) throw new Error('PROJECT_NOT_LINKED');
    return await hydrateHistory(session,log,data.thread_id);
  }

  async function restoreInitialConversation(session, log) {
    const epoch = state.accountEpoch;
    if (!session?.access_token || !(await sameAccount(session,epoch))) return false;
    const key = `${THREAD_KEY}:project-auto:${state.accountId}`;
    try {
      const {response,data} = await callAuthenticated(session,{operation:'project_bridge'});
      if (!(await sameAccount(session,epoch))) return false;
      const bridge = data?.project_bridge;
      if (response.ok && bridge?.available === true && bridge.auto_resume === true && /^[A-Z0-9_.-]{1,100}$/i.test(String(bridge.version || ''))) {
        let seen = ''; try { seen = localStorage.getItem(key) || ''; } catch (_) {}
        if (seen !== bridge.version && await resumeProject(session,log)) {
          if (!(await sameAccount(session,epoch))) return false;
          try { localStorage.setItem(key,bridge.version); } catch (_) {}
          return true;
        }
      }
    } catch (_) {
      if (!(await sameAccount(session,epoch))) return false;
    }
    return await hydrateHistory(session,log,state.threadId,true);
  }

  function threadLabel(row) {
    const title = String(row?.title || '').trim();
    if (title) return title;
    const ticker = validTicker(row?.last_ticker) ? String(row.last_ticker).toUpperCase() : '';
    return ticker ? `${ticker} · Phân tích` : 'Cuộc trò chuyện';
  }

  function threadMeta(row) {
    const bits = [];
    if (validTicker(row?.last_ticker)) bits.push(String(row.last_ticker).toUpperCase());
    const labels = {
      SHORT_TERM: 'Ngắn hạn',
      MEDIUM_TERM: '3–6 tháng',
      LONG_TERM: '12 tháng',
      ACCUMULATION: 'Tích sản'
    };
    if (labels[row?.last_horizon]) bits.push(labels[row.last_horizon]);
    if (row?.last_message_at) {
      try {
        bits.push(new Date(row.last_message_at).toLocaleDateString('vi-VN', { day: '2-digit', month: '2-digit' }));
      } catch (_) {}
    }
    return bits.join(' · ');
  }

  async function renderThreads(session, list, log) {
    if (!list) return;
    const epoch = state.accountEpoch, sequence = ++state.listSequence;
    list.replaceChildren();
    if (!session?.access_token) {
      const empty = node('div', 'sr-thread-empty');
      empty.append(node('strong', '', 'Lịch sử phân tích'));
      empty.append(node('p', '', 'Đăng ký Free để lưu và mở lại các cuộc trò chuyện.'));
      const link = node('a', 'sr-thread-signup', 'Đăng ký Free');
      link.href = new URL('signup/?plan=free', document.baseURI).toString();
      empty.append(link);
      list.append(empty);
      return;
    }

    const client = await authClient();
    const { data, error } = await client.rpc('get_my_stockradar_ai_threads', { p_limit: 30 });
    if (sequence !== state.listSequence || !(await sameAccount(session,epoch))) return;
    if (error) {
      list.append(node('div', 'sr-thread-empty', 'Chưa tải được lịch sử trò chuyện.'));
      return;
    }
    const rows = Array.isArray(data) ? data : [];
    if (!rows.length) {
      list.append(node('div', 'sr-thread-empty', 'Chưa có cuộc trò chuyện nào.'));
      return;
    }
    rows.forEach(row => {
      const button = node('button', 'sr-thread-item');
      button.type = 'button';
      if (String(row.thread_id) === state.threadId) button.classList.add('is-active');
      const title = node('strong', '', threadLabel(row));
      const meta = node('small', '', threadMeta(row));
      button.append(title, meta);
      button.addEventListener('click', async () => {
        if (state.sending || state.hydrating || String(row.thread_id) === state.threadId) return;
        state.sending = true;
        try {
          if (!(await sameAccount(session,epoch))) return;
          if (await hydrateHistory(session,log,row.thread_id)) {
            list.querySelectorAll('.sr-thread-item').forEach(el => el.classList.remove('is-active'));
            button.classList.add('is-active');
            closeThreadDrawer();
          }
        } finally { state.sending = false; }
      });
      list.append(button);
    });
  }

  function closeThreadDrawer() {
    state.ui.host?.classList.remove('threads-open');
    state.ui.threadToggle?.setAttribute('aria-expanded', 'false');
  }

  function toggleThreadDrawer() {
    const open = !state.ui.host?.classList.contains('threads-open');
    state.ui.host?.classList.toggle('threads-open', open);
    state.ui.threadToggle?.setAttribute('aria-expanded', String(open));
  }

  async function startNewThread(session, log, button) {
    if (!session?.access_token || state.sending || state.hydrating) return;
    const epoch = state.accountEpoch;
    state.sending = true;
    button.disabled = true;
    const original = button.textContent;
    button.textContent = 'Đang tạo…';
    try {
      const { response, data } = await callAuthenticated(session, { operation: 'new_thread' });
      if (!(await sameAccount(session,epoch))) return;
      if (!response.ok || !data.thread_id) throw new Error('NEW_THREAD_FAILED');
      saveThreadId(data.thread_id);
      renderProjectMeta(data);
      state.history = [];
      showIntro(log, true);
      await renderThreads(session, state.ui.threadList, log);
      closeThreadDrawer();
    } catch (_) {
      if (epoch === state.accountEpoch) addMessage(log, 'assistant', 'Chưa tạo được cuộc trò chuyện mới. Vui lòng thử lại.');
    } finally {
      state.sending = false;
      button.disabled = false;
      button.textContent = original;
    }
  }

  async function ask(message, log, input, send, status) {
    if (state.sending || state.hydrating) return;
    const epoch = state.accountEpoch;
    state.sending = true;
    input.disabled = true;
    send.disabled = true;
    const oldLabel = send.textContent;
    send.textContent = 'Đang phân tích…';

    try {
      const account = await currentAccountTier();
      if (epoch !== state.accountEpoch) return;
      const session = account.session;
      const ticker = explicitTicker(message);
      const horizon = horizonFromText(message);
      const authenticated = Boolean(session?.access_token);
      updatePlan(status, state.quota ? { quota: state.quota, tier: account.tier } : null, account.tier);

      if (!authenticated && !ticker) {
        addAction(
          log,
          portfolioIntent(message)
            ? 'Danh mục và lịch sử hội thoại theo tài khoản cần đăng nhập. Bạn vẫn có thể hỏi trực tiếp một mã HOSE ở chế độ Guest.'
            : 'Guest dùng để hỏi nhanh một mã HOSE. Tạo tài khoản Free để hỏi nối tiếp, hỏi phương pháp và lưu lịch sử phân tích.',
          'signup/?plan=free',
          'Đăng ký Free'
        );
        return;
      }

      let response, data;
      window.StockRadarAnalytics?.aiSubmitted({ tier: account.tier, ticker, horizon: horizon || 'SHORT_TERM' });

      if (authenticated) {
        ({ response, data } = await callAuthenticated(session, {
          operation: 'ask',
          thread_id: state.threadId || null,
          scope: ticker ? 'auto' : (portfolioIntent(message) ? 'portfolio' : 'auto'),
          ticker: ticker || '',
          horizon: horizon || '',
          message: String(message).slice(0, 700)
        }));
      } else {
        const url = `${String(config.supabaseUrl).replace(/\/$/, '')}/functions/v1/stock-ai-guest`;
        response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'apikey': config.supabasePublishableKey },
          body: JSON.stringify({
            ticker,
            horizon: horizon || 'SHORT_TERM',
            message: String(message).slice(0, 700),
            history: state.history.slice(-MAX_GUEST_HISTORY),
            guest_id: guestId()
          }),
          signal: AbortSignal.timeout(35000)
        });
        data = {};
        try { data = await response.json(); } catch (_) {}
      }

      if (!(await sameAccount(session,epoch))) return;
      if (response.status === 401 && authenticated) {
        window.StockRadarAnalytics?.aiFailed({ tier: account.tier });
        addAction(log, 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại để tiếp tục cuộc trò chuyện.', 'dang-nhap/', 'Đăng nhập lại');
        return;
      }

      if (data?.thread_id) saveThreadId(data.thread_id);
      window.StockRadarAnalytics?.returnedToAI(account.tier);
      const success = response.ok && window.StockRadarAnalytics?.aiResult(data) === true;
      if (!response.ok) window.StockRadarAnalytics?.aiFailed({ tier: account.tier, ...data });

      const answer = data.answer || (response.ok ? 'StockRadar AI chưa có nội dung để trả lời.' : 'StockRadar AI tạm thời chưa thể phản hồi.');
      const modelState = window.StockRadarAnalytics?.modelStatus(data);
      if (response.ok && modelState && modelState !== 'MODEL_READY' && data.model_notice) addMessage(log, 'assistant', data.model_notice);
      if (!window.StockRadarDecisionView?.render(log, data, sourceMeta(data))) addMessage(log, 'assistant', answer, sourceMeta(data));

      const warning = freshnessNotice(data);
      if (warning && !data.decision_cards?.length) addMessage(log, 'assistant', warning);
      updatePlan(status, data, account.tier);

      if (response.status === 429 && data.reason !== 'TECHNICAL_RATE_LIMIT') {
        const responseTier = normalizeTier(data?.tier || account.tier);
        if (responseTier === 'GUEST') guestFreeCta(log, 'exhausted');
        if (responseTier === 'FREE') addAction(log, 'Bạn đã sử dụng hết lượt AI miễn phí. Nâng cấp StockRadar Pro để sử dụng không giới hạn.', 'thanh-toan/?plan=premium', 'Nâng Premium');
        return;
      }

      if (response.ok && !authenticated) {
        state.history.push({ role: 'user', content: String(message).slice(0, 600) });
        state.history.push({ role: 'assistant', content: String(answer).slice(0, 600) });
        state.history = state.history.slice(-MAX_GUEST_HISTORY);
      }
      if (response.ok && authenticated) await renderThreads(session, state.ui.threadList, log);

      if (success && !authenticated && state.tier === 'GUEST') {
        guestFreeCta(log, 'first');
        if (Number(data.quota?.remaining) === 1 && !log.parentElement.querySelector('[data-guest-free-cta]')) guestFreeCta(log, 'last');
        if (Number(data.quota?.remaining) === 0) guestFreeCta(log, 'exhausted');
      }
    } catch (error) {
      if (epoch !== state.accountEpoch) return;
      window.StockRadarAnalytics?.aiFailed({
        tier: state.tier,
        model_status: error?.name === 'TimeoutError' ? 'MODEL_TIMEOUT' : 'MODEL_ERROR'
      });
      addMessage(log, 'assistant', 'Không thể kết nối StockRadar AI lúc này. Vui lòng thử lại.');
    } finally {
      state.sending = false;
      input.disabled = false;
      send.disabled = false;
      send.textContent = oldLabel;
      if (!matchMedia('(pointer: coarse)').matches) input.focus({ preventScroll: true });
    }
  }

  function ensureConversationStyles() {
    if (document.querySelector('link[data-stockradar-conversation-css]')) return;
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.dataset.stockradarConversationCss = '';
    link.href = new URL('assets/ai-conversation-v2.css?v=20260906-chat2', document.baseURI).toString();
    document.head.append(link);
  }

  async function mount() {
    ensureConversationStyles();
    const host = document.querySelector('[data-stockradar-ai-center]');
    if (!host || host.dataset.mounted === 'true') return;
    host.dataset.mounted = 'true';
    host.classList.add('sr-conversation-shell');

    const sidebar = node('aside', 'sr-thread-sidebar');
    const sidebarHead = node('div', 'sr-thread-sidebar-head');
    const sidebarTitle = node('div', 'sr-thread-sidebar-title');
    sidebarTitle.append(node('strong', '', 'Cuộc trò chuyện'), node('span', '', 'Lịch sử phân tích theo tài khoản'));
    const fullPage = node('a', 'sr-thread-fullpage', 'Mở AI toàn màn hình →');
    fullPage.href = new URL('ai/', document.baseURI).toString();
    const sideNewChat = node('button', 'sr-thread-new-chat', '+ Cuộc trò chuyện mới');
    sideNewChat.type = 'button';
    sideNewChat.hidden = true;
    sidebarHead.append(sidebarTitle, fullPage, sideNewChat);
    const threadList = node('div', 'sr-thread-list');
    sidebar.append(sidebarHead, threadList);

    const main = node('div', 'sr-conversation-main');
    const top = node('div', 'sr-center-top');
    const topLeft = node('div', 'sr-center-top-left');
    const threadToggle = node('button', 'sr-thread-toggle', 'Lịch sử');
    threadToggle.type = 'button';
    threadToggle.setAttribute('aria-expanded', 'false');
    const status = node('span', 'sr-center-plan', 'ĐANG KIỂM TRA TÀI KHOẢN…');
    const continuity = node('span', 'sr-center-continuity', 'Hội thoại liên tục');
    const projectResume = node('button', 'sr-center-new-chat', 'Tiếp tục từ dự án');
    projectResume.type = 'button';
    projectResume.hidden = true;
    topLeft.append(threadToggle, status, continuity, projectResume);

    const topRight = node('div', 'sr-center-top-actions');
    const privacy = node('span', 'sr-center-privacy', 'Không nhập mật khẩu · OTP · mã giao dịch');
    const newChat = node('button', 'sr-center-new-chat', 'Cuộc trò chuyện mới');
    newChat.type = 'button';
    newChat.hidden = true;
    topRight.append(privacy, newChat);
    top.append(topLeft, topRight);

    const log = node('div', 'sr-center-log');
    log.setAttribute('aria-live', 'polite');
    showIntro(log, false);

    const chips = node('div', 'sr-center-chips');
    ['Phân tích FPT', 'Mua được chưa?', '3–6 tháng thì sao?', 'SEPA là gì?'].forEach(label => {
      const button = node('button', '', label);
      button.type = 'button';
      chips.append(button);
    });

    const form = node('form', 'sr-center-form');
    const input = document.createElement('textarea');
    input.rows = 2;
    input.maxLength = 700;
    input.placeholder = 'Hỏi tự nhiên, ví dụ: “Phân tích FPT” rồi “mua được chưa?”';
    input.setAttribute('aria-label', 'Hỏi StockRadar AI');
    const send = node('button', 'sr-center-send', 'Gửi');
    send.type = 'submit';
    form.append(input, send);

    const foot = node('div', 'sr-center-foot');
    foot.innerHTML = '<span>Guest · 3 câu/ngày</span><span>Free · 10 câu/ngày + lưu lịch sử</span><span>Premium · AI không giới hạn + email cảnh báo</span>';

    main.append(top, log, chips, form, foot);
    host.replaceChildren(sidebar, main);

    state.ui = { host, threadList, threadToggle, log, sideNewChat, newChat, projectResume, continuity };

    chips.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
      input.value = button.textContent || '';
      input.focus();
    }));

    threadToggle.addEventListener('click', toggleThreadDrawer);
    projectResume.addEventListener('click', async () => {
      if (state.sending) return;
      state.sending = true;
      projectResume.disabled = true;
      try {
        const current = await currentAccountTier();
        if (!current.session?.access_token) return;
        if (await resumeProject(current.session,log)) {
          await renderThreads(current.session,threadList,log);
          closeThreadDrawer();
        }
      } catch (_) {
        addMessage(log,'assistant','Chưa mở được cuộc trò chuyện liên thông của tài khoản này.');
      } finally {
        state.sending = false;
        projectResume.disabled = false;
      }
    });

    form.addEventListener('submit', event => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message || state.sending || state.hydrating) return;
      addMessage(log, 'user', message);
      input.value = '';
      ask(message, log, input, send, status);
    });

    input.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey && !event.isComposing && !matchMedia('(pointer: coarse)').matches) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    const newThreadHandler = async button => {
      try {
        const current = await currentAccountTier();
        if (current.session?.access_token) await startNewThread(current.session, log, button);
      } catch (_) {
        addMessage(log, 'assistant', 'Chưa tạo được cuộc trò chuyện mới. Vui lòng thử lại.');
      }
    };
    newChat.addEventListener('click', () => newThreadHandler(newChat));
    sideNewChat.addEventListener('click', () => newThreadHandler(sideNewChat));

    try {
      const account = await currentAccountTier();
      updatePlan(status, { quota: state.quota }, account.tier);
      const authenticated = Boolean(account.session?.access_token);
      newChat.hidden = !authenticated;
      sideNewChat.hidden = !authenticated;
      continuity.textContent = authenticated ? 'Đã lưu ngữ cảnh theo tài khoản' : 'Guest · ngữ cảnh tạm thời';
      if (authenticated) await restoreInitialConversation(account.session, log);
      await renderThreads(account.session, threadList, log);

      const client = await authClient();
      client?.auth?.onAuthStateChange?.((_event,session) => {
        if (!bindAccount(session)) return;
        setTimeout(async () => {
          try {
            const next = await currentAccountTier();
            updatePlan(status, { quota: state.quota }, next.tier);
            const nextAuth = Boolean(next.session?.access_token);
            newChat.hidden = !nextAuth;
            sideNewChat.hidden = !nextAuth;
            continuity.textContent = nextAuth ? 'Đã lưu ngữ cảnh theo tài khoản' : 'Guest · ngữ cảnh tạm thời';
            if (nextAuth) await restoreInitialConversation(next.session, log);
            else showIntro(log, false);
            await renderThreads(next.session, threadList, log);
          } catch (_) {
            status.textContent = 'Đang chờ xác nhận phiên tài khoản. Vui lòng thử lại.';
          }
        }, 0);
      });
    } catch (_) {
      status.textContent = 'Đang chờ xác nhận phiên tài khoản. Vui lòng thử lại.';
      await renderThreads(null, threadList, log);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();