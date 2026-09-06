(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const STORAGE_KEY = 'stockradar-auth';
  const THREAD_KEY = 'stockradar_ai_thread_id_v1';
  const MAX_GUEST_HISTORY = 6;
  const STOPWORDS = new Set(['MUA','BAN','GIU','CHO','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','DANG','THE','NAO','CAN','XEM','MAI','HOM','TIE','THEO','TOP','CAC','CUA','VOI','TAI','VPA','VCP','EPS','ROE','ROA','PBT','FCF','DCF','ATR']);
  const state = { client: null, sending: false, history: [], tier: 'GUEST', quota: null, threadId: loadThreadId() };

  function node(tag, className, text = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function loadThreadId() {
    try {
      const value = localStorage.getItem(THREAD_KEY) || '';
      return /^[0-9a-f-]{36}$/i.test(value) ? value : '';
    } catch (_) { return ''; }
  }

  function saveThreadId(value) {
    state.threadId = /^[0-9a-f-]{36}$/i.test(String(value || '')) ? String(value) : '';
    try {
      if (state.threadId) localStorage.setItem(THREAD_KEY, state.threadId);
      else localStorage.removeItem(THREAD_KEY);
    } catch (_) {}
  }

  function validTicker(value) {
    const ticker = String(value || '').trim().toUpperCase();
    return /^[A-Z0-9]{3}$/.test(ticker) && /[A-Z]/.test(ticker);
  }

  function explicitTicker(text) {
    const tokens = String(text || '').toUpperCase().match(/(?<![\p{L}\p{N}])[A-Z0-9]{3}(?![\p{L}\p{N}])/gu) || [];
    return tokens.find(token => validTicker(token) && !STOPWORDS.has(token)) || '';
  }

  function horizonFromText(text) {
    const value = String(text || '').toLowerCase();
    if (/(tích sản|tich san|2\s*[-–]\s*5\s*năm)/.test(value)) return 'ACCUMULATION';
    if (/(12\s*tháng|12\s*thang|6\s*[-–]\s*18\s*tháng|dài hạn|dai han)/.test(value)) return 'LONG_TERM';
    if (/(3\s*[-–]\s*6\s*tháng|1\s*[-–]\s*6\s*tháng|trung hạn|trung han|6\s*tháng|6\s*thang)/.test(value)) return 'MEDIUM_TERM';
    return 'SHORT_TERM';
  }

  function portfolioIntent(text) {
    return /(danh mục|danh muc|watchlist|mã tôi|ma toi|cổ phiếu của tôi|co phieu cua toi|đang sở hữu|dang so huu|mã đang giữ|ma dang giu|hôm nay.*(làm gì|lam gi|chú ý|chu y))/i.test(String(text || ''));
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
      auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true, storageKey: STORAGE_KEY }
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
    const user = session?.user;
    if (!user) return { session: null, tier: 'GUEST' };
    let tier = 'FREE';
    const { data: profile, error } = await state.client.rpc('get_my_stockradar_access');
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
    log.replaceChildren();
    addMessage(log, 'assistant', authenticated
      ? 'Bạn có thể trò chuyện liên tục với StockRadar AI như trong một phiên phân tích. Hỏi một mã HOSE, rồi hỏi tiếp “mua được chưa?”, “3–6 tháng thì sao?” hoặc “rủi ro chính?” mà không cần gõ lại mã. Lịch sử được lưu theo tài khoản của bạn.'
      : 'Hỏi tôi về một mã HOSE. Guest có 3 câu/ngày; tạo tài khoản Free để có 10 câu/ngày và giữ ngữ cảnh phân tích trên tài khoản.');
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
    const card = node('aside', 'sr-guest-free-cta'); card.dataset.guestFreeCta = kind;
    card.append(node('strong', '', kind === 'exhausted' ? 'Bạn đã dùng hết 3 lượt Guest hôm nay.' : kind === 'last' ? 'Bạn còn 1 lượt Guest hôm nay.' : 'Muốn hỏi tiếp và giữ ngữ cảnh?'));
    card.append(node('p', '', 'Tạo tài khoản Free để dùng StockRadar AI 10 câu/ngày và tiếp tục cuộc phân tích trên tài khoản.'));
    card.append(node('small', '', '0đ · Không cần thẻ · Chỉ cần email'));
    const link = node('a', 'button button-primary', 'Đăng ký Free');
    link.href = new URL('signup/?plan=free', document.baseURI).toString();
    link.addEventListener('click', () => window.StockRadarAnalytics?.guestCtaClick());
    card.append(link); log.after(card);
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
    return 'Chưa đủ dữ liệu hiện tại để xác nhận hành động mua/bán. StockRadar vẫn có thể giải thích phần phương pháp và dữ liệu đang có.';
  }

  async function callAuthenticated(session, payload) {
    const url = `${String(config.supabaseUrl).replace(/\/$/, '')}/functions/v1/stock-ai-chat`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'apikey': config.supabasePublishableKey, 'Authorization': `Bearer ${session.access_token}` },
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(40000)
    });
    let data = {};
    try { data = await response.json(); } catch (_) {}
    return { response, data };
  }

  async function hydrateHistory(session, log) {
    if (!session?.access_token) return false;
    const { response, data } = await callAuthenticated(session, { operation: 'history', thread_id: state.threadId || null });
    if (!response.ok) return false;
    if (data.thread_id) saveThreadId(data.thread_id);
    const messages = Array.isArray(data.messages) ? data.messages : [];
    if (!messages.length) {
      showIntro(log, true);
      return true;
    }
    log.replaceChildren();
    messages.forEach(item => addMessage(log, item.role === 'user' ? 'user' : 'assistant', String(item.content || '')));
    state.history = messages.slice(-MAX_GUEST_HISTORY).map(item => ({ role: item.role, content: String(item.content || '').slice(0, 600) }));
    return true;
  }

  async function startNewThread(session, log, button) {
    if (!session?.access_token || state.sending) return;
    button.disabled = true;
    const original = button.textContent;
    button.textContent = 'Đang tạo…';
    try {
      const { response, data } = await callAuthenticated(session, { operation: 'new_thread' });
      if (!response.ok || !data.thread_id) throw new Error('NEW_THREAD_FAILED');
      saveThreadId(data.thread_id);
      state.history = [];
      showIntro(log, true);
    } catch (_) {
      addMessage(log, 'assistant', 'Chưa tạo được cuộc trò chuyện mới. Vui lòng thử lại.');
    } finally {
      button.disabled = false;
      button.textContent = original;
    }
  }

  async function ask(message, log, input, send, status) {
    if (state.sending) return;
    state.sending = true;
    input.disabled = true;
    send.disabled = true;
    const oldLabel = send.textContent;
    send.textContent = 'Đang phân tích…';

    try {
      const account = await currentAccountTier();
      const session = account.session;
      const ticker = explicitTicker(message);
      const horizon = horizonFromText(message);
      const authenticated = Boolean(session?.access_token);
      updatePlan(status, state.quota ? {quota: state.quota, tier: account.tier} : null, account.tier);

      if (!authenticated && !ticker && portfolioIntent(message)) {
        addAction(log, 'Danh mục và lịch sử hội thoại theo tài khoản cần đăng nhập. Bạn vẫn có thể hỏi trực tiếp một mã HOSE ở chế độ Guest.', 'signup/?plan=free', 'Đăng ký Free');
        return;
      }

      let response, data;
      if (authenticated) {
        ({ response, data } = await callAuthenticated(session, {
          operation: 'ask',
          thread_id: state.threadId || null,
          scope: ticker ? 'auto' : (portfolioIntent(message) ? 'portfolio' : 'auto'),
          ticker: ticker || '',
          horizon,
          message: String(message).slice(0, 700)
        }));
      } else {
        const url = `${String(config.supabaseUrl).replace(/\/$/, '')}/functions/v1/stock-ai-guest`;
        response = await fetch(url, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'apikey': config.supabasePublishableKey },
          body: JSON.stringify({ ticker, horizon, message: String(message).slice(0, 700), history: state.history.slice(-MAX_GUEST_HISTORY), guest_id: guestId() }),
          signal: AbortSignal.timeout(35000)
        });
        data = {};
        try { data = await response.json(); } catch (_) {}
      }

      if (response.status === 401 && authenticated) {
        window.StockRadarAnalytics?.aiFailed({tier: account.tier});
        addAction(log, 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại để tiếp tục cuộc trò chuyện.', 'dang-nhap/', 'Đăng nhập lại');
        return;
      }

      if (data?.thread_id) saveThreadId(data.thread_id);
      window.StockRadarAnalytics?.aiSubmitted({tier: account.tier, ticker, horizon});
      window.StockRadarAnalytics?.returnedToAI(account.tier);
      const success = response.ok && window.StockRadarAnalytics?.aiResult(data) === true;
      if (!response.ok) window.StockRadarAnalytics?.aiFailed({tier: account.tier, ...data});
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

      if (response.ok) {
        state.history.push({ role: 'user', content: String(message).slice(0, 600) });
        state.history.push({ role: 'assistant', content: String(answer).slice(0, 600) });
        state.history = state.history.slice(-MAX_GUEST_HISTORY);
      }
      if (success && !authenticated && state.tier === 'GUEST') {
        guestFreeCta(log, 'first');
        if (Number(data.quota?.remaining) === 1 && !log.parentElement.querySelector('[data-guest-free-cta]')) guestFreeCta(log, 'last');
        if (Number(data.quota?.remaining) === 0) guestFreeCta(log, 'exhausted');
      }
    } catch (error) {
      window.StockRadarAnalytics?.aiFailed({tier: state.tier, model_status: error?.name === 'TimeoutError' ? 'MODEL_TIMEOUT' : 'MODEL_ERROR'});
      addMessage(log, 'assistant', 'Không thể kết nối StockRadar AI lúc này. Vui lòng thử lại.');
    } finally {
      state.sending = false;
      input.disabled = false;
      send.disabled = false;
      send.textContent = oldLabel;
      if (!matchMedia('(pointer: coarse)').matches) input.focus({preventScroll: true});
    }
  }

  async function mount() {
    const host = document.querySelector('[data-stockradar-ai-center]');
    if (!host || host.dataset.mounted === 'true') return;
    host.dataset.mounted = 'true';

    const top = node('div', 'sr-center-top');
    const topLeft = node('div', 'sr-center-top-left');
    const status = node('span', 'sr-center-plan', 'ĐANG KIỂM TRA TÀI KHOẢN…');
    const continuity = node('span', 'sr-center-continuity', 'Hội thoại liên tục');
    topLeft.append(status, continuity);
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
    input.placeholder = 'VD: Phân tích FPT; sau đó hỏi tiếp “mua được chưa?”';
    input.setAttribute('aria-label', 'Hỏi StockRadar AI');
    const send = node('button', 'sr-center-send', 'Gửi');
    send.type = 'submit';
    form.append(input, send);

    const foot = node('div', 'sr-center-foot');
    foot.innerHTML = '<span>Guest · 3 câu/ngày</span><span>Free · 10 câu/ngày + lưu ngữ cảnh</span><span>Premium · AI không giới hạn + email cảnh báo</span>';
    host.replaceChildren(top, log, chips, form, foot);

    chips.querySelectorAll('button').forEach(button => button.addEventListener('click', () => {
      input.value = button.textContent || '';
      input.focus();
    }));

    form.addEventListener('submit', event => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message) return;
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

    try {
      const account = await currentAccountTier();
      updatePlan(status, {quota:state.quota}, account.tier);
      const authenticated = Boolean(account.session?.access_token);
      newChat.hidden = !authenticated;
      continuity.textContent = authenticated ? 'Đã lưu ngữ cảnh theo tài khoản' : 'Guest · ngữ cảnh tạm thời';
      if (authenticated) await hydrateHistory(account.session, log);
      newChat.addEventListener('click', () => startNewThread(account.session, log, newChat));

      const client = await authClient();
      client?.auth?.onAuthStateChange?.(() => {
        setTimeout(async () => {
          try {
            const next = await currentAccountTier();
            updatePlan(status, {quota:state.quota}, next.tier);
            const nextAuth = Boolean(next.session?.access_token);
            newChat.hidden = !nextAuth;
            continuity.textContent = nextAuth ? 'Đã lưu ngữ cảnh theo tài khoản' : 'Guest · ngữ cảnh tạm thời';
            if (nextAuth) await hydrateHistory(next.session, log);
          } catch (_) {
            status.textContent = 'Đang chờ xác nhận phiên tài khoản. Vui lòng thử lại.';
          }
        }, 0);
      });
    } catch (_) {
      status.textContent = 'Đang chờ xác nhận phiên tài khoản. Vui lòng thử lại.';
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();