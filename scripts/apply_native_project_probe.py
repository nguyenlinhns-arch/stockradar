"""Mount only a public static MCP probe; all existing guest behavior is byte-preserved."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
P=ROOT/'supabase/functions/stock-ai-guest/index.ts'
ANCHOR='Deno.serve(async req=>{\n'
PATCH='''  // NATIVE_PROJECT_PROBE_V1: public static test UI; no queue, auth data or model calls.
  if (/\\/native-probe\\/(mcp|health)$/.test(new URL(req.url).pathname)) {
    const { handleNativeProbe } = await import("../_shared/native-probe/index.ts");
    return await handleNativeProbe(req);
  }
'''
s=P.read_text()
if 'NATIVE_PROJECT_PROBE_V1' not in s:
 if s.count(ANCHOR)!=1:raise RuntimeError('GUEST_SOURCE_DRIFT')
 s=s.replace(ANCHOR,ANCHOR+PATCH,1);P.write_text(s)
html=(ROOT/'supabase/functions/_shared/native-probe/widget.html').read_text()
(ROOT/'supabase/functions/_shared/native-probe/widget.ts').write_text('// Generated from reviewed widget.html; no remote fetch.\nexport default '+json.dumps(html,ensure_ascii=False)+';\n')
print('Mounted bounded public UI probe; existing guest auth/origin/no-API logic unchanged.')
