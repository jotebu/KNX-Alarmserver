const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
class Node {
 constructor(tag='div'){this.tagName=tag;this.children=[];this.hidden=true;this.value='';this.checked=false;this.classList={remove(){},toggle(){}};this.textContent='';this.attrs={};}
 append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=nodes;}setAttribute(k,v){this.attrs[k]=v;}
}
async function setup(role,knx={enabled:false,ready:false,connections:[]},page='/'){
 const nodes=new Map(),redirects=[];
 const document={querySelectorAll:()=>[],getElementById(id){if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);},createElement:tag=>new Node(tag),createDocumentFragment:()=>new Node('fragment')};
 const snapshot={telegrams:[],telegram_rates:{minute:1234,hour:56789},status:{user:'person@example.org',role,version:'test',permissions:{configure:role==='admin',acknowledge:role!=='viewer'},knx},alarms:[{status:'active',pending:1,fresh:true,name:'Alarm',display_value:'1',group_address:'1/2/3',dpt:'1.005',operator:'eq',threshold:1}]};
 const context=vm.createContext({document,Date,JSON,Math,window:{location:{pathname:page,replace:p=>redirects.push(p)}},setTimeout:()=>0,clearTimeout(){},encodeURIComponent,snapshot});
 const prefix=source.slice(0,source.indexOf('async function api('));
 const schedule=source.slice(source.indexOf('let pollTimer='),source.indexOf('function failure('));
 const render=source.slice(source.indexOf('function render(){'),source.indexOf('let settingsOpen='));
 const access=source.slice(source.indexOf('function applyAccess(){'),source.indexOf('async function initializePage(){'));
 vm.runInContext(prefix+schedule+'\nlet settingsOpen=false,filtersOpen=false;function failure(){}function renderReadStatus(){}async function api(){return snapshot;}async function initializePage(){}\n'+render+access,context);
 await vm.runInContext('refresh()',context);
 return {nodes,context,redirects};
}
function all(node){return [node,...node.children.flatMap(all)];}
test('role in profile menu; admin gear and acknowledgement controls respect roles',async()=>{
 for(const role of ['viewer','user','admin']){
  const {nodes}=await setup(role);
  assert.equal(nodes.get('settings-menu').hidden,role==='viewer');
  assert.equal(nodes.get('mail-link').hidden,role!=='admin');
  assert.equal(nodes.get('identity').textContent,{admin:'Admin',user:'User',viewer:'Viewer'}[role]);
  assert.equal(nodes.get('profile-user').textContent,'person@example.org');
  assert.equal(all(nodes.get('table-body')).filter(n=>n.tagName==='button').length,role==='viewer'?0:1);
 }
});
test('KNX icon shows yellow when disabled, green when ready, red for fault or storage failure',async()=>{
 for(const [knx,color] of [[{enabled:false},'yellow'],[{enabled:true,ready:true},'green'],[{enabled:true,ready:false},'red'],[{enabled:true,ready:true,storage_error:true},'red']]){
  const {nodes}=await setup('admin',{connections:[],...knx});
  assert.equal(nodes.get('knx-status-icon').className,'icon-button status-'+color);
  assert.ok(nodes.get('knx-status-icon').attrs['aria-label']);
 }
});
test('non-admin management navigation is redirected away',async()=>{
 const {redirects}=await setup('viewer',undefined,'/users');assert.deepEqual(redirects,['/']);
});
test('alarm timestamp displays the state transition rather than a later repeated reception',async()=>{
 const {nodes,context}=await setup('admin');
 await vm.runInContext("snapshot.alarms[0].changed_at='2026-10-21T12:00:00Z';snapshot.alarms[0].last_seen='2026-10-22T12:00:00Z';refresh()",context);
 const cells=all(nodes.get('table-body')).filter(node=>node.tagName==='td');
 assert.match(cells[4].textContent,/21\.10\.2026/);
 assert.doesNotMatch(cells[4].textContent,/22\.10\.2026/);
});

test('acknowledgement targets the displayed occurrence, with its own three timestamps',async()=>{
 const {nodes,context}=await setup('user');
 await vm.runInContext("snapshot.alarms[0].occurrence_id=73;snapshot.alarms[0].came_at='2026-10-20T12:00:00Z';snapshot.alarms[0].changed_at='2026-10-22T12:00:00Z';snapshot.alarms[0].went_at='2026-10-21T12:00:00Z';refresh()",context);
 const cells=all(nodes.get('table-body')).filter(node=>node.tagName==='td');
 assert.equal(cells.length,8);assert.match(cells[4].textContent,/20\.10\.2026/);assert.match(cells[6].textContent,/21\.10\.2026/);
 vm.runInContext("let ackPath='';api=async(path,options)=>{if(options){ackPath=path;return {changed:true};}return snapshot;}",context);
 await all(nodes.get('table-body')).find(node=>node.tagName==='button').onclick();
 assert.equal(vm.runInContext('ackPath',context),'/api/occurrences/73/acknowledge');
});

test('telegram counters show unfiltered rolling totals and update to zero',async()=>{
 const {nodes,context}=await setup('admin',undefined,'/telegrams');
 assert.equal(nodes.get('telegram-rates').hidden,false);
 assert.equal(nodes.get('telegram-minute').textContent,(1234).toLocaleString('de-DE'));
 assert.equal(nodes.get('telegram-hour').textContent,(56789).toLocaleString('de-DE'));
 await vm.runInContext("snapshot.telegram_rates={minute:0,hour:0};refresh()",context);
 assert.equal(nodes.get('telegram-minute').textContent,'0');
 assert.equal(nodes.get('telegram-hour').textContent,'0');
 const dashboard=await setup('admin');assert.equal(dashboard.nodes.get('telegram-rates').hidden,true);
});
