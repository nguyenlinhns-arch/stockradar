import {test} from 'node:test';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
const {number,state,selectRows,validate}=createRequire(import.meta.url)('../../website/assets/live-radar-v1.js');
const rows=[
 {ticker:'AAA',sector:'A',fresh:true,research_ready:true,initial_setup:false,new_buy_allowed:false,score:60,scores:{technical:70,flow:65},technical:{change_pct:0}},
 {ticker:'BBB',sector:'B',fresh:true,research_ready:true,initial_setup:true,new_buy_allowed:false,score:80,scores:{technical:60,flow:70},technical:{change_pct:2}},
 {ticker:'L10',sector:'A',fresh:true,research_ready:false,initial_setup:true,new_buy_allowed:false,score:null,scores:{technical:99}},
 {ticker:'DDD',sector:'A',fresh:false,research_ready:false,initial_setup:false,new_buy_allowed:true,score:null},
];
test('research sort keeps incomplete rows out of rankings and supports all HOSE lookup',()=>{
 assert.deepEqual(selectRows(rows).map(r=>r.ticker),['BBB','AAA']);
 assert.deepEqual(selectRows(rows,{filter:'all',sort:'technical'}).map(r=>r.ticker),['AAA','BBB','DDD','L10']);
 assert.deepEqual(selectRows(rows,{filter:'all',search:'l10'}).map(r=>r.ticker),['L10']);
 assert.deepEqual(rows.map(r=>r.ticker),['AAA','BBB','L10','DDD']);
});
test('initial technical signs cannot become confirmed buy recommendations',()=>{
 assert.equal(selectRows(rows,{filter:'initial'}).length,2);
 assert.equal(selectRows(rows,{filter:'buy'}).length,0);
 assert.equal(state(rows[1]),'Có dấu hiệu ban đầu');
 assert.equal(state(rows[2]),'Dấu hiệu · thiếu dữ liệu');
 assert.equal(state(rows[3]),'Dữ liệu cũ');
});
test('combined sector, ticker and state filters respect the same observations',()=>{
 assert.deepEqual(selectRows(rows,{filter:'all',sector:'A',sort:'ticker'}).map(r=>r.ticker),['AAA','DDD','L10']);
 assert.equal(selectRows(rows,{filter:'ready',search:'BBB',sector:'A'}).length,0);
});
test('missing values stay missing and a real zero remains zero',()=>{
 for(const v of [null,undefined,'',' ',[],{},false,'oops'])assert.equal(number(v),null);
 assert.equal(number(0),0);assert.equal(number('0'),0);
});
test('Radar rejects action-only feeds and unknown authorization flags',()=>{
 assert.throws(()=>validate({schema_version:'STOCKRADAR_VERIFIED_HISTORY_V1',items:rows}));
 assert.throws(()=>validate({schema_version:'STOCKRADAR_RESEARCH_RADAR_V1',mode:'RESEARCH_SCREEN',items:[{...rows[0],new_buy_allowed:'true'}]}));
 assert.equal(validate({schema_version:'STOCKRADAR_RESEARCH_RADAR_V1',mode:'RESEARCH_SCREEN',items:rows}).items.length,4);
});
