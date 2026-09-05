// Explanations of observed values; these do not create or change trading signals.
function num(value: any): number | null {
  if (value == null || typeof value === 'boolean' || typeof value === 'object' || String(value).trim() === '') return null;
  const n = Number(value); return Number.isFinite(n) ? n : null;
}
function first(...values: any[]): number | null { for (const v of values) { const n = num(v); if (n != null) return n; } return null; }
function number(value: number, digits = 1): string { return value.toLocaleString('vi-VN', { maximumFractionDigits: digits }); }
function price(value: number): string { return `${number(Math.round(value), 0)}đ`; }
export function observationDate(value: any): string {
  const s = String(value || '').slice(0, 10), m = s.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  return m ? `${m[3]}/${m[2]}/${m[1]}` : 'chưa rõ ngày quan sát';
}
export function wantsResearchDetail(question = ''): boolean {
  // A general "phân tích" request still gets the plain, concise answer.
  const q = question.normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').toLowerCase();
  if (/\b(ngan gon|don gian|de hieu|tom tat)\b/.test(q)) return false;
  return /\b(chi tiet|chuyen sau|day du chi so|bang diem|toan bo du lieu)\b/.test(q);
}

export function readableResearchFacts(context: any): any {
  const c = context || {}, t = c.technical_detail || {}, a = c.analysis || {}, post = c.scanner_postclose || {}, q = c.quote || {};
  const p = first(q.price, a.price, post.price), pivot = first(t.pivot20, t.pivot, post.pivot20, post.pivot);
  const date = observationDate(c.as_of_date), mode = c.volume_mode || t.volume_mode || 'UNKNOWN';
  const priceLabel = mode === 'EOD' ? 'Giá đóng cửa' : 'Giá ghi nhận';
  let priceText = p != null ? `${priceLabel} ngày ${date}: ${price(p)}.` : `Chưa có giá ngày ${date} để so sánh.`;
  if (pivot != null && pivot > 0) {
    if (p != null && p > 0) {
      const delta = p - pivot;
      priceText = `${priceLabel} ngày ${date}: ${price(p)}, ${delta === 0 ? `bằng mốc theo dõi ${price(pivot)}` : `${delta < 0 ? 'thấp hơn' : 'cao hơn'} mốc theo dõi ${price(pivot)} là ${price(Math.abs(delta))} (khoảng ${number(Math.abs(delta) / pivot * 100)}% tính theo mốc ${price(pivot)})`}.`;
    } else priceText += ` Mốc theo dõi là ${price(pivot)}; chưa tính được chênh lệch.`;
  }
  const volume = first(t.volume, q.volume, post.volume), vol20 = first(t.vol20, t.volume20, t.avg_volume_20, post.vol20);
  const rvol = mode === 'EOD' ? (volume != null && volume >= 0 && vol20 != null && vol20 > 0 ? volume / vol20 : num(t.rvol)) : null;
  let volumeText = '';
  if (rvol != null && rvol >= 0) {
    const amount = volume != null && volume >= 0 ? `${number(volume, 0)} cổ phiếu được giao dịch trong phiên` : 'Khối lượng giao dịch cuối phiên';
    const comparison = rvol === 1 ? 'bằng' : `${rvol < 1 ? 'thấp hơn' : 'cao hơn'} khoảng ${number(Math.abs(rvol - 1) * 100)}% so với`;
    volumeText = `${amount}, ${comparison} mức trung bình 20 phiên trước${vol20 != null && vol20 > 0 ? ` (${number(vol20, 0)} cổ phiếu/phiên)` : ''}.`;
  } else if (mode === 'INTRADAY') {
    const sameTime = num(t.same_time_volume_ratio), projected = num(t.rvol_progress_adjusted);
    if (sameTime != null && sameTime >= 0) volumeText = `Khối lượng đang giao dịch bằng khoảng ${number(sameTime * 100)}% mức trung bình tại cùng thời điểm của các phiên so sánh. Phiên hôm nay chưa kết thúc.`;
    else if (projected != null && projected >= 0) volumeText = `Khối lượng cả phiên ước tính bằng khoảng ${number(projected * 100)}% mức trung bình 20 phiên trước. Đây là ước tính trong phiên, chưa phải số cuối phiên.`;
    else volumeText = 'Chưa đủ dữ liệu khối lượng tại cùng thời điểm để đánh giá giao dịch trong phiên.';
  }
  // Prefer the existing daily engine's benchmark, not a legacy intraday flag.
  const downMax = first(t.computed_indicators?.max_down_volume10, t.max_down_volume10, t.max_down_volume_10, post.max_down_volume10);
  const earlyVolumePass = mode === 'EOD' && volume != null && volume >= 0 && downMax != null && downMax > 0 ? volume > downMax : null;
  const earlyVolumeText = earlyVolumePass == null
    ? 'Chưa đủ dữ liệu phù hợp để xác nhận điều kiện khối lượng của điểm mua sớm.'
    : `Điều kiện khối lượng của điểm mua sớm ${earlyVolumePass ? 'đạt' : 'chưa đạt'}: ${number(volume!, 0)} cổ phiếu ${earlyVolumePass ? 'lớn hơn' : 'chưa vượt'} ${number(downMax!, 0)} cổ phiếu — mức giao dịch lớn nhất trong các phiên giảm giá thuộc 10 phiên trước. Đây chỉ là một điều kiện, chưa đủ để kết luận nên mua.`;
  return { price: p, pivot, priceText, volumeText, earlyVolumeText, earlyVolumePass, downMax, rvol, date };
}
