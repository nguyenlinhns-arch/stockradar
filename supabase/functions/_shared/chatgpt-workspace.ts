// Default is no billable inference. API mode requires an explicit server-side opt-in.
// Production uses this default; deployment wrappers do not mutate runtime environment values.
export function chatGPTWorkspaceMode(env) {
  return env?.get?.('STOCKRADAR_INFERENCE_MODE') !== 'API';
}
export function chatGPTWorkspaceHandoff(message, horizon = 'SHORT_TERM') {
  const question = String(message || '').replace(/[\u0000-\u001f\u007f]/g,' ').trim().slice(0,2000);
  const prompt = `Phân tích theo phương pháp StockRadar, chỉ cổ phiếu HOSE.\nYêu cầu của tôi: ${question}\nKhung thời gian: ${String(horizon || 'SHORT_TERM').slice(0,30)}.\nDùng 4M/Payback, CANSLIM, định giá Bear/Base/Bull, SEPA/VCP, VPA và quản trị rủi ro. Kiểm tra nguồn và thời điểm dữ liệu; không dùng trí nhớ làm giá hiện tại. Khi thiếu dữ liệu, ghi rõ phần thiếu; không tự đặt giá mua, stop, target hoặc xác suất.\nGói này chỉ chứa câu hỏi, chưa kèm dữ liệu thị trường và không phải khuyến nghị. Trong Project StockRadar có kết nối dữ liệu, hãy đọc dữ liệu qua kết nối được cấp quyền trước khi phân tích.`;
  return {
    status:'HANDOFF_READY',mode:'CHATGPT_WORKSPACE',execution_mode:'CHATGPT_WORKSPACE',
    answer_engine:'CHATGPT_HANDOFF',model_status:'MODEL_NOT_CALLED',model_notice:null,
    provider_attempted:false,quota_consumed:false,generated_analysis:false,
    conversation_persisted:false,public_action_allowed:false,
    answer:'StockRadar đã chuyển sang phân tích trong ChatGPT. Website không gọi thêm OpenAI API cho yêu cầu này. Mở ChatGPT bằng tài khoản của bạn để phân tích; kết quả chỉ được lưu về StockRadar khi bạn yêu cầu.',
    handoff:{url:'https://chatgpt.com/',prompt,includes_market_data:false,includes_private_history:false,automatic_chatgpt_sync:false},
  };
}
