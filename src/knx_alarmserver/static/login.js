
'use strict';
document.getElementById('login-form').onsubmit=async event=>{
  event.preventDefault();
  const button=document.getElementById('login-submit'),feedback=document.getElementById('login-feedback');
  button.disabled=true;feedback.textContent='Anmeldung wird geprüft …';
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),15000);
  try{
    const response=await fetch('/api/login',{method:'POST',credentials:'same-origin',signal:controller.signal,
      headers:{'Content-Type':'application/json','X-Alarmserver-Action':'login'},
      body:JSON.stringify({username:document.getElementById('login-name').value,password:document.getElementById('login-password').value})});
    const result=await response.json();
    if(!response.ok)throw new Error(result.detail||'Anmeldung fehlgeschlagen');
    document.getElementById('login-password').value='';window.location.replace('/');
  }catch(error){feedback.textContent=controller.signal.aborted?'Zeitüberschreitung. Bitte erneut anmelden.':error.message;}
  finally{clearTimeout(timer);button.disabled=false;}
};
