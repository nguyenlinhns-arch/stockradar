(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  const MAX_HISTORY = 6;
  const STOPWORDS = new Set([
    'MUA','BAN','GIU','CHO','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','DANG','THE','NAO','CAN','XEM','MAI','HOM','TIE','THEO'
  ]);
  const state = { ticker: tickerFromPage(), history: [], client: null, sending: false };

  function siteUrl(path = '') { return new URL(String(path).replace(/^\/+/, ''), document.baseURI).toString(); }

  function validTicker(value) {
    return /^[A-Z0-9]{3}$/.test(String(value || '')) && /[A-Z]/.test(String(value || ''));
  }

  function tickerFromPage() {
    const params = new URLSearchParams(location.search);
    const queryTicker = String(params.get('ticker') || '').trim().toUpperCase();
    if (validTicker(queryTicker)) return queryTicker;
    const parts = location.pathname.split('/').filter(Boolean);
    const coPhieuIndex = parts.findIndex(part => part.toLowerCase() === 'co-phieu');
    const routeTicker = coPhieuIndex >= 0 ? String(parts[coPhieuIndex + 1] || '').toUpperCase() : '';
    return validTicker(routeTicker) ? routeTicker : '';
  }

  function explicitTicker(text) {
    const tokens = String(text || '').toUpperCase().match(/\b[A-Z0-9]{3}\b/g) || [];
    return tokens.find(token => validTicker(token) && !STOPWORDS.has(token)) || '';
  }

  function isPortfolioPage() {
    return location.pathname.split('/').filter(Boolean).some(part => part.toLowerCase() === 'hom-nay');
  }

  function portfolioIntent(text) {
    const value = String(text || '').toLowerCase();
    return /(danh mục|danh muc|watchlist|mã tôi|ma toi|cổ phiếu của tôi|co phieu cua toi|đang sở hữu|dang so huu|các mã đang giữ|cac ma dang giu|tài khoản|tai khoan|hôm nay.*(làm gì|lam gi|chú ý|chu y)|mã nào.*(gần|gan|tốt|tot|rủi ro|rui ro))/.test(value);
  }

  function tickerForMessage(text) {
    const explicit = explicitTicker(text);
    if (explicit) return explicit;
    if (portfolioIntent(text)) return '';
    return state.ticker || '';
  }

  function requestScope(message, ticker) {
    if (ticker) return 'ticker';
    return portfolioIntent(message) || isPortfolioPage() ? 'portfolio' : '';
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
    wrap.append(node('div', 'sr-ai-bubble', 'Hãy đăng nhập để StockRadar AI đọc dữ liệu theo quyền tài khoản của bạn.'));
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
    const personalization = data?.personalization || {};
    const bits = [];
    if (data?.scope === 'portfolio') bits.push('Danh mục cá nhân');
    if (source.generated_at) {
      try { bits.push(`Dữ liệu ${new Date(source.generated_at).toLocaleString('vi-VN')}`); } catch (_) {}
    }
    if (source.snapshot_id) bits.push(`Snapshot ${String(source.snapshot_id).slice(0, 18)}`);
    if (personalization.watchlist_count != null) bits.push(`${personalization.watchlist_count} mã theo dõi`);
    if (personalization.owned_count != null) bits.push(`${personalization.owned_count} mã đang sở hữu`);
    if (data?.quota?.remaining != null) bits.push(`Còn ${data.quota.remaining} lượt`);
    return bits.join(' · ');
  }

  async function askAI(message, log, input, sendButton) {
    if (state.sending) return;
    const ticker = tickerForMessage(message);
    const scope = requestScope(message, ticker);
    if (!scope) {
      appendMessage(log, 'assistant', 'Hãy nhập một mã HOSE, hoặc hỏi về danh mục/watchlist, ví dụ: “FPT mua được chưa?” hay “Danh mục hôm nay cần chú ý gì?”.');
      return;
    }
    if (ticker) state.ticker = ticker;
    const horizon = horizonFromText(message);
    state.sending = true;
    input.disabled = true;
    sendButton.disabled = true;
    sendButton.textContent = scope === 'portfolio' ? 'Đang đọc danh mục…' : 'Đang đọc dữ liệu…';

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
          scope,
          ticker: ticker || '',
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

  function chipLabels() {
    if (isPortfolioPage()) {
      return ['Danh mục hôm nay cần làm gì?', 'Watchlist có mã nào đáng chú ý?', 'Mã đang giữ cần chú ý gì?', 'Rủi ro danh mục'];
    }
    if (state.ticker) return ['Mua được chưa?', '3–6 tháng thế nào?', 'Rủi ro chính', 'Đang nắm giữ thì sao?'];
    return ['Danh mục hôm nay', 'Watchlist có gì mới?', 'Mã đang giữ cần chú ý?', '3–6 tháng mã nào tốt?'];
  }

  function mountContextShortcut(setOpen, input) {
    const actions = document.querySelector('.page-heading-actions');
    if (!actions || actions.querySelector('[data-stockradar-ai-shortcut]')) return;
    let label = '';
    let prompt = '';
    if (isPortfolioPage()) {
      label = 'Hỏi StockRadar AI';
      prompt = 'Danh mục hôm nay cần làm gì?';
    } else if (state.ticker) {
      label = `Hỏi AI về ${state.ticker}`;
      prompt = `${state.ticker} mua mới hay chờ?`;
    } else {
      return;
    }
    const button = node('button', 'button button-primary button-small', label);
    button.type = 'button';
    button.dataset.stockradarAiShortcut = '';
    button.addEventListener('click', () => {
      setOpen(true);
      input.value = prompt;
      input.focus();
    });
    actions.prepend(button);
  }

  function mount() {
    if (document.querySelector('[data-stockradar-ai]')) return;

    const root = node('div', 'sr-ai-root');
    root.dataset.stockradarAi = '';
    const launcher = node('button', 'sr-ai-launcher', '✦ StockRadar AI');
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
    heading.append(node('span', '', 'Hỏi về mã HOSE, watchlist và danh mục của bạn'));
    const close = node('button', 'sr-ai-close', '×');
    close.type = 'button';
    close.setAttribute('aria-label', 'Đóng StockRadar AI');
    header.append(heading, close);

    const log = node('div', 'sr-ai-log');
    log.setAttribute('aria-live', 'polite');
    const greeting = isPortfolioPage()
      ? 'Tôi có thể đọc watchlist và các mã bạn đánh dấu đang sở hữu. Hỏi “Danh mục hôm nay cần làm gì?” hoặc “Watchlist có mã nào đáng chú ý?”.'
      : state.ticker
        ? `Bạn đang xem ${state.ticker}. Hỏi “mua được chưa?”, “3–6 tháng thế nào?” hoặc “đang nắm giữ thì sao?”.`
        : 'Bạn có thể hỏi một mã HOSE hoặc hỏi toàn danh mục/watchlist. Tôi chỉ dùng dữ liệu StockRadar đã vượt điều kiện phát hành.';
    appendMessage(log, 'assistant', greeting);

    const chips = node('div', 'sr-ai-chips');
    chipLabels().forEach(label => {
      const button = node('button', '', label);
      button.type = 'button';
      button.addEventListener('click', () => {
        const isPortfolioLabel = portfolioIntent(label) || isPortfolioPage();
        input.value = state.ticker && !isPortfolioLabel ? `${state.ticker} ${label}` : label;
        input.focus();
      });
      chips.append(button);
    });

    const form = node('form', 'sr-ai-form');
    const input = document.createElement('textarea');
    input.rows = 2;
    input.maxLength = 700;
    input.placeholder = isPortfolioPage()
      ? 'VD: Danh mục hôm nay cần làm gì?'
      : state.ticker ? `Hỏi về ${state.ticker}…` : 'VD: FPT mua được chưa?';
    input.setAttribute('aria-label', 'Câu hỏi cho StockRadar AI');
    const send = node('button', 'sr-ai-send', 'Gửi');
    send.type = 'submit';
    form.append(input, send);

    const disclaimer = node('p', 'sr-ai-disclaimer', 'AI chỉ diễn giải dữ liệu StockRadar và dữ liệu tài khoản đã đăng nhập. Không tự tạo giá hoặc tín hiệu khi dữ liệu chưa đạt chuẩn.');
    panel.append(header, log, chips, form, disclaimer);
    root.append(panel, launcher);
    document.body.append(root);

    const setOpen = (open) => {
      panel.hidden = !open;
      launcher.setAttribute('aria-expanded', String(open));
      root.classList.toggle('is-open', open);
      if (open) setTimeout(() => input.focus(), 0);
    };
    mountContextShortcut(setOpen, input);
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