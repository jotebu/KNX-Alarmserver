// Run with: node --test tests/dashboard_polling.cjs (no npm dependencies).
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
function setup(fetch){
  let id=0;const timers=new Map(),nodes=new Map();
  const document={hidden:false,getElementById(key){if(!nodes.has(key))nodes.set(key,{hidden:false,textContent:''});return nodes.get(key);}};
  const context=vm.createContext({document,fetch,AbortController,Date,JSON,Error,Math,encodeURIComponent,
    setTimeout(fn,ms){timers.set(++id,{fn,ms});return id;},clearTimeout(key){timers.delete(key);}});
  const prefix=source.slice(0,source.indexOf('function failure('));
  const refresh=source.slice(source.indexOf('async function refresh(){'),source.indexOf('let settingsOpen='));
  vm.runInContext(prefix+"\nlet settingsOpen=false;function applyAccess(){}function render(){}function failure(error){$('error').textContent=error.message;}\n"+refresh,context);
  return {context,timers,nodes,run:code=>vm.runInContext(code,context)};
}
const snapshot=()=>({status:{version:'test',user:'admin',knx:{enabled:false,ready:false,connections:[]}},alarms:[]});
test('stalled fetch times out, releases busy and retries with backoff without overlap',async()=>{
  let calls=0,healthy=false;
  const s=setup(async(url,{signal})=>{calls++;if(healthy)return {ok:true,json:async()=>snapshot()};return await new Promise((resolve,reject)=>signal.addEventListener('abort',()=>reject(new Error('aborted'))));});
  const first=s.run('refresh()');await s.run('refresh()');assert.equal(calls,1);
  const deadline=[...s.timers.values()].find(t=>t.ms===10000);assert.ok(deadline);deadline.fn();await first;
  assert.equal(s.run('busy'),false);assert.match(s.nodes.get('error').textContent,/10 Sekunden/);
  assert.ok([...s.timers.values()].some(t=>t.ms===10000));
  healthy=true;await s.run('refresh()');assert.equal(calls,2);assert.equal(s.run('refreshFailures'),0);
  assert.ok([...s.timers.values()].some(t=>t.ms===5000));
});
test('timeout includes stalled response body, and writes get no automatic retry',async()=>{
  let signal,calls=0,bodyStarted;const bodyReady=new Promise(resolve=>{bodyStarted=resolve;});
  const s=setup(async(url,options)=>{calls++;signal=options.signal;return {ok:true,json:()=>new Promise((resolve,reject)=>{signal.addEventListener('abort',()=>reject(new Error('body stalled')));bodyStarted();})};});
  const result=s.run("api('/api/knx/config',{method:'PUT'})");const rejected=assert.rejects(result,/30 Sekunden/);
  await bodyReady;[...s.timers.values()].find(t=>t.ms===30000).fn();await rejected;assert.equal(calls,1);assert.equal(s.timers.size,0);
});
test('hidden page pauses polling and repeated failures have a bounded backoff',async()=>{
  const s=setup(async()=>{throw new Error('network down');});
  for(let i=0;i<5;i++)await s.run('refresh()');
  assert.ok([...s.timers.values()].some(t=>t.ms===30000));
  s.run('document.hidden=true;scheduleRefresh()');assert.equal(s.timers.size,0);
});
test('one dashboard request per refresh includes only selected view',async()=>{
  const urls=[];const s=setup(async url=>{urls.push(url);return {ok:true,json:async()=>({...snapshot(),history:[]})};});
  s.run("view='history'");await s.run('refresh()');assert.deepEqual(urls,['/api/dashboard?view=history']);assert.equal(s.timers.size,1);
});
