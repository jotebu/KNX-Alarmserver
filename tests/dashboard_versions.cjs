const {test}=require('node:test');
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
function setup(result,fails=false){
 const flags=new Set(),link={title:'Versionshistorie öffnen',classList:{toggle(name,value){if(value)flags.add(name);else flags.delete(name);}}};
 const ctx=vm.createContext({page:'/versions',access:{configure:true},newerVersionKnown:false,$:()=>link,api:async()=>{if(fails)throw Error('offline');return result;}});
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
  const ctx=vm.createContext({newerVersionKnown:false,renderVersionCheck(){},$:id=>{if(!nodes.has(id))nodes.set(id,{});return nodes.get(id);},api:async()=>state,setTimeout:()=>0,clearTimeout(){},date:()=>''});
  vm.runInContext(source.slice(source.indexOf('let updatePoll=null;'),source.indexOf("$('update-start').onclick=")),ctx);
  await vm.runInContext('loadUpdate()',ctx);
  assert.equal(nodes.get('update-start').disabled,disabled);
 }
});

test('manual status check gives progress and result; update box is visible only for newer versions',async()=>{
 for(const newer of [false,true]){
  const nodes=new Map();
  const node=()=>({textContent:'',hidden:false,disabled:false,children:[],classList:{toggle(){},remove(){}},setAttribute(){},append(...items){this.children.push(...items);},replaceChildren(...items){this.children=items;}});
  const get=id=>{if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);};
  let resolve,requested;
  const pending=new Promise(r=>resolve=r);
  const ctx=vm.createContext({page:'/versions',access:{configure:true},newerVersionKnown:false,checkingVersionStatus:false,
    $:get,api:async path=>{requested=path;return pending;},date:()=> 'now',Boolean,
    document:{createDocumentFragment:node,createElement:node},text:(tag,value)=>({...node(),textContent:value}),loadUpdate:async()=>{}});
  vm.runInContext(source.slice(source.indexOf('function renderVersionCheck('),source.indexOf('let updatePoll=null;')),ctx);
  const task=vm.runInContext('checkVersionStatus()',ctx);
  assert.equal(get('update-reload').disabled,true);
  assert.match(get('versions-feedback').textContent,/wird geprüft/);
  assert.equal(requested,'/api/versions?refresh=true');
  resolve({check_ok:true,update_available:newer,current_version:'0.10.13',latest_version:newer?'0.10.14':'0.10.13',checked_at:'now',changelog:'# Changelog',history_source:'github'});
  await task;
  assert.equal(get('update-reload').disabled,false);
  assert.match(get('versions-feedback').textContent,/Geprüft:/);
  assert.equal(get('update-panel').hidden,!newer);
  if(!newer)assert.match(get('versions-feedback').textContent,/Installierte Version ist aktuell/);
 }
});
