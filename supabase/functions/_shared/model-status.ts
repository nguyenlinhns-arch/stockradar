// CHATGPT_WORKSPACE_NO_API_V1
export function modelStatus(body: Record<string, any>) {
  if (body.mode === 'METHOD_ONLY') return 'MODEL_NOT_CALLED';
  const reason = String(body.reason || '');
  if (/CREDIT|BALANCE|INSUFFICIENT_QUOTA|CIRCUIT_OPEN/.test(reason)) return 'MODEL_CREDIT_BLOCKED';
  if (/TIMEOUT/.test(reason)) return 'MODEL_TIMEOUT';
  if (body.status === 'READY' && String(body.answer_engine || '').startsWith('MODEL_')) return 'MODEL_READY';
  return 'MODEL_ERROR';
}

export function withModelStatus(body: Record<string, any>) {
  if (body.mode === "CHATGPT_WORKSPACE") return {...body,model_status:"MODEL_NOT_CALLED",model_notice:null};
  if (!body.answer_engine) return body;
  const status = modelStatus(body);
  // Operational state only: no question, conversation, portfolio, identity, or provider body.
  console.info(JSON.stringify({component: 'stockradar-model', status}));
  const notices: Record<string, string> = {
    MODEL_NOT_CALLED: 'Chưa đủ dữ liệu để dùng mô hình phân tích. Nội dung bên dưới là giải thích phương pháp có sẵn.',
    MODEL_CREDIT_BLOCKED: 'Mô hình AI đang tạm gián đoạn do hạn mức dịch vụ. Bên dưới là dữ liệu tham chiếu của StockRadar, chưa phải câu trả lời từ mô hình AI.',
    MODEL_TIMEOUT: 'Mô hình AI phản hồi quá chậm. Bên dưới là dữ liệu tham chiếu; bạn có thể thử lại sau.',
    MODEL_ERROR: 'Mô hình AI chưa trả lời được. Bên dưới là dữ liệu tham chiếu của StockRadar.',
  };
  return {...body, model_status: status, model_notice: notices[status] || null};
}
