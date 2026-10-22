const {test}=require('node:test'),assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../src/knx_alarmserver/static/theme.js'),'utf8');
function setup({stored=null,systemDark=true,storageBlocked=false,systemUnavailable=false,login=false}={}){
 const data=new Map(),events={},docEvents={},selectEvents={};if(stored!==null)data.set('knx-alarmserver.theme',stored);
 const inputs=['dark','light','auto'].map(value=>({value,checked:false})),select={dataset:{},querySelectorAll:()=>inputs,addEventListener:(name,fn)=>selectEvents[name]=fn},root={dataset:{}},media={matches:systemDark,addEventListener:(name,fn)=>events['system-'+name]=fn};
 const window={localStorage:{getItem:key=>{if(storageBlocked)throw Error('blocked');return data.get(key)||null;},setItem:(key,value)=>{if(storageBlocked)throw Error('blocked');data.set(key,value);}},matchMedia:()=>{if(systemUnavailable)throw Error('unavailable');return media;},addEventListener:(name,fn)=>events[name]=fn};
 const document={readyState:'loading',documentElement:root,getElementById:id=>!login&&id==='theme-choice'?select:null,addEventListener:(name,fn)=>docEvents[name]=fn};
 vm.runInNewContext(source,{window,document,Set});
 return{root,select,data,events,bind:()=>docEvents.DOMContentLoaded(),choose:value=>{selectEvents.change({target:{value}});},system:value=>{media.matches=value;events['system-change']?.();}};
}
test('current Dark appearance is the default and applies before DOM content is ready',()=>{
 const s=setup({systemDark:false});assert.equal(s.root.dataset.theme,'dark');s.bind();assert.equal(s.select.dataset.preference,'dark');
});
test('Dark and Light choices persist, survive reload and ignore system changes',()=>{
 const s=setup();s.bind();s.choose('light');assert.equal(s.root.dataset.theme,'light');assert.equal(s.data.get('knx-alarmserver.theme'),'light');s.system(true);assert.equal(s.root.dataset.theme,'light');const next=setup({stored:s.data.get('knx-alarmserver.theme')});assert.equal(next.root.dataset.theme,'light');next.bind();assert.equal(next.select.dataset.preference,'light');s.choose('dark');assert.equal(s.root.dataset.theme,'dark');
});
test('Automatic follows both system transitions and keeps Automatic selected',()=>{
 const s=setup({stored:'auto',systemDark:false});assert.equal(s.root.dataset.theme,'light');s.bind();assert.equal(s.select.dataset.preference,'auto');s.system(true);assert.equal(s.root.dataset.theme,'dark');assert.equal(s.select.dataset.preference,'auto');s.system(false);assert.equal(s.root.dataset.theme,'light');
});
test('blocked storage, unavailable system detection and invalid values remain usable',()=>{
 const s=setup({storageBlocked:true,systemUnavailable:true,stored:'light'});assert.equal(s.root.dataset.theme,'dark');s.bind();s.choose('light');assert.equal(s.root.dataset.theme,'light');s.choose('auto');assert.equal(s.root.dataset.theme,'dark');s.choose('invalid');assert.equal(s.select.dataset.preference,'auto');const invalid=setup({stored:'invalid'});assert.equal(invalid.root.dataset.theme,'dark');
});
test('other tabs synchronize the preference; login applies a saved choice without a menu',()=>{
 const s=setup();s.bind();s.data.set('knx-alarmserver.theme','light');s.events.storage({key:'knx-alarmserver.theme'});assert.equal(s.root.dataset.theme,'light');assert.equal(s.select.dataset.preference,'light');s.data.clear();s.events.storage({key:null});assert.equal(s.root.dataset.theme,'dark');const login=setup({stored:'light',login:true});login.bind();assert.equal(login.root.dataset.theme,'light');
});
