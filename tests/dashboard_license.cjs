const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/license.js'),'utf8');
async function setup(){
  const nodes=new Map(),requests=[];
  const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',hidden:true,textContent:'',disabled:false,events:{},addEventListener(k,v){this.events[k]=v;},setAttribute(){},focus(){},select(){}});return nodes.get(id);};
  const state={licensed:false,state:'unlicensed',trusted_keys:1,device:'sha256:abc'};
  const api=async(url,options)=>{requests.push({url,options});if(url.endsWith('/request'))return {request_code:'ASKREQ1.example',email:'kunde@example.de'};if(url.endsWith('/activate'))return {...state,licensed:true,license_email:'kunde@example.de',license_id:'test-id'};return state;};
  const context={window:{location:{pathname:'/license'}},document:{getElementById:node,execCommand:()=>true},api,navigator:{},Date,JSON,Error,setTimeout,URL,Blob};
  vm.runInNewContext(source,context);
  await new Promise(resolve=>setImmediate(resolve));
  return {nodes,node,requests,state};
}
test('license request normalizes identity, downloads are invalidated after email changes',async()=>{
  const {node,requests}=await setup();
  node('license-email').value='Kunde@EXAMPLE.DE';
  node('license-request-form').onsubmit({preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(node('license-request-code').value,'ASKREQ1.example');
  assert.equal(node('license-request-result').hidden,false);
  assert.equal(node('license-email').value,'kunde@example.de');
  assert.equal(requests.at(-1).options.headers['X-Alarmserver-Action'],'manage-license');
  node('license-email').events.input();
  assert.equal(node('license-request-code').value,'');
  assert.equal(node('license-request-result').hidden,true);
});
test('activation uses chosen email and code, shows confirmed state and clears submitted code',async()=>{
  const {node,requests}=await setup();
  node('license-email').value='kunde@example.de';node('license-code').value='ASKLIC1.test';
  node('license-activate-form').onsubmit({preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(JSON.parse(requests.at(-1).options.body),{email:'kunde@example.de',code:'ASKLIC1.test'});
  assert.equal(node('license-status').textContent,'Dauerlizenz aktiviert.');
  assert.equal(node('license-code').value,'');
  assert.match(node('license-feedback').textContent,/erfolgreich/);
});
test('missing verification keys disable activation; device errors disable requests',async()=>{
  const {node,state}=await setup();
  state.trusted_keys=0;state.device=null;state.device_error='Keine Gerätekennung';
  node('license-reload').onclick();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(node('license-activate').disabled,true);
  assert.equal(node('license-request').disabled,true);
  assert.equal(node('license-key-note').hidden,false);
  assert.equal(node('license-error').textContent,'Keine Gerätekennung');
});
