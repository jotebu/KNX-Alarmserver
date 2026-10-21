const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
process.env.TZ='Europe/Berlin';
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
function setup(){
 const nodes=new Map(),errors=[];let calls=0;
 const get=id=>{if(!nodes.has(id))nodes.set(id,{value:'',checked:true});return nodes.get(id);};
 const ctx=vm.createContext({window:{location:{pathname:'/'}},document:{getElementById:get},Date,Math,encodeURIComponent,setTimeout(){},clearTimeout(){},refresh(){calls++;},failure(error){errors.push(error.message);},render(){}});
 vm.runInContext(source.slice(0,source.indexOf('async function api(')),ctx);
 vm.runInContext(source.slice(source.indexOf('let searchTimer='),source.indexOf("document.addEventListener('visibilitychange'")),ctx);
 return {get,ctx,errors,calls:()=>calls};
}
test('date range includes the full local end day and filters search the full list',()=>{
 const s=setup();s.get('date-from').value='2026-10-21';s.get('date-until').value='2026-10-21';s.get('search').value='Pumpe';
 vm.runInContext('applyListFilters()',s.ctx);
 assert.equal(vm.runInContext('listFilters.from',s.ctx),'2026-10-20T22:00:00.000Z');
 assert.equal(vm.runInContext('listFilters.until',s.ctx),'2026-10-21T22:00:00.000Z');
 assert.equal(s.calls(),1);
 const query=vm.runInContext("listQuery('alarms')",s.ctx);assert.match(query,/list_mode=true&search=Pumpe/);
 s.get('date-from').value='2026-10-22';vm.runInContext('applyListFilters()',s.ctx);
 assert.equal(s.calls(),1);assert.match(s.errors[0],/Von/);
});
test('filters start collapsed, toggle without requests and reset clears dates',()=>{
 const s=setup();assert.equal(vm.runInContext('filtersOpen',s.ctx),false);
 s.get('filter-toggle').onclick();assert.equal(vm.runInContext('filtersOpen',s.ctx),true);assert.equal(s.calls(),0);
 s.get('filter-toggle').onclick();assert.equal(vm.runInContext('filtersOpen',s.ctx),false);
 s.get('date-from').value='2026-10-21';s.get('date-until').value='2026-10-22';s.get('date-clear').onclick();
 assert.equal(s.get('date-from').value,'');assert.equal(s.get('date-until').value,'');assert.equal(s.calls(),1);
});
