import { McpServer } from 'npm:@modelcontextprotocol/sdk@1.26.0/server/mcp.js';
import { WebStandardStreamableHTTPServerTransport } from 'npm:@modelcontextprotocol/sdk@1.26.0/server/webStandardStreamableHttp.js';
import { createClient } from 'npm:@supabase/supabase-js@2.95.0';
import widget from './widget.ts';

const URI='ui://stockradar/native-project-queue-trigger-v3.html';
const V2_URI='ui://stockradar/native-project-queue-trigger-v2.html';
const LEGACY_URI='ui://stockradar/native-message-probe-v1.html';
const MIME='text/html;profile=mcp-app';
const SUPABASE_ORIGIN='https://xamviatbxufjlpiwhebb.supabase.co';
const HEADERS={'cache-control':'no-store','x-content-type-options':'nosniff','access-control-allow-origin':'*','access-control-allow-headers':'content-type,accept,mcp-protocol-version,mcp-session-id','access-control-allow-methods':'GET,POST,OPTIONS'};
function json(body:unknown,status=200){return new Response(JSON.stringify(body),{status,headers:{...HEADERS,'content-type':'application/json; charset=utf-8'}});}
function resource(uri:string){return {contents:[{uri,mimeType:MIME,text:widget,_meta:{ui:{prefersBorder:true,csp:{connectDomains:[SUPABASE_ORIGIN],resourceDomains:[]}},'openai/widgetDescription':'Owner-initiated StockRadar Project queue watcher. The widget receives only a boolean pending signal; it never reads website questions, account data, claim tokens or private history and calls no separate model API.'}}]};}

async function pendingSignal(){
  const url=Deno.env.get('SUPABASE_URL')||'';
  const key=Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')||'';
  if(!url||!key)return {pending:false,signal_version:'PENDING_BOOL_V1',available:false};
  const db=createClient(url,key,{auth:{persistSession:false,autoRefreshToken:false}});
  const {data,error}=await db.rpc('stockradar_native_probe_signal');
  if(error)return {pending:false,signal_version:'PENDING_BOOL_V1',available:false};
  return {pending:data?.pending===true,signal_version:'PENDING_BOOL_V1',available:true};
}

function createServer(){
 const server=new McpServer({name:'stockradar-native-probe',version:'0.3.1'});
 server.registerResource('native-project-queue-trigger',URI,{mimeType:MIME},async()=>resource(URI));
 server.registerResource('native-project-queue-trigger-v2',V2_URI,{mimeType:MIME},async()=>resource(V2_URI));
 server.registerResource('native-probe-widget-legacy',LEGACY_URI,{mimeType:MIME},async()=>resource(LEGACY_URI));
 server.registerTool('show_stockradar_native_probe',{title:'Mở cầu nối Native StockRadar',description:'Use this when the owner asks to link or continuously process StockRadar website questions in the current ChatGPT Project. It renders a watcher that sees only a boolean pending signal. Website question content remains in Supabase and is read by the authorized Project connector after the native message enters this conversation.',inputSchema:{},annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false,idempotentHint:true},_meta:{ui:{resourceUri:URI},'openai/outputTemplate':URI,'openai/toolInvocation/invoking':'Mở cầu nối Project','openai/toolInvocation/invoked':'Cầu nối Native đã mở'}},async()=>({structuredContent:{test:'native_project_queue_trigger',state:'READY_TO_ENABLE',native_queue_trigger_ready:true,website_queue_data_read_by_app:false,pending_signal_only:true,uses_model_api:false},content:[{type:'text',text:'Đã mở cầu nối Native. Widget chỉ nhận tín hiệu có/không có câu hỏi chờ; nội dung câu hỏi vẫn chỉ được đọc trong Project qua Supabase đã cấp quyền.'}]}));
 return server;
}

Deno.serve(async req=>{
 const url=new URL(req.url);
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers:HEADERS});
 if(req.method==='GET'&&url.pathname.endsWith('/signal'))return json(await pendingSignal());
 if(req.method==='GET'&&url.pathname.endsWith('/health'))return json({service:'stockradar-native-probe',status:'QUEUE_WATCH_READY',model_api_used:false,question_data_exposed:false,pending_signal_only:true,native_queue_trigger_ready:true,legacy_resource_supported:true});
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
