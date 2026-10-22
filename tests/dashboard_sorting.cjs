const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
function setup(){const context=vm.createContext({window:{location:{pathname:'/'}},document:{getElementById:()=>({})},Date,encodeURIComponent});vm.runInContext(source.slice(0,source.indexOf('async function api(')),context);return {run:code=>vm.runInContext(code,context),context};}
function sorted(s,rows,key,direction){s.context.rows=rows;s.context.key=key;s.context.direction=direction;return JSON.parse(s.run('alarmSort=key?{key,direction}:null;JSON.stringify([...rows].sort(compareAlarmRows).map(r=>r.id))'));}
test('priority and occurrence numbers sort numerically; default keeps priority then newest start',()=>{
 const s=setup(),rows=[{id:'a',priority:4,occurrence_id:2,came_at:'2026-01-02'},{id:'b',priority:1,occurrence_id:10,came_at:'2026-01-01'},{id:'c',priority:1,occurrence_id:3,came_at:'2026-01-03'}];
 assert.deepEqual(sorted(s,rows,'priority',1),['c','b','a']);assert.deepEqual(sorted(s,rows,'number',1),['a','c','b']);assert.deepEqual(sorted(s,rows,'number',-1),['b','c','a']);assert.deepEqual(sorted(s,rows,null,1),['c','b','a']);
});
test('all three dates sort chronologically and missing values remain last in both directions',()=>{
 const s=setup();for(const [key,field] of [['came','came_at'],['acknowledged','acknowledged_at'],['went','went_at']]){
  const rows=[{id:'a',[field]:'2026-10-22T12:00:00Z'},{id:'b',[field]:null},{id:'c',[field]:'2026-09-30T12:00:00Z'}];assert.deepEqual(sorted(s,rows,key,1),['c','a','b']);assert.deepEqual(sorted(s,rows,key,-1),['a','c','b']);
 }
});
test('message/state/action columns and unknown occurrence IDs remain sortable',()=>{
 const s=setup();s.run('access.acknowledge=true');const rows=[{id:'a',name:'Pumpe 10',status:'clear_pending',pending:1,occurrence_id:null},{id:'b',name:'Pumpe 2',status:'active',pending:0,occurrence_id:4}];
 assert.deepEqual(sorted(s,rows,'name',1),['b','a']);assert.deepEqual(sorted(s,rows,'status',1),['a','b']);assert.deepEqual(sorted(s,rows,'action',-1),['a','b']);assert.deepEqual(sorted(s,rows,'number',-1),['b','a']);assert.equal(rows[0].id,'a');
});
test('column clicks toggle direction and leave status/date filters unchanged',()=>{
 const s=setup();s.run("let renderCount=0;render=()=>renderCount++;alarmStatusFilter='active';listFilters.from='2026-10-01';sortAlarmColumn('came')");assert.equal(s.run('alarmSort.direction'),-1);s.run("sortAlarmColumn('came')");assert.equal(s.run('alarmSort.direction'),1);assert.equal(s.run('renderCount'),2);assert.equal(s.run('alarmStatusFilter'),'active');assert.equal(s.run('listFilters.from'),'2026-10-01');
});
