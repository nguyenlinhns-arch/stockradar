import { McpServer } from 'npm:@modelcontextprotocol/sdk@1.26.0/server/mcp.js';
import { WebStandardStreamableHTTPServerTransport } from 'npm:@modelcontextprotocol/sdk@1.26.0/server/webStandardStreamableHttp.js';
import { createClient } from 'npm:@supabase/supabase-js@2.95.0';
import widget from './widget.ts';

const VERSION='0.4.0';
const URI='ui://stockradar/native-project-queue-trigger-v4.html';
const LEGACY_URIS=['ui://stockradar/native-project-queue-trigger-v3.html','ui://stockradar/native-project-queue-trigger-v2.html','ui://stockradar/native-message-probe-v1.html'];
const MIME='text/html;profile=mcp-app';
const SUPABASE_ORIGIN='https://xamviatbxufjlpiwhebb.supabase.co';
const HEADERS={'cache-control':'no-store','x-content-type-options':'nosniff','access-control-allow-origin':'*','access-control-allow-headers':'content-type,accept,mcp-protocol-version,mcp-session-id','access-control-allow-methods':'GET,POST,OPTIONS'};
function json(body:unknown,status=200){return new Response(JSON.stringify(body),{status,headers:{...HEADERS,'content-type':'application/json; charset=utf-8'}});}
function resource(uri:string){return {contents:[{uri,mimeType:MIME,text:widget,_meta:{ui:{prefersBorder:true,csp:{connectDomains:[SUPABASE_ORIGIN],resourceDomains:[]}},'openai/widgetDescription':'Owner-initiated StockRadar Project queue watcher, version 0.4.0. It receives only the existing boolean pending signal, never website question content, credentials or history. Opening this card is not proof that a native message or website answer was delivered.'}}]};}

async function pendingSignal(){
 const unavailable={pending:false,signal_version:'PENDING_BOOL_V1',available:false};
 const url=Deno.env.get('SUPABASE_URL')||'',key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
 if(!url||!key)return unavailable;
 try{
  const db=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data,error}=await db.rpc('stockradar_native_probe_signal');
  if(error||typeof data?.pending!=='boolean')return unavailable;
  return {pending:data.pending,signal_version:'PENDING_BOOL_V1',available:true};
 }catch{return unavailable;}
}
function createServer(){
 const server=new McpServer({name:'stockradar-native-probe',version:VERSION});
 server.registerResource('native-project-queue-trigger',URI,{mimeType:MIME},async()=>resource(URI));
 LEGACY_URIS.forEach((uri,i)=>server.registerResource('native-project-queue-trigger-legacy-'+i,uri,{mimeType:MIME},async()=>resource(uri)));
 server.registerTool('show_stockradar_native_probe',{title:'Mở cầu nối Native StockRadar',description:'Use when the owner asks to link or test StockRadar website questions in the current ChatGPT Project. Renders an inactive card. The owner may explicitly send one queue-check follow-up or enable a visible-card boolean-signal watcher. The widget does not read website question content or prove automatic answers work; authorized Project tools perform that work separately.',inputSchema:{},annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false,idempotentHint:true},_meta:{ui:{resourceUri:URI},'openai/outputTemplate':URI,'openai/toolInvocation/invoking':'Mở cầu nối Project','openai/toolInvocation/invoked':'Thẻ cầu nối sẵn sàng, chưa bật'}},async()=>({structuredContent:{test:'native_project_queue_trigger',version:VERSION,state:'READY_TO_ENABLE',native_queue_trigger_ready:true,current_conversation_verified:false,website_delivery_verified:false,website_queue_data_read_by_app:false,pending_signal_only:true,uses_model_api:false},content:[{type:'text',text:'Đã mở thẻ cầu nối 0.4.0, chưa tự gửi tin nhắn. Chủ tài khoản có thể bấm kiểm tra một yêu cầu hoặc bật theo dõi tín hiệu. Chưa xác minh lượt native hay câu trả lời trên website.'}]}));
 return server;
}
Deno.serve(async req=>{
 const url=new URL(req.url);
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers:HEADERS});
 if(req.method==='GET'&&url.pathname.endsWith('/signal')){const signal=await pendingSignal();return json(signal,signal.available?200:503);}
 if(req.method==='GET'&&url.pathname.endsWith('/health'))return json({service:'stockradar-native-probe',version:VERSION,status:'WIDGET_READY_HOST_UNVERIFIED',model_api_used:false,question_data_exposed:false,pending_signal_only:true,native_queue_trigger_ready:true,current_conversation_verified:false,website_delivery_verified:false,legacy_resource_supported:true});
 if(!url.pathname.endsWith('/mcp'))return json({error:'NOT_FOUND'},404);
 if(req.method!=='POST')return json({error:'METHOD_NOT_ALLOWED'},405);
 if(!(req.headers.get('content-type')||'').toLowerCase().startsWith('application/json'))return json({error:'JSON_REQUIRED'},415);
 let raw='';
 try{const bytes=new Uint8Array(await req.arrayBuffer());if(bytes.byteLength>16384)return json({error:'REQUEST_TOO_LARGE'},413);raw=new TextDecoder().decode(bytes);JSON.parse(raw);}catch{return json({error:'INVALID_JSON'},400);}
 const server=createServer(),transport=new WebStandardStreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
 try{await server.connect(transport);const r=await transport.handleRequest(new Request(req.url,{method:'POST',headers:req.headers,body:raw}));const body=await r.arrayBuffer();const h=new Headers(r.headers);for(const[k,v]of Object.entries(HEADERS))h.set(k,v);return new Response(body.byteLength?body:null,{status:r.status,headers:h});}
 catch{return json({error:'MCP_PROBE_UNAVAILABLE'},503);}
 finally{await server.close().catch(()=>{});}
});
