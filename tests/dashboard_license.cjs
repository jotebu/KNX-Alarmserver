const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/license.js'),'utf8');
async function setup(){
  const nodes=new Map(),requests=[];
  const node=id=>{if(!nodes.has(id))nodes.set(id,{value:'',hidden:true,textContent:'',disabled:false,events:{},addEventListener(k,v){this.events[k]=v;},setAttribute(){},focus(){},select(){}});return nodes.get(id);};
  const state={licensed:false,state:'trial',trial_active:true,trial_days_remaining:7,trusted_keys:1,device:'sha256:abc'};
  const api=async(url,options)=>{requests.push({url,options});if(url.endsWith('/request'))return {request_code:'ASKREQ1.example',email:'kunde@example.de'};if(url.endsWith('/activate')||url.endsWith('/import'))return {...state,licensed:true,license_email:'kunde@example.de',license_id:'test-id'};return state;};
  const context={window:{location:{pathname:'/license'}},document:{getElementById:node,execCommand:()=>true},api,navigator:{},Date,JSON,Error,setTimeout,URL,Blob};
  vm.runInNewContext(source,context);
  await new Promise(resolve=>setImmediate(resolve));
  return {nodes,node,requests,state,context};
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
  node('license-activation-email').value='kunde@example.de';node('license-code').value='ASKLIC1.test';
  node('license-activate-form').onsubmit({preventDefault(){}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.deepEqual(JSON.parse(requests.at(-1).options.body),{email:'kunde@example.de',code:'ASKLIC1.test'});
  assert.equal(node('license-status').textContent,'Lizenz aktiv');
  assert.equal(node('license-code').value,'');
  assert.match(node('license-feedback').textContent,/erfolgreich/);
});
test('header icon is yellow in trial, red after expiry, neutral with an active license',async()=>{
  const {node,context,state}=await setup();
  assert.match(node('license-link').className,/status-yellow/);
  context.window.AlarmLicense.status({...state,trial_active:false,trial_days_remaining:0});
  assert.match(node('license-link').className,/status-red/);
  assert.match(node('license-link').title,/abgelaufen/);
  context.window.AlarmLicense.status({...state,licensed:true});
  assert.equal(node('license-link').className,'icon-button license-link');
  assert.equal(node('license-link').title,'Lizenz aktiv');
  assert.equal(node('license-status').textContent,'Lizenz aktiv');
});
test('license icon sits directly before KNX button and info/actions are grouped separately',()=>{
  const html=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/index.html'),'utf8');
  const license=html.indexOf('id="license-link"'),knx=html.indexOf('id="knx-status-menu"');
  assert.ok(license>0&&knx>license);
  assert.match(html.slice(license,knx),/<\/a>\s*<details $/);
  for(const id of ['license-overview','license-request-step','license-activate-step','license-activation-email'])assert.ok(html.includes(id));
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
test('license file import submits raw bytes and fills identity only from verified response',async()=>{
  const {node,requests}=await setup();
  const bytes=new Uint8Array([65,83,75]).buffer;
  node('license-file').files=[{size:3,arrayBuffer:async()=>bytes}];
  node('license-activation-email').value='wrong@example.de';
  node('license-import').onclick();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(requests.at(-1).url,'/api/license/import');
  assert.equal(requests.at(-1).options.body,bytes);
  assert.equal(requests.at(-1).options.headers['X-Alarmserver-Action'],'manage-license');
  assert.equal(node('license-activation-email').value,'kunde@example.de');
  assert.equal(node('license-link').className,'icon-button license-link');
  assert.match(node('license-feedback').textContent,/erfolgreich/);
});
test('empty or oversized license files never reach the server',async()=>{
  const {node,requests}=await setup();
  const before=requests.length;
  for(const size of [0,8193]){
    node('license-file').files=[{size}];node('license-import').onclick();
    await new Promise(resolve=>setImmediate(resolve));
    assert.equal(requests.length,before);
    assert.match(node('license-feedback').textContent,/8 KiB/);
  }
});
