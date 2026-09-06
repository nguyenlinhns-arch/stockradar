// A strict, non-identifying envelope shared by anonymous measurement and signup receipts.
export const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
export const FUNNEL_EVENTS = new Set(['landing_view','ai_question_started','ai_result_success','ai_result_failed','ai_guest_first_result','guest_free_cta_impression','guest_free_cta_click','signup_view','signup_started','signup_submitted','signup_verification_requested','signup_completed','login_success','return_to_ai_after_registration','premium_view','checkout_view','checkout_started','payment_submitted','ticker_lookup_submit','stock_report_view','premium_sample_view','performance_proof_view','conversion_click','free_activation','meaningful_report','meaningful_return_d1','meaningful_return_d7','email_cta_landing']);
const UTM = ['utm_source','utm_medium','utm_campaign','utm_content','utm_term'];
export function cleanTouch(value: unknown) {
  const v = value && typeof value === 'object' ? value as Record<string, unknown> : {};
  const out: Record<string, unknown> = {source: ['facebook','instagram','organic','direct','other'].includes(String(v.source)) ? v.source : 'direct'};
  for (const k of UTM) {
    const s = typeof v[k] === 'string' ? String(v[k]).trim() : '';
    if (s.length <= 120 && /^[\p{L}\p{N} _.,+-]+$/u.test(s) && !/(?:eyJ|sk-|sb_secret_|Bearer|https?)/i.test(s)) out[k] = s;
  }
  return out;
}
export async function hash(value: string) {
  const bytes = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  return Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, '0')).join('');
}
export async function fingerprints(req: Request, session: unknown, serverKey: string) {
  const sid = UUID.test(String(session || '')) ? String(session) : crypto.randomUUID();
  const day = new Date(Date.now() + 7 * 3600000).toISOString().slice(0, 10);
  const address = req.headers.get('cf-connecting-ip') || req.headers.get('x-forwarded-for')?.split(',')[0]?.trim() || 'unknown';
  // The daily connection hash is used for abuse limits only; neither hash goes to Meta.
  return {session: await hash(`${serverKey}|funnel-session-v2|${sid}`), ip: await hash(`${serverKey}|funnel-ip-v2|${day}|${address}`)};
}
export function knownBot(req: Request) {
  return /bot\b|crawler|spider|HeadlessChrome|facebookexternalhit|preview|slurp/i.test(req.headers.get('user-agent') || '');
}
