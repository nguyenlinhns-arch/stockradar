// Pure formatting helpers; caller must authenticate and load the owned thread first.
export function projectRecordIntent(message) {
  const q = String(message || '').normalize('NFC').replace(/\bbạn\b/giu,' ').normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/[đĐ]/g,'d').toLowerCase().trim();
  if (!/(lien thong|dong bo|ngu canh|tri thuc|chatgpt)/.test(q)) return null;
  const guardText = q.replace(/\b(phien ban|ban tom tat|ban ngu canh|ban tri thuc)\b/g,' ');
  // Mixed action/market questions still use the normal analysis and quota gates.
  if (/\b(mua|ban|gia|target|stop|top|quet|loc|email|otp|mat khau)\b|dinh gia|cat lo|loi nhuan|pocket|canslim|sepa|vpa|4m|nang (cap|goi)|thanh toan/.test(guardText)) return null;
  if (/(xem|hien thi|doc lai|cho xem|noi dung|tom tat)/.test(q) && /(ngu canh|tri thuc|ban tom tat)/.test(q)) return 'SUMMARY';
  if (/(lien thong|dong bo)/.test(q) && /(chua|khong|trang thai|kiem tra|da |dang |the nao)/.test(q)) return 'STATUS';
  if (/(ngu canh|tri thuc)/.test(q) && /(phien ban|cap nhat luc|ngay cap nhat)/.test(q)) return 'STATUS';
  return null;
}

export function projectRecordAnswer(bridge, threadId, intent) {
  if (!['STATUS','SUMMARY'].includes(intent)) return null;
  const linked = Boolean(bridge && bridge.thread_id === threadId);
  if (!linked) return {
    status:'READY', mode:'PROJECT_CONTEXT_ONLY', scope:'conversation',
    answer_engine:'PROJECT_HANDOFF_RECORD', model_status:'MODEL_NOT_CALLED',
    quota_consumed:false, provider_attempted:false,
    answer:'Cuộc trò chuyện này chưa được gắn bản ngữ cảnh dự án đã duyệt. Không có nội dung riêng nào được nạp vào câu trả lời này. Đây là trạng thái đọc từ máy chủ, không phải phản hồi của mô hình AI.'
  };
  const reviewed = new Date(bridge.reviewed_at).toLocaleString('vi-VN',{timeZone:'Asia/Ho_Chi_Minh'});
  const status = `Hội thoại này đã được gắn bản ngữ cảnh chuyển từ dự án.\nPhiên bản: ${bridge.version}.\nThời điểm duyệt: ${reviewed} (giờ Việt Nam).`;
  const boundary = 'Đây là thông tin đọc trực tiếp từ bản ghi máy chủ, không phải câu trả lời mới của mô hình AI. Chỉ các nội dung đã chuyển và duyệt có trong bản này; chưa tự đồng bộ nguyên văn từng tin nhắn mới của ChatGPT. Bản ngữ cảnh không phải dữ liệu thị trường hiện tại.';
  return {
    status:'READY', mode:'PROJECT_CONTEXT_ONLY', scope:'conversation',
    answer_engine:'PROJECT_HANDOFF_RECORD', model_status:'MODEL_NOT_CALLED',
    quota_consumed:false, provider_attempted:false,
    answer:intent === 'SUMMARY' ? `${status}\n\nBẢN NGỮ CẢNH ĐÃ CHUYỂN — KHÔNG PHẢI TIN NHẮN NGUYÊN VĂN\n${bridge.summary}\n\n${boundary}` : `${status}\n\n${boundary}`
  };
}

export function knowledgeProviderFailure({kind='',status=0,payload=null}={}) {
  const code = String(payload?.error?.code || payload?.error?.type || '').toUpperCase();
  const http = Number.isInteger(status) && status>=100 && status<=599 ? status : 0;
  let reason='OPENAI_RESPONSE_INVALID', model_status='MODEL_ERROR';
  let explanation='Mô hình AI chưa tạo được câu trả lời hợp lệ cho câu hỏi này.';
  if (kind==='MISSING_KEY') {
    reason='OPENAI_KEY_MISSING'; explanation='Mô hình AI chưa được cấu hình khóa truy cập dịch vụ.';
  } else if (kind==='TIMEOUT') {
    reason='OPENAI_TIMEOUT';model_status='MODEL_TIMEOUT'; explanation='Yêu cầu tới mô hình AI đã hết thời gian chờ.';
  } else if (kind==='NETWORK') {
    reason='OPENAI_NETWORK_ERROR'; explanation='Chưa kết nối được tới dịch vụ mô hình AI.';
  } else if (http===429 && /CREDIT|QUOTA|BALANCE/.test(code) && code!=='RATE_LIMIT_EXCEEDED') {
    reason='OPENAI_429_QUOTA_EXHAUSTED';model_status='MODEL_CREDIT_BLOCKED';
    explanation='Dịch vụ mô hình AI trả lỗi hết tín dụng hoặc hạn mức API. Đây không phải hết lượt hỏi của tài khoản StockRadar.';
  } else if (http===429) {
    reason='OPENAI_429_RATE_LIMITED'; explanation='Dịch vụ mô hình AI đang giới hạn tốc độ yêu cầu. Đây không phải kết luận rằng đã hết tín dụng API.';
  } else if (http===401) {
    reason='OPENAI_401_AUTHENTICATION_FAILED'; explanation='Dịch vụ mô hình AI chưa chấp nhận cấu hình xác thực.';
  } else if (http===403 || http===404) {
    reason=`OPENAI_${http}_ACCESS_UNAVAILABLE`; explanation='Mô hình hoặc quyền truy cập API đang cấu hình chưa khả dụng.';
  } else if (http>=500) {
    reason=`OPENAI_${http}_SERVICE_ERROR`; explanation='Dịch vụ mô hình AI đang gặp lỗi máy chủ.';
  } else if (http>=400) {
    reason=`OPENAI_${http}_REQUEST_FAILED`; explanation='Dịch vụ mô hình AI chưa chấp nhận yêu cầu hiện tại.';
  } else if (payload?.status==='incomplete') {
    reason='OPENAI_RESPONSE_INCOMPLETE'; explanation='Mô hình AI trả về câu trả lời chưa hoàn tất; hệ thống không công bố nội dung dở dang.';
  }
  return {reason,model_status,provider_http_status:http||null,provider_attempted:kind!=='MISSING_KEY',
    answer:`${explanation}\n\nNội dung và ngữ cảnh hội thoại đã lưu trước đó vẫn được giữ lại. Phản hồi này chỉ thông báo trạng thái, không thay thế câu trả lời phân tích.`};
}
