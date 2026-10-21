const {test}=require('node:test');
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
function setup(result,fails=false){
 const flags=new Set(),link={title:'Versionshistorie öffnen',classList:{toggle(name,value){if(value)flags.add(name);else flags.delete(name);}}};
 const ctx=vm.createContext({$:()=>link,api:async()=>{if(fails)throw Error('offline');return result;}});
 vm.runInContext(source.slice(source.indexOf('function renderVersionCheck('),source.indexOf('async function loadVersions(')),ctx);
 return {link,flags,run:()=>vm.runInContext('checkVersion()',ctx)};
}
test('version link is red only for a confirmed newer version',async()=>{
 for(const result of [{check_ok:true,update_available:true},{check_ok:true,update_available:false},{check_ok:false,update_available:false}]){
  const s=setup({...result,current_version:'0.10.10',latest_version:'0.10.11'});await s.run();
  assert.equal(s.flags.has('update-available'),result.check_ok&&result.update_available);
  assert.equal(s.link.textContent,'Version 0.10.10');assert.doesNotMatch(s.link.title,/nicht möglich|fehlgeschlagen/);
 }
});
test('unreachable version service leaves normal styling and no failure notice',async()=>{
 const s=setup(null,true);await s.run();assert.equal(s.flags.has('update-available'),false);assert.equal(s.link.title,'Versionshistorie öffnen');
});

test('update button requires a confirmed newer version, installed helper and idle updater',async()=>{
 for(const [state,disabled] of [
  [{available:true,check_ok:true,update_available:true,state:'idle'},false],
  [{available:true,check_ok:true,update_available:false,state:'idle'},true],
  [{available:true,check_ok:false,update_available:true,state:'idle'},true],
  [{available:false,check_ok:true,update_available:true,state:'idle'},true],
  [{available:true,check_ok:true,update_available:true,state:'installing'},true]]){
  const nodes=new Map();
  const ctx=vm.createContext({$:id=>{if(!nodes.has(id))nodes.set(id,{});return nodes.get(id);},api:async()=>state,setTimeout:()=>0,clearTimeout(){},date:()=>''});
  vm.runInContext(source.slice(source.indexOf('let updatePoll=null;'),source.indexOf("$('update-start').onclick=")),ctx);
  await vm.runInContext('loadUpdate()',ctx);
  assert.equal(nodes.get('update-start').disabled,disabled);
 }
});
