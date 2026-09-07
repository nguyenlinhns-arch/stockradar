// Isolated, public static UI capability probe. No DB client, auth data or model API.
// Mounted only on /stock-ai-guest/native-probe/*; the existing guest policy is unchanged.
import { McpServer } from 'npm:@modelcontextprotocol/sdk@1.26.0/server/mcp.js';
import { WebStandardStreamableHTTPServerTransport } from 'npm:@modelcontextprotocol/sdk@1.26.0/server/webStandardStreamableHttp.js';
import widget from './widget.ts';
const URI='ui://stockradar/native-message-probe-v1.html';
const MIME='text/html;profile=mcp-app';
const headers={'content-type':'application/json; charset=utf-8','cache-control':'no-store','x-content-type-options':'nosniff','access-control-allow-origin':'*','access-control-allow-headers':'content-type,accept,mcp-protocol-version,mcp-session-id','access-control-allow-methods':'GET,POST,OPTIONS'};
function json(body,status=200){return new Response(JSON.stringify(body),{status,headers});}
function createServer(){
 const server=new McpServer({name:'stockradar-native-probe',version:'0.1.0'});
 server.registerResource('native-probe-widget',URI,{mimeType:MIME},async()=>({contents:[{uri:URI,mimeType:MIME,text:widget,_meta:{ui:{prefersBorder:true,csp:{connectDomains:[],resourceDomains:[]}},'openai/widgetDescription':'An opt-in single-message capability test. No website questions, accounts or chat history are read.'}}]}));
 server.registerTool('show_stockradar_native_probe',{
  title:'Mở phép thử nhắn trực tiếp trong hội thoại',
  description:'Use this when the user asks to test whether a StockRadar component can send one explicitly consented follow-up in the current ChatGPT conversation. This only renders an isolated test interface. It does not read website data, process the queue, or prove automatic replies work. No input is needed.',
  inputSchema:{},annotations:{readOnlyHint:true,destructiveHint:false,openWorldHint:false,idempotentHint:true},
  _meta:{ui:{resourceUri:URI},'openai/outputTemplate':URI,'openai/toolInvocation/invoking':'Mở phép thử kết nối','openai/toolInvocation/invoked':'Phép thử đang chờ người dùng bật'}
 },async()=>({structuredContent:{test:'native_message_probe',state:'USER_OPT_IN_REQUIRED',native_model_reply_verified:false,website_queue_connected:false,uses_model_api:false},content:[{type:'text',text:'Đã mở giao diện kiểm thử. Chưa gửi tin nhắn. Người dùng cần bật và bấm Gửi thử một tin sau 3 giây. Chỉ khi ChatGPT tạo một lượt nhắn mới và trả lời mã kiểm thử mới có bằng chứng về lượt xử lý; công cụ này chưa xác nhận điều đó.'}]}));
 return server;
}
export async function handleNativeProbe(req){
 const url=new URL(req.url);
 if(!/\/native-probe\/(mcp|health)$/.test(url.pathname))return json({error:'NOT_FOUND'},404);
 if(req.method==='OPTIONS')return new Response(null,{status:204,headers});
 if(req.method==='GET'&&url.pathname.endsWith('/health'))return json({service:'stockradar-native-probe',status:'PROBE_READY',model_api_used:false,database_access:false,native_model_reply_verified:false});
 if(!url.pathname.endsWith('/mcp'))return json({error:'NOT_FOUND'},404);
 if(req.method!=='POST')return json({error:'METHOD_NOT_ALLOWED'},405);
 if(!(req.headers.get('content-type')||'').toLowerCase().startsWith('application/json'))return json({error:'JSON_REQUIRED'},415);
 let raw='';
 try{
  const reader=req.body?.getReader();if(!reader)return json({error:'INVALID_JSON'},400);
  const chunks=[];let size=0;
  for(;;){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>8192){await reader.cancel();return json({error:'REQUEST_TOO_LARGE'},413);}chunks.push(value);}
  const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.byteLength;}
  raw=new TextDecoder().decode(bytes);JSON.parse(raw);
 }catch{return json({error:'INVALID_JSON'},400);}
 // Stateless, per-request instance: one visitor cannot receive another client's state.
 const server=createServer(),transport=new WebStandardStreamableHTTPServerTransport({sessionIdGenerator:undefined,enableJsonResponse:true});
 try{
  await server.connect(transport);
  const response=await transport.handleRequest(new Request(req.url,{method:'POST',headers:req.headers,body:raw}));
  const body=await response.arrayBuffer();const finalHeaders=new Headers(response.headers);
  for(const [key,value]of Object.entries(headers))if(key!=='content-type')finalHeaders.set(key,value);
  return new Response(body.byteLength?body:null,{status:response.status,headers:finalHeaders});
 }catch{return json({error:'MCP_PROBE_UNAVAILABLE'},503);}finally{await server.close().catch(()=>{});}
}
