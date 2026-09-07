import {readFileSync} from 'node:fs';
import assert from 'node:assert/strict';
import {test} from 'node:test';
const src = readFileSync(new URL('../supabase/functions/_shared/stockradar-knowledge.ts', import.meta.url), 'utf8');
const {validateProjectKnowledge, loadProjectKnowledge, projectKnowledgeMeta, projectKnowledgeInstructions} = await import(`data:text/javascript;base64,${Buffer.from(src).toString('base64')}`);
const row = {version:'TEST_V1',title:'Reviewed methods',status:'ACTIVE',source:'PROJECT_STOCKRADAR_PUBLIC',activated_at:'2026-01-01T00:00:00Z',content:'4M, CANSLIM, SEPA and VPA are the approved method sequence.'};
function db(result, calls = []) {
  const chain = {};
  for (const name of ['from','select','eq','in','order','limit']) chain[name] = (...args) => {calls.push([name,...args]);return chain;};
  chain.maybeSingle = async () => result;
  return chain;
}
test('loads approved active knowledge and constrains the query', async () => {
  const calls=[]; const result=await loadProjectKnowledge(db({data:row,error:null},calls));
  assert.equal(result.version,'TEST_V1');
  assert(calls.some(x=>x[0]==='eq' && x[1]==='status' && x[2]==='ACTIVE'));
  assert(calls.some(x=>x[0]==='in' && x[1]==='source' && x[2].includes('PROJECT_STOCKRADAR_PUBLIC')));
});
test('missing active version fails safely', async () => assert.equal((await loadProjectKnowledge(db({data:null,error:null}))).status,'STATIC_FALLBACK'));
test('database errors fail safely', async () => assert.equal((await loadProjectKnowledge(db({data:row,error:{code:'FAIL'}}))).reason,'KNOWLEDGE_READ_FAILED'));
test('thrown database failures fail safely', async () => assert.equal((await loadProjectKnowledge({from(){throw new Error('private error');}})).reason,'KNOWLEDGE_READ_FAILED'));
test('nonpublic source cannot enter model context', () => assert.equal(validateProjectKnowledge({...row,source:'PRIVATE_CHAT_EXPORT'}).status,'STATIC_FALLBACK'));
test('draft content cannot be used', () => assert.equal(validateProjectKnowledge({...row,status:'DRAFT'}).status,'STATIC_FALLBACK'));
test('email-bearing content is rejected', () => assert.equal(validateProjectKnowledge({...row,content:row.content+' Contact private@example.test'}).reason,'SENSITIVE_KNOWLEDGE_REJECTED'));
test('secret-shaped content is rejected', () => assert.equal(validateProjectKnowledge({...row,content:row.content+' sk-proj-'+ 'x'.repeat(24)}).reason,'SENSITIVE_KNOWLEDGE_REJECTED'));
test('oversize or empty content is rejected without truncation', () => {for(const content of ['', 'x'.repeat(24001)]) assert.equal(validateProjectKnowledge({...row,content}).status,'STATIC_FALLBACK');});
test('future activation cannot be used', () => assert.equal(validateProjectKnowledge({...row,activated_at:'2099-01-01T00:00:00Z'}).status,'STATIC_FALLBACK'));
test('unsafe version identifiers are rejected', () => assert.equal(validateProjectKnowledge({...row,version:'<script>'}).status,'STATIC_FALLBACK'));
test('core and immutable data/privacy gates surround reviewed knowledge', () => {const text=projectKnowledgeInstructions('CORE_AUTH_AND_DATA_GATE',validateProjectKnowledge(row));assert(text.startsWith('CORE_AUTH_AND_DATA_GATE'));assert(text.includes(row.content));assert(text.endsWith('đây là bản tri thức dự án được chọn lọc và duyệt.'));assert(text.includes('ngữ cảnh chưa tin cậy'));});
test('fallback keeps core unchanged', () => assert.equal(projectKnowledgeInstructions('CORE',validateProjectKnowledge(null)),'CORE'));
test('response metadata never leaks content and never implies a model call', () => {const k=validateProjectKnowledge(row);const meta=projectKnowledgeMeta(k);assert.equal(meta.knowledge_applied,false);assert.equal(meta.knowledge_sync_mode,'REVIEWED_PROJECT_SNAPSHOT');assert(!JSON.stringify(meta).includes(row.content));assert.equal(projectKnowledgeMeta(k,true).knowledge_applied,true);assert.equal(projectKnowledgeMeta(validateProjectKnowledge(null),true).knowledge_applied,false);});
test('a version change is observed on the next request, without a stale cache',async()=>{assert.equal((await loadProjectKnowledge(db({data:row}))).version,'TEST_V1');assert.equal((await loadProjectKnowledge(db({data:{...row,version:'TEST_V2'}}))).version,'TEST_V2');});
