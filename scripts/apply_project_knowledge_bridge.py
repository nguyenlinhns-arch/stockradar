"""One-time, idempotent bridge repair. Abort on source drift; never rewrite secrets."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMPORT = 'import { loadProjectKnowledge, projectKnowledgeInstructions, projectKnowledgeMeta } from "../_shared/stockradar-knowledge.ts";\n'
MARKER = '// PROJECT_KNOWLEDGE_BRIDGE_V2'

def replace_once(text, old, new):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'Expected exactly one source anchor, found {count}: {old[:90]!r}')
    return text.replace(old, new, 1)

def patch_ticker(name):
    path = ROOT / 'supabase/functions' / name / 'index.ts'
    text = path.read_text()
    if MARKER in text:
        return
    text = replace_once(text, 'import { withModelStatus } from "../_shared/model-status.ts";\n', 'import { withModelStatus } from "../_shared/model-status.ts";\n' + IMPORT)
    # Only after account/quota authorization; the client never supplies knowledge content.
    anchor = '  const researchForAnswer=' if name == 'stock-ai' else '  const ready=reportRows.filter'
    if text.count(anchor) != 1:
        raise RuntimeError('Research anchor changed')
    text = text.replace(anchor, f'  {MARKER}\n  const projectKnowledge=await loadProjectKnowledge(db);\n' + anchor, 1)
    text = replace_once(text, '  const base={', '  const base={...projectKnowledgeMeta(projectKnowledge),')
    text = replace_once(text, 'instructions:STOCKRADAR_SYSTEM_CORE,', 'instructions:projectKnowledgeInstructions(STOCKRADAR_SYSTEM_CORE,projectKnowledge),')
    text = replace_once(text, '...base,answer_engine:modelText?', '...base,...projectKnowledgeMeta(projectKnowledge,Boolean(modelText)),answer_engine:modelText?')
    path.write_text(text)

def patch_chat():
    path = ROOT / 'supabase/functions/stock-ai-chat/index.ts'
    text = path.read_text()
    if MARKER in text:
        return
    text = replace_once(text, 'import { createClient } from "npm:@supabase/supabase-js@2.95.0";\n', 'import { createClient } from "npm:@supabase/supabase-js@2.95.0";\n' + IMPORT + MARKER + '\n')
    start = text.index('async function activeKnowledge(db: any) {')
    end = text.index('\nasync function ensureThread(', start)
    text = text[:start] + 'async function activeKnowledge(db: any) {\n  return await loadProjectKnowledge(db);\n}\n' + text[end:]
    # Retain method-mode behavior; wrap it in the same immutable privacy/data guards.
    start = text.index('  const instructions = `Bạn là StockRadar AI.')
    end = text.index('\n  const context =', start)
    text = text[:start] + '  const instructions = projectKnowledgeInstructions("Bạn là StockRadar AI. Trả lời bằng tiếng Việt rõ ràng, liên tục theo hội thoại. Chỉ giải thích phương pháp cho HOSE; không phân tích Crypto/Coin, HNX hoặc UPCoM. Trong nhánh KNOWLEDGE_ONLY, không có dữ liệu thị trường mới: không công bố giá, Buy Zone, Stop, Target, xác suất hay tín hiệu hành động; số trong lịch sử không phải dữ liệu hiện tại.", knowledge);' + text[end:]
    text = replace_once(text, 'answer_engine:"MODEL_PLUS_KNOWLEDGE_CORE",answer:text', 'answer_engine:"MODEL_PLUS_KNOWLEDGE_CORE",...projectKnowledgeMeta(knowledge,true),answer:text')
    # Do not overwrite the version actually used by stock-ai if activation occurs in flight.
    text = replace_once(text, 'conversation_persisted:upstream.ok && Boolean(result?.answer),knowledge_version:knowledge.version', 'conversation_persisted:upstream.ok && Boolean(result?.answer),knowledge_version:result?.knowledge_version || knowledge.version')
    text = replace_once(text, '},result,knowledge.version);', '},result,result?.knowledge_version || knowledge.version);')
    path.write_text(text)

if __name__ == '__main__':
    paths = [ROOT / 'supabase/functions' / name / 'index.ts' for name in ('stock-ai','stock-ai-guest','stock-ai-chat')]
    original = {p:p.read_text() for p in paths}
    try:
        patch_ticker('stock-ai')
        patch_ticker('stock-ai-guest')
        patch_chat()
    except Exception:
        for p,text in original.items():
            p.write_text(text)
        raise
    status_path = ROOT / 'STOCKRADAR_BUILD_STATUS.md'
    heading = '## Project knowledge bridge — 2026-09-07\n'
    if heading not in status_path.read_text():
        status_path.write_text(status_path.read_text() + '\n' + heading + '\nAll three AI endpoints now load the same reviewed project-knowledge version server-side. Data/Action gates, quotas, payment approval and account ownership are unchanged. This is a reviewed snapshot bridge, not direct or automatic access to ChatGPT project chats. Runtime deploy and live-model verification are tracked separately in `docs/AI_PROJECT_KNOWLEDGE_BRIDGE_20260907.md`.\n')
    print('Project knowledge bridge source updated; no production secrets or client credentials changed.')
