// PROJECT_AUTORESUME_ROUTING_V1
// PRIVATE_PROJECT_BRIDGE_V1
import { normalizeResearchContext } from './stockradar-core.ts';

function extractStockTickers(text) {
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
  return tickers;
}

export function parseResearchQuery(message: string, requestedTicker = '') {
  const q = message.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLowerCase();
  const explicit = extractStockTickers(message);
  const requested = String(requestedTicker || '').trim().toUpperCase();
  const tickers = explicit.length ? explicit : /^[A-Z0-9]{3}$/.test(requested) && /[A-Z]/.test(requested) ? [requested] : [];
  const scan = /\b(top|quet|loc|ma nao|co phieu nao|nganh nao)\b/.test(q) || (!tickers.length && /\bnganh\b/.test(q));
  const filter = /pocket/.test(q)?'pocket_pivot':/(gan|chuan bi|near).*breakout|gan.*pivot/.test(q)?'near_pivot':/breakout/.test(q)?'breakout':'top';
  const sector = /ngan hang/.test(q)?'Ngân hàng':/thep/.test(q)?'Thép':/bat dong san/.test(q)?'Bất động sản':'';
  return {scope:scan?'scan':tickers.length>1?'compare':tickers.length?'ticker':'portfolio',tickers,filter,sector};
}

export async function loadResearchQuery(db: any, query: ReturnType<typeof parseResearchQuery>) {
  if(query.scope==='scan') {
    const {data,error}=await db.rpc('query_stockradar_research',{p_filter:query.filter,p_sector:query.sector,p_limit:5});
    if(error) throw new Error('DATA_QUERY_UNAVAILABLE');
    return (data?.items||[]).map(normalizeResearchContext).filter(Boolean);
  }
  return (await Promise.all(query.tickers.map(async ticker=>{
    const {data,error}=await db.rpc('fetch_stockradar_ai_context',{p_ticker:ticker});
    if(error) throw new Error('DATA_QUERY_UNAVAILABLE');
    return normalizeResearchContext(data);
  }))).filter(Boolean);
}

// Hosted Supabase's trusted proxy supplies CF-Connecting-IP. Client IDs are never quota identities.
export async function guestQuotaIdentity(req: Request, secret: string) {
  const ip = req.headers.get('cf-connecting-ip')?.trim();
  if(!ip || !/^[0-9a-fA-F:.]{3,45}$/.test(ip)) return null;
  const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(secret),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  const digest=await crypto.subtle.sign('HMAC',key,new TextEncoder().encode('stockradar-guest-network-v1|'+ip));
  return Array.from(new Uint8Array(digest),x=>x.toString(16).padStart(2,'0')).join('');
}
