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
test('KNX icon uses worst menu connection: red before yellow before green',async()=>{
 const on={name:'On',state:'CONNECTED'},off={name:'Off',state:'DISABLED'},error={name:'Error',state:'ERROR'};
 for(const [knx,color] of [
  [{enabled:true,connections:[on]},'green'],
  [{enabled:true,ready:true,connections:[on,off]},'yellow'],
  [{enabled:true,connections:[on,off,error]},'red'],
  [{enabled:true,connections:[error,off,on]},'red'],
  [{enabled:true,connections:[off,on]},'yellow'],
  [{enabled:false,connections:[on,error]},'yellow'],
  [{enabled:true,connections:[]},'yellow'],
  [{enabled:false,connections:[]},'yellow'],
  [{enabled:true,storage_error:true,connections:[on]},'red']
 ]){
  const {nodes}=await setup('admin',knx);
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

test('selected table order survives refreshed dashboard snapshots',async()=>{
 const {nodes,context}=await setup('admin');
 await vm.runInContext("snapshot.alarms=[{...snapshot.alarms[0],id:'a',name:'Pumpe 10',occurrence_id:10},{...snapshot.alarms[0],id:'b',name:'Pumpe 2',occurrence_id:2}];alarmSort={key:'number',direction:1};refresh()",context);
 const names=()=>nodes.get('table-body').children[0].children.map(tr=>tr.children[2].textContent);
 assert.deepEqual(names(),['Pumpe 2','Pumpe 10']);
 await vm.runInContext('snapshot.alarms.reverse();refresh()',context);assert.deepEqual(names(),['Pumpe 2','Pumpe 10']);
});

test('alarm list reveals 100 rows at a time near the scroll end without changing totals',async()=>{
 const {nodes,context}=await setup('user');
 await vm.runInContext("snapshot.alarms=Array.from({length:250},(_,i)=>({...snapshot.alarms[0],id:String(i),occurrence_id:i+1,priority:1}));snapshot.list_info={total:250};snapshot.counts={active:250,acked:0,pending:0,closed:0,unknown:0};refresh()",context);
 const count=()=>nodes.get('table-body').children[0].children.length;
 const scroll=nodes.get('message-list-scroll');scroll.clientHeight=600;scroll.scrollHeight=6000;scroll.scrollTop=0;
 assert.equal(count(),100);assert.equal(nodes.get('active').textContent,250);assert.equal(nodes.get('list-summary').textContent,'Vorgänge: 250');
 scroll.onscroll();assert.equal(count(),100);
 scroll.scrollTop=5200;scroll.onscroll();assert.equal(count(),200);assert.equal(scroll.scrollTop,5200);
 scroll.scrollHeight=12000;scroll.scrollTop=11200;scroll.onscroll();assert.equal(count(),250);
 scroll.onscroll();assert.equal(count(),250);
 await vm.runInContext('refresh()',context);assert.equal(count(),250);
 assert.equal(nodes.get('active').textContent,250);assert.equal(nodes.get('list-summary').textContent,'Vorgänge: 250');
});
test('sorting and filter changes restart display at 100 rows, sorting the full result first',async()=>{
 const {nodes,context}=await setup('viewer');
 await vm.runInContext("snapshot.alarms=Array.from({length:240},(_,i)=>({...snapshot.alarms[0],id:String(i),occurrence_id:i+1}));snapshot.list_info={total:240};refresh();alarmVisibleCount=200;render();alarmSort={key:'number',direction:-1};render()",context);
 const rows=()=>nodes.get('table-body').children[0].children;
 assert.equal(rows().length,100);assert.equal(rows()[0].children[1].children[0].textContent,240);
 assert.equal(nodes.get('message-list-scroll').scrollTop,0);
 await vm.runInContext("alarmVisibleCount=200;render();listFilters.from='2026-10-01';listGeneration++;render()",context);assert.equal(rows().length,100);
});
test('telegram rows are not limited by the alarm display window',async()=>{
 const {nodes,context}=await setup('admin',undefined,'/telegrams');
 await vm.runInContext("snapshot.telegrams=Array.from({length:250},()=>({connection:'KNX',source:'1.1.1',destination:'1/2/3',service:'GroupValueWrite'}));refresh()",context);
 assert.equal(nodes.get('table-body').children[0].children.length,250);
});

test('compact KNX menu lists colored connections and one latest receive timestamp',async()=>{
 const {nodes}=await setup('viewer',{enabled:true,ready:false,connections:[
  {name:'Hauptlinie',state:'CONNECTED',last_received:'2026-10-22T21:58:37Z'},
  {name:'Nebenlinie',state:'ERROR',last_received:'2026-10-22T22:05:00Z'},
  {name:'Reserve',state:'DISABLED',last_received:null}
 ]});
 const rows=nodes.get('connection-detail').children[0].children;
 assert.equal(nodes.get('knx-status-heading').textContent,'KNX-Verbindungen');
 assert.deepEqual(rows.map(r=>r.children[0].textContent),['Hauptlinie','Nebenlinie','Reserve']);
 assert.deepEqual(rows.map(r=>r.children[1].className),['knx-connection-dot dot-green','knx-connection-dot dot-red','knx-connection-dot dot-yellow']);
 assert.deepEqual(rows.map(r=>r.children[1].attrs['aria-label']),['Aktiv','Fehler','Deaktiviert']);
 assert.equal(nodes.get('connection-last-received').textContent,'Letzter Empfang '+new Date('2026-10-22T22:05:00Z').toLocaleString('de-DE'));
 assert.equal(nodes.get('connection-error').hidden,true);
});
test('KNX disabled and unconfigured menu remains yellow with no reception; storage errors remain visible',async()=>{
 const empty=await setup('admin',{enabled:false,ready:false,connections:[]});
 assert.equal(empty.nodes.get('knx-status-heading').textContent,'KNX-Verbindung');
 assert.equal(empty.nodes.get('connection-last-received').textContent,'Letzter Empfang —');
 assert.equal(empty.nodes.get('connection-detail').children[0].children[0].children[1].className,'knx-connection-dot dot-yellow');
 const disabled=await setup('admin',{enabled:false,storage_error:true,connections:[{name:'Hauptlinie',state:'CONNECTED',last_received:'invalid'}]});
 assert.equal(disabled.nodes.get('connection-detail').children[0].children[0].children[1].className,'knx-connection-dot dot-yellow');
 assert.equal(disabled.nodes.get('knx-status-heading').textContent,'KNX-Verbindung');
 assert.equal(disabled.nodes.get('connection-error').hidden,false);
 assert.equal(disabled.nodes.get('connection-last-received').textContent,'Letzter Empfang —');
});
