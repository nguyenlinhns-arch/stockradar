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
    const standalone = masked.trim() === match[0] && match[2] === ticker;
    const command = /^(MUA|BAN|GIU|CHO|GHI|TOP|SAO|KHI|NEU|HAY|TOI|XEM|CAC|CUA|VOI|NAY|ROI|RUI|CHI|THE|FOR|AND|ALL|GET|SET)$/.test(ticker);
    if (command && !match[1]) continue;
    if (words.has(ticker) && !match[1] && !stockCue && !standalone) continue;
    if (!tickers.includes(ticker)) tickers.push(ticker);
    if (tickers.length === 4) break;
  }
  return tickers;
}
