const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
process.env.TZ='Europe/Berlin';
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
function setup(){
 const errors=[];let calls=0;
 const ctx=vm.createContext({window:{location:{pathname:'/'}},Date,Math,encodeURIComponent,refresh(){calls++;},failure(error){errors.push(error.message);}});
 vm.runInContext(source.slice(0,source.indexOf('async function api(')),ctx);
 vm.runInContext(source.slice(source.indexOf('function applyListDateRange('),source.indexOf('const dateRangePicker=')),ctx);
 return {ctx,errors,calls:()=>calls,run:code=>vm.runInContext(code,ctx)};
}
test('common date range includes the full local end day and retains the status filter',()=>{
 const s=setup();s.run("alarmStatusFilter='closed';applyListDateRange('2026-10-21','2026-10-21')");
 assert.equal(s.run('listFilters.from'),'2026-10-20T22:00:00.000Z');
 assert.equal(s.run('listFilters.until'),'2026-10-21T22:00:00.000Z');
 assert.equal(s.calls(),1);assert.match(s.run("listQuery('alarms')"),/status_filter=closed/);
 s.run("applyListDateRange('','')");assert.equal(s.run('listFilters.from'),'');assert.equal(s.run('listFilters.until'),'');assert.equal(s.run('alarmStatusFilter'),'closed');assert.equal(s.calls(),2);
});
test('local calendar days include 23-hour and 25-hour daylight-saving transitions',()=>{
 const s=setup();
 for(const [day,hours] of [['2026-03-29',23],['2026-10-25',25]]){
  const bounds=s.run(`dateRangeBounds('${day}','${day}')`);
  assert.equal((Date.parse(bounds.until)-Date.parse(bounds.from))/3600000,hours);
 }
});
test('invalid, incomplete or reversed dates cannot replace an applied filter or request data',()=>{
 const s=setup();s.run("applyListDateRange('2026-12-31','2027-01-01')");const before=s.run('JSON.stringify(listFilters)');
 for(const [from,until] of [['2026-10-22','2026-10-21'],['2026-02-30','2026-03-02'],['2026-13-01','2027-01-01'],['2026-01-01',''],['','2026-01-01'],['invalid','2026-01-01']]){
  s.run(`applyListDateRange('${from}','${until}')`);assert.equal(s.run('JSON.stringify(listFilters)'),before);
 }
 assert.equal(s.calls(),1);assert.equal(s.errors.length,6);
});
