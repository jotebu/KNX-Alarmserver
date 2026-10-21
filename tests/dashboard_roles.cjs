const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
class Node {
  constructor(tag='div'){this.tagName=tag;this.children=[];this.hidden=true;this.value='';this.checked=false;this.classList={remove(){}};this.textContent='';}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=nodes;}
}
function setup(role){
  const nodes=new Map(),document={getElementById(id){if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);},createElement:tag=>new Node(tag),createDocumentFragment:()=>new Node('fragment')};
  const context=vm.createContext({document,Date,JSON,Math,setTimeout,clearTimeout,encodeURIComponent});
  const prefix=source.slice(0,source.indexOf('async function api('));
  const render=source.slice(source.indexOf('function render(){'),source.indexOf('async function refresh(){'));
  const access=source.slice(source.indexOf('function closeUsers(){'),source.indexOf('let editingUser='));
  vm.runInContext(prefix+'\nlet settingsOpen=false;\n'+render+access,context);
  vm.runInContext(`access={role:'${role}',configure:${role==='admin'},acknowledge:${role!=='viewer'}};data.alarms=[{status:'active',pending:1,fresh:true,name:'Alarm',display_value:'1',group_address:'1/2/3',dpt:'1.005',operator:'eq',threshold:1}];applyAccess();render();`,context);
  return {nodes,context};
}
function all(node){return [node,...node.children.flatMap(all)];}
test('viewer has no acknowledgement or configuration controls; user can only acknowledge; admin has all',()=>{
  for(const role of ['viewer','user','admin']){
    const {nodes}=setup(role);
    for(const id of ['knx-settings-tab','ets-tab','users-tab'])assert.equal(nodes.get(id).hidden,role!=='admin',`${role}: ${id}`);
    const buttons=all(nodes.get('table-body')).filter(n=>n.tagName==='button');
    assert.equal(buttons.length,role==='viewer'?0:1,role);
    if(buttons.length)assert.equal(buttons[0].textContent,'Quittieren');
  }
});
test('losing admin access closes privileged panels and returns to read view',()=>{
  const {nodes,context}=setup('admin');
  vm.runInContext("settingsOpen=true;access={role:'viewer',configure:false,acknowledge:false};applyAccess();render();",context);
  for(const id of ['knx-settings','ets-panel','users-panel'])assert.equal(nodes.get(id).hidden,true,id);
  assert.equal(nodes.get('data-panel').hidden,false);
  assert.equal(vm.runInContext('settingsOpen',context),false);
  assert.equal(all(nodes.get('table-body')).filter(n=>n.tagName==='button').length,0);
});
