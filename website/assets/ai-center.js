(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const MAX_HISTORY = 6;
  const STOPWORDS = new Set(['MUA','BAN','GIU','CHO','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','DANG','THE','NAO','CAN','XEM','MAI','HOM','TIE','THEO']);
  const state = { client: null, sending: false, history: [], tier: 'GUEST' };

  function node(tag, className, text = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function validTicker(value) {
    const ticker = String(value || '').toUpperCase();
    return /^[A-Z0-9]{3}$/.test(ticker) && /[A-Z]/.test(ticker);
  }

  function explicitTicker(text) {
    const tokens = String(text || '').toUpperCase().match(/\b[A-Z0-9]{3}\b/g) || [];
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

  function loadSupabaseLibrary() {
    if (window.supabase?.createClient) return Promise.resolve();
    if (window.__stockradarSupabaseLoading) return window.__stockradarSupabaseLoading;
    window.__stockradarSupabaseLoading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      script.async = true;
      script.onload = resolve;
      script.onerror = () => reject(new Error('Không tải được lớp tài khoản.'));
      document.head.append(script);
    });
    return window.__stockradarSupabaseLoading;
  }

  async function authSession() {
    if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey) return null;
    await loadSupabaseLibrary();
    if (!state.client) {
      state.client = window.supabase.createClient(config.supabaseUrl, config.supabasePublishableKey, {
        auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true }
      });
    }
    const { data } = await state.client.auth.getSession();
    return data?.session || null;
  }

  function addMessage(log, role, text, meta = '') {
    const wrap = node('div', `sr-center-message sr-center-${role}`);
    wrap.append(node('div', 'sr-center-bubble', text));
    if (meta) wrap.append(node('small', 'sr-center-meta', meta));
    log.append(wrap);
    log.scrollTop = log.scrollHeight;
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

  function sourceMeta(data) {
    const bits = [];
    const source = data?.source || {};
    const quota = data?.quota || {};
    if (data?.mode === 'ACTION_READY') bits.push('Action đã xác nhận');
    else if (data?.mode === 'RESEARCH_ONLY') bits.push('Góc nhìn nghiên cứu');
    else if (data?.mode === 'METHOD_ONLY') bits.push('Chưa đủ dữ liệu hiện tại');
    if (source.generated_at) {
      try { bits.push(`Dữ liệu ${new Date(source.generated_at).toLocaleString('vi-VN')}`); } catch (_) {}
    }
    if (data?.tier === 'GUEST') {
      if (quota.remaining != null) bits.push(`Khách · còn ${quota.remaining}/3 câu hôm nay`);
      else bits.push('Khách · tối đa 3 câu/ngày');
    } else if (data?.tier === 'FREE') {
      if (quota.remaining != null) bits.push(`Free · còn ${quota.remaining}/10 câu hôm nay`);
      else bits.push('Free · tối đa 10 câu/ngày');
    } else if (data?.tier === 'PAID') {
      bits.push('Paid · hỏi không giới hạn');
    } else if (data?.tier === 'TRIAL') {
      bits.push('Trial');
    }
    return bits.join(' · ');
  }

  function updatePlan(status, data = null, signedIn = false) {
    if (!status) return;
    const tier = data?.tier || (signedIn ? 'ACCOUNT' : 'GUEST');
    state.tier = tier;
    if (tier === 'GUEST') {
      const remaining = data?.quota?.remaining;
      status.textContent = remaining == null ? 'KHÁCH · 3 CÂU / NGÀY' : `KHÁCH · CÒN ${remaining}/3 CÂU HÔM NAY`;
      status.dataset.tier = 'guest';
    } else if (tier === 'FREE') {
      const remaining = data?.quota?.remaining;
      status.textContent = remaining == null ? 'FREE · 10 CÂU / NGÀY' : `FREE · CÒN ${remaining}/10 CÂU HÔM NAY`;
      status.dataset.tier = 'free';
    } else if (tier === 'PAID') {
      status.textContent = 'PAID · AI KHÔNG GIỚI HẠN · EMAIL ACTION ALERT';
      status.dataset.tier = 'paid';
    } else if (tier === 'TRIAL') {
      status.textContent = 'TRIAL · AI + QUYỀN THEO GÓI';
      status.dataset.tier = 'trial';
    } else {
      status.textContent = 'ĐÃ ĐĂNG NHẬP · QUYỀN THEO TÀI KHOẢN';
      status.dataset.tier = 'account';
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
      let session = null;
      try { session = await authSession(); } catch (_) {}
      const ticker = explicitTicker(message);
      const horizon = horizonFromText(message);
      const authenticated = Boolean(session?.access_token);

      if (!authenticated && !ticker) {
        addAction(log, 'Khách chưa đăng nhập có thể hỏi trực tiếp một mã HOSE. Để hỏi về danh mục/watchlist hoặc nhận 10 câu/ngày, hãy tạo tài khoản Free.', 'dang-ky/?plan=free', 'Tạo tài khoản Free');
        updatePlan(status, null, false);
        return;
      }

      const endpoint = authenticated ? 'stock-ai' : 'stock-ai-guest';
      const url = `${String(config.supabaseUrl).replace(/\/$/, '')}/functions/v1/${endpoint}`;
      const headers = { 'Content-Type': 'application/json', 'apikey': config.supabasePublishableKey };
      if (authenticated) headers.Authorization = `Bearer ${session.access_token}`;
      const body = authenticated ? {
        scope: ticker ? 'ticker' : (portfolioIntent(message) ? 'portfolio' : 'portfolio'),
        ticker: ticker || '',
        horizon,
        message: String(message).slice(0, 700),
        history: state.history.slice(-MAX_HISTORY)
      } : {
        ticker,
        horizon,
        message: String(message).slice(0, 700),
        history: state.history.slice(-MAX_HISTORY),
        guest_id: guestId()
      };

      const response = await fetch(url, { method: 'POST', headers, body: JSON.stringify(body) });
      let data = {};
      try { data = await response.json(); } catch (_) {}

      if (response.status === 401 && authenticated) {
        addAction(log, 'Phiên đăng nhập đã hết hạn. Hãy đăng nhập lại để tiếp tục với hạn mức tài khoản của bạn.', 'dang-nhap/', 'Đăng nhập lại');
        return;
      }

      const answer = data.answer || (response.ok ? 'StockRadar AI chưa có nội dung để trả lời.' : 'StockRadar AI tạm thời chưa thể phản hồi.');
      addMessage(log, 'assistant', answer, sourceMeta(data));
      updatePlan(status, data, authenticated);

      if (response.status === 429) {
        if (data?.tier === 'GUEST') addAction(log, 'Bạn có thể tiếp tục ngay bằng tài khoản Free với 10 câu/ngày.', 'dang-ky/?plan=free', 'Đăng ký Free');
        if (data?.tier === 'FREE') addAction(log, 'Nếu cần hỏi không giới hạn và nhận Action Alert qua email, hãy nâng cấp Paid.', 'dang-ky/?plan=premium', 'Xem gói Paid');
        return;
      }

      if (response.ok) {
        state.history.push({ role: 'user', content: String(message).slice(0, 600) });
        state.history.push({ role: 'assistant', content: String(answer).slice(0, 600) });
        state.history = state.history.slice(-MAX_HISTORY);
      }
    } catch (error) {
      addMessage(log, 'assistant', error?.message || 'Không thể kết nối StockRadar AI lúc này.');
    } finally {
      state.sending = false;
      input.disabled = false;
      send.disabled = false;
      send.textContent = oldLabel;
      input.focus();
    }
  }

  async function mount() {
    const host = document.querySelector('[data-stockradar-ai-center]');
    if (!host || host.dataset.mounted === 'true') return;
    host.dataset.mounted = 'true';

    const top = node('div', 'sr-center-top');
    const status = node('span', 'sr-center-plan', 'KHÁCH · 3 CÂU / NGÀY');
    const privacy = node('span', 'sr-center-privacy', 'Không nhập mật khẩu · OTP · mã giao dịch');
    top.append(status, privacy);

    const log = node('div', 'sr-center-log');
    log.setAttribute('aria-live', 'polite');
    addMessage(log, 'assistant', 'Tôi là StockRadar AI, dùng cùng lõi 4M/Payback · CANSLIM · định giá · SEPA/VCP · VPA · Pocket Pivot của StockRadar. Nhập một mã HOSE và hỏi thẳng điều bạn cần biết.');

    const chips = node('div', 'sr-center-chips');
    ['FPT mua được chưa?', 'MWG 3–6 tháng thế nào?', 'Rủi ro chính của VNM?', 'Danh mục hôm nay cần làm gì?'].forEach(label => {
      const button = node('button', '', label);
      button.type = 'button';
      chips.append(button);
    });

    const form = node('form', 'sr-center-form');
    const input = document.createElement('textarea');
    input.rows = 2;
    input.maxLength = 700;
    input.placeholder = 'Hỏi StockRadar AI về một mã HOSE…';
    input.setAttribute('aria-label', 'Hỏi StockRadar AI');
    const send = node('button', 'sr-center-send', 'Hỏi StockRadar AI');
    send.type = 'submit';
    form.append(input, send);

    const foot = node('div', 'sr-center-foot');
    foot.innerHTML = '<span><strong>Khách:</strong> 3 câu/ngày</span><span><strong>Free:</strong> 10 câu/ngày</span><span><strong>Paid:</strong> không giới hạn + email Action Alert</span>';

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
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });

    try {
      const session = await authSession();
      updatePlan(status, null, Boolean(session?.access_token));
    } catch (_) {
      updatePlan(status, null, false);
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true });
  else mount();
})();
