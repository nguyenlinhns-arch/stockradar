(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const MAX_HISTORY = 6;
  const STOPWORDS = new Set([
    'MUA','BAN','GIU','CHO','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','DANG','THE','NAO','CAN','XEM','MAI','HOM','TIE','THEO'
  ]);
  const state = { ticker: tickerFromPage(), history: [], client: null, sending: false };

  function siteUrl(path = '') { return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString(); }

  function tickerFromPage() {
    const params = new URLSearchParams(location.search);
    const queryTicker = String(params.get('ticker') || '').trim().toUpperCase();
    if (/^[A-Z]{3}$/.test(queryTicker)) return queryTicker;
    const parts = location.pathname.split('/').filter(Boolean);
    const coPhieuIndex = parts.findIndex(part => part.toLowerCase() === 'co-phieu');
    const routeTicker = coPhieuIndex >= 0 ? String(parts[coPhieuIndex + 1] || '').toUpperCase() : '';
    return /^[A-Z]{3}$/.test(routeTicker) ? routeTicker : '';
  }

  function extractTicker(text) {
    const tokens = String(text || '').toUpperCase().match(/\b[A-Z]{3}\b/g) || [];
    return tokens.find(token => !STOPWORDS.has(token)) || state.ticker || '';
  }

  function horizonFromText(text) {
    const value = String(text || '').toLowerCase();
    if (/(tích sản|tich san|2\s*[-–]\s*5\s*năm|dài hạn nhiều năm)/.test(value)) return 'ACCUMULATION';
    if (/(12\s*tháng|12\s*thang|6\s*[-–]\s*18\s*tháng|dài hạn|dai han)/.test(value)) return 'LONG_TERM';
    if (/(3\s*[-–]\s*6\s*tháng|1\s*[-–]\s*6\s*tháng|trung hạn|trung han|6\s*tháng|6\s*thang)/.test(value)) return 'MEDIUM_TERM';
    return 'SHORT_TERM';
  }

  function loadSupabaseLibrary() {
    if (window.supabase?.createClient) return Promise.resolve();
    if (window.__stockradarSupabaseLoading) return window.__stockradarSupabaseLoading;
    window.__stockradarSupabaseLoading = new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2';
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Không tải được lớp đăng nhập.'));
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

  function node(tag, className, text = '') {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (text) el.textContent = text;
    return el;
  }

  function appendMessage(log, role, text, meta = '') {
    const wrap = node('div', `sr-ai-message sr-ai-${role}`);
    const body = node('div', 'sr-ai-bubble', text);
    wrap.append(body);
    if (meta) wrap.append(node('small', 'sr-ai-meta', meta));
    log.append(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function appendLogin(log) {
    const wrap = node('div', 'sr-ai-message sr-ai-assistant');
    wrap.append(node('div', 'sr-ai-bubble', 'Hãy đăng nhập để StockRadar AI đọc báo cáo theo quyền tài khoản của bạn.'));
    const link = node('a', 'sr-ai-login', 'Đăng nhập để hỏi AI');
    const login = new URL('dang-nhap/', document.baseURI);
    login.searchParams.set('next', location.href);
    link.href = login.toString();
    wrap.append(link);
    log.append(wrap);
    log.scrollTop = log.scrollHeight;
  }

  function sourceMeta(data) {
    const source = data?.source || {};
    const bits = [];
    if (source.generated_at) {
      try { bits.push(`Dữ liệu ${new Date(source.generated_at).toLocaleString('vi-VN')}`); } catch (_) {}
    }
    if (source.snapshot_id) bits.push(`Snapshot ${String(source.snapshot_id).slice(0, 18)}`);
    if (data?.quota?.remaining != null) bits.push(`Còn ${data.quota.remaining} lượt`);
    return bits.join(' · ');
  }

  async function askAI(message, log, input, sendButton) {
    if (state.sending) return;
    const ticker = extractTicker(message);
    if (!ticker) {
      appendMessage(log, 'assistant', 'Hãy nhập mã HOSE gồm 3 chữ cái, ví dụ: “FPT mua được chưa?”.');
      return;
    }
    state.ticker = ticker;
    const horizon = horizonFromText(message);
    state.sending = true;
    input.disabled = true;
    sendButton.disabled = true;
    sendButton.textContent = 'Đang đọc dữ liệu…';

    try {
      const session = await authSession();
      if (!session?.access_token) {
        appendLogin(log);
        return;
      }
      const endpoint = `${String(config.supabaseUrl).replace(/\/$/, '')}/functions/v1/stock-ai`;
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'apikey': config.supabasePublishableKey,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          ticker,
          horizon,
          message: String(message).slice(0, 700),
          history: state.history.slice(-MAX_HISTORY)
        })
      });
      let data = {};
      try { data = await response.json(); } catch (_) {}
      if (response.status === 401) {
        appendLogin(log);
        return;
      }
      const answer = data.answer || (response.ok
        ? 'StockRadar AI chưa có nội dung để trả lời.'
        : 'StockRadar AI tạm thời chưa thể phản hồi.');
      appendMessage(log, 'assistant', answer, sourceMeta(data));
      state.history.push({ role: 'user', content: String(message).slice(0, 600) });
      state.history.push({ role: 'assistant', content: String(answer).slice(0, 600) });
      state.history = state.history.slice(-MAX_HISTORY);
    } catch (error) {
      appendMessage(log, 'assistant', error?.message || 'Không thể kết nối StockRadar AI lúc này.');
    } finally {
      state.sending = false;
      input.disabled = false;
      sendButton.disabled = false;
      sendButton.textContent = 'Gửi';
      input.focus();
    }
  }

  function mount() {
    if (document.querySelector('[data-stockradar-ai]')) return;

    const root = node('div', 'sr-ai-root');
    root.dataset.stockradarAi = '';
    const launcher = node('button', 'sr-ai-launcher', '✦ AI Phân tích');
    launcher.type = 'button';
    launcher.setAttribute('aria-expanded', 'false');
    launcher.setAttribute('aria-controls', 'stockradar-ai-panel');

    const panel = node('section', 'sr-ai-panel');
    panel.id = 'stockradar-ai-panel';
    panel.hidden = true;
    panel.setAttribute('aria-label', 'StockRadar AI');

    const header = node('header', 'sr-ai-header');
    const heading = node('div', 'sr-ai-heading');
    heading.append(node('strong', '', 'StockRadar AI'));
    heading.append(node('span', '', 'Phân tích mã HOSE trên dữ liệu StockRadar'));
    const close = node('button', 'sr-ai-close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', 'Đóng StockRadar AI');
    header.append(heading, close);

    const log = node('div', 'sr-ai-log');
    log.setAttribute('aria-live', 'polite');
    appendMessage(log, 'assistant', state.ticker
      ? `Bạn đang xem ${state.ticker}. Hỏi tôi “mua được chưa?”, “3–6 tháng thế nào?” hoặc “rủi ro chính là gì?”.`
      : 'Nhập một mã HOSE và câu hỏi, ví dụ: “FPT mua được chưa?”. Tôi chỉ diễn giải dữ liệu StockRadar đã vượt Data Gate.');

    const chips = node('div', 'sr-ai-chips');
    ['Mua được chưa?', 'Phân tích 3–6 tháng', 'Rủi ro chính', 'Đang nắm giữ thì sao?'].forEach(label => {
      const button = node('button', '', label);
      button.type = 'button';
      button.addEventListener('click', () => {
        if (state.ticker) input.value = `${state.ticker} ${label}`;
        else input.value = label;
        input.focus();
      });
      chips.append(button);
    });

    const form = node('form', 'sr-ai-form');
    const input = document.createElement('textarea');
    input.rows = 2;
    input.maxLength = 700;
    input.placeholder = state.ticker ? `Hỏi về ${state.ticker}…` : 'VD: FPT mua được chưa?';
    input.setAttribute('aria-label', 'Câu hỏi cho StockRadar AI');
    const send = node('button', 'sr-ai-send', 'Gửi');
    send.type = 'submit';
    form.append(input, send);

    const disclaimer = node('p', 'sr-ai-disclaimer', 'AI chỉ diễn giải dữ liệu StockRadar. Không tự tạo giá hoặc tín hiệu khi Data Gate chưa đạt.');
    panel.append(header, log, chips, form, disclaimer);
    root.append(panel, launcher);
    document.body.append(root);

    const setOpen = (open) => {
      panel.hidden = !open;
      launcher.setAttribute('aria-expanded', String(open));
      root.classList.toggle('is-open', open);
      if (open) setTimeout(() => input.focus(), 0);
    };
    launcher.addEventListener('click', () => setOpen(panel.hidden));
    close.addEventListener('click', () => setOpen(false));
    document.addEventListener('keydown', event => { if (event.key === 'Escape' && !panel.hidden) setOpen(false); });
    form.addEventListener('submit', event => {
      event.preventDefault();
      const message = input.value.trim();
      if (!message) return;
      appendMessage(log, 'user', message);
      input.value = '';
      askAI(message, log, input, send);
    });
    input.addEventListener('keydown', event => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        form.requestSubmit();
      }
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount);
  else mount();
})();
