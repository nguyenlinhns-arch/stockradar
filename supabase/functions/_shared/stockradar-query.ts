import { normalizeResearchContext } from './stockradar-core.ts';

const STOP = new Set(['CHI','DON','GON','SAU','TIN','RUI','MOC','MOI','TOP','MUA','BAN','GIU','CHO','GIA','NAY','SAO','KHI','NEU','HAY','DAI','HAN','VON','LOI','ROI','THE','NAO','CAN','XEM','MAI','HOM','CAC','CUA','VOI','TAI']);
export function parseResearchQuery(message: string, requestedTicker = '') {
  const q = message.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLowerCase();
  // Accented Vietnamese words such as “đạt” must not become ticker DAT.
  const tokens = (message.toUpperCase().match(/(?<![\p{L}\p{N}])[A-Z0-9]{3}(?![\p{L}\p{N}])/gu)||[]).filter(t=>/[A-Z]/.test(t)&&!STOP.has(t));
  const tickers = [...new Set([requestedTicker.toUpperCase(),...tokens].filter(Boolean))].slice(0,4);
  const scan = /\b(top|quet|nganh|ma nao|co phieu nao)\b/.test(q);
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
