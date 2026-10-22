const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/app.js'),'utf8');
class Node{
 constructor(tag='div'){this.attrs={};this.tagName=tag;this.children=[];this.dataset={};this.value='';this.checked=false;this.disabled=false;this.textContent='';}
 append(...items){for(const item of items)this.children.push(...(item.tagName==='fragment'?item.children:[item]));}
 replaceChildren(...items){this.children=[];this.append(...items);}
 querySelector(selector){const field=/template-field="(\w+)"/.exec(selector)?.[1];return this.children.flatMap(all).find(n=>n.dataset.templateField===field);}
 querySelectorAll(){return [];}
 setAttribute(key,value){this.attrs[key]=value;}
 showModal(){this.open=true;}
 close(){this.open=false;if(this.onclose)this.onclose();}
 focus(){this.focused=true;}
 reportValidity(){return this.value.includes('@');}
}
const all=node=>[node,...node.children.flatMap(all)];
async function setup(){
 const nodes=new Map(),requests=[];const get=id=>{if(!nodes.has(id))nodes.set(id,new Node());return nodes.get(id);};get('profile-user').textContent='admin@example.org';
 let snapshot={revision:'initial',priorities:[{priority:1,name:'Brand'}],placeholders:{meldung:'Bezeichnung'},counts:{failed:1},jobs:[],config:{enabled:false,host:'smtp.example.org',port:587,security:'starttls',username:'sender',password:'',password_set:true,from_email:'alarm@example.org',from_name:'Alarmserver',server_name:'Alarmserver',server_url:'',templates:{1:{subject:'{meldung}',body:'Hallo {empfaenger_name}'}}}};
 const ctx=vm.createContext({document:{createElement:tag=>new Node(tag),createDocumentFragment:()=>new Node('fragment'),createTextNode:value=>Object.assign(new Node('text'),{textContent:value})},$:get,text:(tag,value)=>Object.assign(new Node(tag),{textContent:value}),date:()=>'',Boolean,Number,Object,JSON,String,
 api:async(url,opts={})=>{requests.push({url,opts});if(opts.method==='PUT'){const payload=JSON.parse(opts.body);snapshot={...snapshot,revision:'saved',config:{...payload.config,password:'',password_set:true}};}if(url==='/api/mail/test')return {message:'Testmail angenommen.'};if(url==='/api/mail/retry'){snapshot.counts.failed=0;return {retried:1};}return snapshot;}});
 vm.runInContext(source.slice(source.indexOf('let mailRevision='),source.indexOf('let editingUser=')),ctx);await vm.runInContext('loadMail()',ctx);return {get,ctx,requests};
}
test('mail configuration masks saved password and sends templates with revision and action header',async()=>{
 const s=await setup();assert.equal(s.get('mail-password').value,'');assert.match(s.get('mail-password-state').textContent,/gespeichert/);assert.equal(s.get('mail-test-recipient').value,'admin@example.org');assert.equal(s.get('mail-templates').children.length,1);
 s.get('mail-password').value='new-secret';s.get('mail-enabled').checked=true;s.get('mail-form').onsubmit({preventDefault(){}});await new Promise(setImmediate);
 const request=s.requests.find(r=>r.opts.method==='PUT'),payload=JSON.parse(request.opts.body);assert.equal(payload.revision,'initial');assert.equal(payload.config.password,'new-secret');assert.equal(payload.config.enabled,true);assert.equal(payload.config.templates[1].subject,'{meldung}');assert(!('password_set'in payload.config));assert.equal(request.opts.headers['X-Alarmserver-Action'],'manage-mail');assert.equal(s.get('mail-password').value,'');
});
test('test mail requires a valid recipient and saved edits; it is never sent automatically',async()=>{
 const s=await setup();assert(!s.requests.some(r=>r.url==='/api/mail/test'));s.get('mail-form').oninput();await s.get('mail-test').onclick();assert.match(s.get('mail-feedback').textContent,/zuerst/);assert(!s.requests.some(r=>r.url==='/api/mail/test'));
 await vm.runInContext('loadMail()',s.ctx);s.get('mail-test-recipient').value='invalid';await s.get('mail-test').onclick();assert(!s.requests.some(r=>r.url==='/api/mail/test'));s.get('mail-test-recipient').value='person@example.org';await s.get('mail-test').onclick();assert.equal(s.requests.filter(r=>r.url==='/api/mail/test').length,1);assert.match(s.get('mail-feedback').textContent,/angenommen/);
});
test('retry updates the status and disables retry when no failures remain',async()=>{
 const s=await setup();assert.equal(s.get('mail-retry').disabled,false);await s.get('mail-retry').onclick();assert.equal(s.get('mail-retry').disabled,true);assert.match(s.get('mail-feedback').textContent,/1 fehlgeschlagene/);
});

test('provider help opens and closes without saving edits or sending mail',async()=>{
 const s=await setup();const before=s.requests.length;s.get('mail-password').value='unsaved-secret';s.get('mail-form').oninput();s.get('mail-help-open').onclick();assert.equal(s.get('mail-help-dialog').open,true);assert.equal(s.get('mail-help-open').attrs['aria-expanded'],'true');s.get('mail-help-close').onclick();assert.equal(s.get('mail-help-dialog').open,false);assert.equal(s.get('mail-help-open').attrs['aria-expanded'],'false');assert.equal(s.get('mail-help-open').focused,true);assert.equal(s.get('mail-password').value,'unsaved-secret');assert.equal(s.requests.length,before);await s.get('mail-test').onclick();assert.match(s.get('mail-feedback').textContent,/zuerst/);assert.equal(s.requests.length,before);
});
