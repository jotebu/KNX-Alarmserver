const {test}=require('node:test');
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
class Node{
 constructor(tag='div'){this.tagName=tag;this.children=[];this.value='';this.disabled=false;this.textContent='';this.files=[];}
 append(...items){this.children.push(...items);}replaceChildren(...items){this.children=items;}setAttribute(){}
 querySelectorAll(){return [];}
}
function setup(){
 const nodes=new Map(),requests=[];let confirmCalls=0;
 const get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};
 const row={id:'alarm-000001',name:'Pumpe',group_address:'1/2/3',dpt:'1.005',operator:'eq',threshold:'true',hysteresis:'0',field:'',area:'Technik',priority:'2'};
 const ctx=vm.createContext({access:{configure:true},page:'/matrix',$:get,document:{createDocumentFragment:()=>new Node('fragment'),createElement:tag=>new Node(tag)},
 text:(tag,value)=>Object.assign(new Node(tag),{textContent:value}),confirm:()=>{confirmCalls++;return true;},window:{addEventListener(){}},
 api:async(url,options={})=>{requests.push({url,options});if(!options.method)return {rows:[{...row}],revision:'r1',priorities:[{priority:2,name:'Warnung'}]};const body=JSON.parse(options.body);return {rows:(body.rows||[row]).map((r,i)=>({...r,id:r.id||'alarm-00000'+(i+1)})),revision:'r2',priorities:[{priority:2,name:'Warnung'}]};}});
 vm.runInContext(source.slice(source.indexOf('let matrixRows='),source.indexOf('function applyAccess(){')),ctx);
 return {get,ctx,requests,confirms:()=>confirmCalls};
}
test('matrix editor loads rows, edits fields and submits revision with server-assigned IDs',async()=>{
 const s=setup();await vm.runInContext('loadMatrix()',s.ctx);
 assert.equal(vm.runInContext('matrixPriorities[0].name',s.ctx),'Warnung');
 s.get('matrix-add').onclick();assert.equal(vm.runInContext('matrixRows[1].id',s.ctx),'');
 assert.equal(vm.runInContext('matrixDirty',s.ctx),true);
 await s.get('matrix-save').onclick();
 const saved=s.requests.find(r=>r.options.method==='PUT');const body=JSON.parse(saved.options.body);
 assert.equal(body.revision,'r1');assert.equal(body.rows[1].id,'');assert.equal(body.rows[1].priority,'2');assert.equal(saved.options.headers['X-Alarmserver-Action'],'manage-matrix');
 assert.equal(vm.runInContext('matrixDirty',s.ctx),false);
 assert.equal(vm.runInContext('matrixRows[1].id',s.ctx),'alarm-000002');
 assert.match(s.get('matrix-feedback').textContent,/sofort aktiviert/);
});
test('CSV import refuses unsaved table changes and sends file plus revision when clean',async()=>{
 const s=setup();await vm.runInContext('loadMatrix()',s.ctx);s.get('matrix-add').onclick();
 const submit=()=>s.get('matrix-import-form').onsubmit({preventDefault(){}});
 submit();assert.match(s.get('matrix-feedback').textContent,/speichern oder verwerfen/);
 assert.equal(s.requests.length,1);
 await vm.runInContext('loadMatrix()',s.ctx);assert.equal(s.confirms(),1);
 s.get('matrix-file').files=[{size:10,text:async()=> 'csv example'}];submit();
 await new Promise(resolve=>setImmediate(resolve));
 const request=s.requests.find(r=>r.url==='/api/matrix/import');
 assert.deepEqual(JSON.parse(request.options.body),{csv:'csv example',revision:'r1'});
});

test('priority table renames labels while sending stable numeric keys',async()=>{
 const nodes=new Map(),requests=[];const get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};
 const ctx=vm.createContext({$:get,document:{createDocumentFragment:()=>new Node('fragment'),createElement:tag=>new Node(tag)},
 text:(tag,value)=>Object.assign(new Node(tag),{textContent:value}),window:{addEventListener(){}},confirm:()=>true,
 api:async(url,options={})=>{requests.push({url,options});return options.method?{...JSON.parse(options.body),revision:'new'}:{entries:[{priority:1,name:'Brand'},{priority:2,name:'Warnung'}],revision:'old'};}});
 vm.runInContext(source.slice(source.indexOf('let priorityEntries='),source.indexOf('let matrixRows=')),ctx);
 await vm.runInContext('loadPriorities()',ctx);
 vm.runInContext("priorityEntries[0].name='Notfall';prioritiesDirty=true",ctx);
 await get('priorities-save').onclick();
 const saved=JSON.parse(requests.find(r=>r.options.method==='PUT').options.body);
 assert.deepEqual(saved,{entries:[{priority:1,name:'Notfall'},{priority:2,name:'Warnung'}],revision:'old'});
 assert.equal(vm.runInContext('prioritiesDirty',ctx),false);
 assert.equal(vm.runInContext('priorityEntries[0].priority',ctx),1);
 assert.match(get('priorities-feedback').textContent,/gespeichert/);
});

test('single bus test is admin-only and unavailable with unsaved matrix edits',async()=>{
 const s=setup();await vm.runInContext('loadMatrix()',s.ctx);
 function buttons(node){return [node,...node.children.flatMap(buttons)].filter(n=>n.tagName==='button'&&n.textContent==='▷');}
 let tests=buttons(s.get('matrix-rows'));assert.equal(tests.length,1);assert.equal(tests[0].disabled,false);
 let opened='';s.ctx.window.KnxBusTest={open:id=>opened=id};tests[0].onclick();assert.equal(opened,'alarm-000001');
 vm.runInContext('matrixChanged();renderMatrix()',s.ctx);assert.equal(buttons(s.get('matrix-rows'))[0].disabled,true);
 vm.runInContext('access.configure=false;renderMatrix()',s.ctx);assert.equal(buttons(s.get('matrix-rows')).length,0);
});
