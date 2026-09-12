// STOCKRADAR_PROJECT_LIVE_BRIDGE_V1
// Owner-authenticated website requests are routed through the linked ChatGPT Project queue.
// Guest traffic and accounts without an active Project channel keep the existing AI path.
(() => {
  'use strict';

  const config = window.STOCKRADAR_AUTH_CONFIG || {};
  if (!config.configured || !config.supabaseUrl || !config.supabasePublishableKey || window.__stockradarProjectLiveBridgeInstalled) return;
  window.__stockradarProjectLiveBridgeInstalled = true;

  const nativeFetch = window.fetch.bind(window);
  const base = String(config.supabaseUrl).replace(/\/$/, '');
  const HORIZONS = new Set(['SHORT_TERM','MEDIUM_TERM','LONG_TERM','ACCUMULATION']);
  const MAX_WAIT_MS = 120000;
  const POLL_MS = 1600;

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const uuid = () => globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}-${Math.random().toString(16).slice(2)}`;
  const validUuid = value => /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(String(value || ''));

  function requestUrl(input) {
    if (typeof input === 'string') return input;
    if (input instanceof URL) return input.toString();
    return String(input?.url || '');
  }

  function requestMethod(input, init) {
    return String(init?.method || input?.method || 'GET').toUpperCase();
  }

  function requestHeaders(input, init) {
    const headers = new Headers(input?.headers || {});
    new Headers(init?.headers || {}).forEach((value, key) => headers.set(key, value));
    return headers;
  }

  function jsonResponse(body, status = 200) {
    return new Response(JSON.stringify(body), {
      status,
      headers: {
        'Content-Type': 'application/json; charset=utf-8',
        'Cache-Control': 'no-store',
        'X-StockRadar-Project-Bridge': 'live-v1'
      }
    });
  }

  async function parseJson(response) {
    try { return await response.json(); } catch (_) { return null; }
  }

  async function rpc(name, args, headers) {
    const response = await nativeFetch(`${base}/rest/v1/rpc/${name}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'apikey': headers.get('apikey') || config.supabasePublishableKey,
        'Authorization': headers.get('Authorization') || ''
      },
      body: JSON.stringify(args || {})
    });
    const data = await parseJson(response);
    if (!response.ok) {
      const error = new Error(String(data?.message || data?.code || `RPC_${response.status}`));
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  async function readQuestion(id, headers) {
    const select = 'id,thread_id,status,answer,answer_source,evidence,answered_at,updated_at,research_ticker,research_snapshot_id,research_as_of_date,research_context_grade';
    const url = `${base}/rest/v1/stockradar_project_questions?id=eq.${encodeURIComponent(id)}&select=${encodeURIComponent(select)}`;
    const response = await nativeFetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
        'apikey': headers.get('apikey') || config.supabasePublishableKey,
        'Authorization': headers.get('Authorization') || ''
      }
    });
    const data = await parseJson(response);
    if (!response.ok) throw new Error(`PROJECT_STATUS_${response.status}`);
    return Array.isArray(data) ? data[0] || null : null;
  }

  function answeredPayload(row) {
    return {
      status: 'READY',
      mode: 'CHATGPT_PROJECT',
      answer_engine: 'CHATGPT_PROJECT_BRIDGE',
      model_status: 'MODEL_READY',
      provider_attempted: false,
      quota_consumed: false,
      conversation_persisted: true,
      public_action_allowed: false,
      thread_id: row.thread_id,
      project_question_id: row.id,
      ticker: row.research_ticker || '',
      answer: String(row.answer || ''),
      source: {
        kind: 'CHATGPT_PROJECT',
        answer_source: row.answer_source || 'CHATGPT_PROJECT',
        snapshot_id: row.research_snapshot_id || null,
        as_of_date: row.research_as_of_date || null,
        context_grade: row.research_context_grade || null,
        generated_at: row.answered_at || row.updated_at || null
      },
      project_bridge: {
        available: true,
        sync_mode: 'LIVE_PROJECT_QUEUE',
        context_loaded: true,
        context_applied: true
      },
      evidence: Array.isArray(row.evidence) ? row.evidence : []
    };
  }

  function pendingPayload(row, submitted) {
    return {
      status: 'PROJECT_PENDING',
      mode: 'CHATGPT_PROJECT',
      answer_engine: 'CHATGPT_PROJECT_BRIDGE',
      model_status: 'WAITING_FOR_PROJECT',
      provider_attempted: false,
      quota_consumed: false,
      conversation_persisted: false,
      public_action_allowed: false,
      thread_id: row?.thread_id || null,
      project_question_id: row?.id || submitted?.id || null,
      ticker: row?.research_ticker || submitted?.research_ticker || '',
      answer: 'Câu hỏi đã được chuyển vào đúng Project StockRadar trên ChatGPT. Cầu nối đang chờ xử lý; nếu bạn rời trang, câu trả lời vẫn được lưu vào lịch sử ngay khi Project hoàn tất.',
      source: {
        kind: 'CHATGPT_PROJECT_QUEUE',
        snapshot_id: row?.research_snapshot_id || null,
        as_of_date: row?.research_as_of_date || submitted?.research_as_of_date || null,
        context_grade: row?.research_context_grade || submitted?.research_context_grade || null,
        generated_at: row?.updated_at || null
      },
      project_bridge: {
        available: true,
        sync_mode: 'LIVE_PROJECT_QUEUE',
        context_loaded: true,
        context_applied: false
      }
    };
  }

  async function routeProjectAsk(payload, headers) {
    const channel = await rpc('get_my_stockradar_project_channel', {}, headers);
    if (channel?.available !== true) return null;

    const horizon = HORIZONS.has(String(payload?.horizon || '').toUpperCase())
      ? String(payload.horizon).toUpperCase()
      : 'SHORT_TERM';
    const clientKey = uuid();
    if (!validUuid(clientKey)) return null;

    const submitted = await rpc('submit_my_stockradar_project_question', {
      p_question: String(payload?.message || '').slice(0, 6000),
      p_horizon: horizon,
      p_client_key: clientKey,
      p_parent_id: null
    }, headers);

    if (!validUuid(submitted?.id)) throw new Error('PROJECT_QUEUE_INVALID_ID');
    const deadline = Date.now() + MAX_WAIT_MS;
    let row = await readQuestion(submitted.id, headers);

    while (Date.now() < deadline) {
      if (row?.status === 'ANSWERED' && row?.answer) return answeredPayload(row);
      if (row?.status === 'CANCELLED') throw new Error('PROJECT_QUESTION_CANCELLED');
      await sleep(POLL_MS);
      row = await readQuestion(submitted.id, headers);
    }
    return pendingPayload(row, submitted);
  }

  window.fetch = async function stockRadarProjectAwareFetch(input, init = {}) {
    const url = requestUrl(input);
    if (!url.includes('/functions/v1/stock-ai-chat') || requestMethod(input, init) !== 'POST') {
      return nativeFetch(input, init);
    }

    let payload = null;
    try { payload = JSON.parse(typeof init.body === 'string' ? init.body : 'null'); } catch (_) {}
    if (!payload || String(payload.operation || 'ask').toLowerCase() !== 'ask') return nativeFetch(input, init);

    const headers = requestHeaders(input, init);
    if (!/^Bearer\s+\S+/i.test(headers.get('Authorization') || '')) return nativeFetch(input, init);

    try {
      const result = await routeProjectAsk(payload, headers);
      if (result) return jsonResponse(result, 200);
    } catch (error) {
      // A missing/disabled Project channel must never break the existing StockRadar AI path.
      const text = String(error?.message || '');
      if (/PROJECT_CHANNEL_NOT_AVAILABLE|AUTHENTICATION_REQUIRED|ACCOUNT_NOT_ACTIVE|WORKSPACE|PGRST|404/i.test(text)) {
        return nativeFetch(input, init);
      }
      console.warn('StockRadar Project Live Bridge:', text);
      return jsonResponse({
        status: 'PROJECT_BRIDGE_UNAVAILABLE',
        mode: 'CHATGPT_PROJECT',
        model_status: 'MODEL_NOT_CALLED',
        provider_attempted: false,
        quota_consumed: false,
        conversation_persisted: false,
        public_action_allowed: false,
        answer: 'Cầu nối Project tạm thời chưa nhận được câu trả lời. Yêu cầu không được chuyển sang một mô hình trả phí khác; vui lòng mở lại lịch sử sau.'
      }, 200);
    }

    return nativeFetch(input, init);
  };

  window.StockRadarProjectLiveBridge = Object.freeze({
    version: '1.0.0',
    mode: 'LIVE_PROJECT_QUEUE',
    modelApiFallback: false
  });
})();
