'use strict';
// Runs before the stylesheet, including on the login page, to avoid a theme flash.
(()=>{
  const key='knx-alarmserver.theme',choices=new Set(['dark','light','auto']);
  const stored=()=>{try{const value=window.localStorage.getItem(key);return choices.has(value)?value:'dark';}catch{return 'dark';}};
  let preference=stored(),system=null;
  try{system=window.matchMedia('(prefers-color-scheme: dark)');}catch{/* Keep Dark when system detection is unavailable. */}
  function apply(){
    document.documentElement.dataset.theme=preference==='auto'?(system&&system.matches===false?'light':'dark'):preference;
    const control=document.getElementById('theme-choice');
    if(control){control.dataset.preference=preference;for(const input of control.querySelectorAll('input'))input.checked=input.value===preference;}
  }
  function bind(){
    const control=document.getElementById('theme-choice');if(!control)return;
    apply();
    control.addEventListener('change',event=>{
      if(!choices.has(event.target.value)){apply();return;}
      preference=event.target.value;try{window.localStorage.setItem(key,preference);}catch{/* Theme still works without persistent storage. */}
      apply();
    });
  }
  apply();
  if(system){const changed=()=>{if(preference==='auto')apply();};if(system.addEventListener)system.addEventListener('change',changed);else if(system.addListener)system.addListener(changed);}
  window.addEventListener('storage',event=>{if(event.key===key||event.key===null){preference=stored();apply();}});
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',bind,{once:true});else bind();
})();
