'use strict';
// Nur auf der Lizenzseite initialisieren; alle Änderungen zusätzlich serverseitig geschützt.
if(window.location.pathname==='/license'){
  const licenseNode=id=>document.getElementById(id);
  let licenseBusy=false;
  function renderLicense(state){
    licenseNode('license-status').textContent=state.licensed?'Dauerlizenz aktiviert.':state.state==='invalid'?'Gespeicherte Lizenz konnte nicht bestätigt werden.':'Noch keine Lizenz aktiviert.';
    licenseNode('license-owner').textContent=state.license_email||'—';
    licenseNode('license-id').textContent=state.license_id||'—';
    licenseNode('license-activated').textContent=state.activated_at?new Date(state.activated_at).toLocaleString('de-DE'):'—';
    licenseNode('license-error').textContent=[state.error,state.device_error,state.key_error].filter(Boolean).join(' ');
    licenseNode('license-error').hidden=!licenseNode('license-error').textContent;
    licenseNode('license-key-note').hidden=state.trusted_keys>0;
    licenseNode('license-request').disabled=!state.device;
    licenseNode('license-activate').disabled=!state.device||!state.trusted_keys;
    if(state.license_email&&!licenseNode('license-email').value)licenseNode('license-email').value=state.license_email;
  }
  async function loadLicense(feedback=false){
    renderLicense(await api('/api/license'));
    if(feedback)licenseNode('license-feedback').textContent='Lizenzstatus aktualisiert.';
  }
  async function licenseAction(action){
    if(licenseBusy)return;
    licenseBusy=true;licenseNode('license-panel').setAttribute('aria-busy','true');
    licenseNode('license-feedback').textContent='Wird geprüft …';
    try{await action();}catch(error){licenseNode('license-feedback').textContent=error.message;}
    finally{licenseBusy=false;licenseNode('license-panel').setAttribute('aria-busy','false');}
  }
  function invalidateLicenseRequest(){
    licenseNode('license-request-result').hidden=true;
    licenseNode('license-request-code').value='';
  }
  licenseNode('license-email').addEventListener('input',invalidateLicenseRequest);
  licenseNode('license-reload').onclick=()=>licenseAction(()=>loadLicense(true));
  licenseNode('license-request-form').onsubmit=event=>{
    event.preventDefault();
    invalidateLicenseRequest();
    licenseAction(async()=>{
      const result=await api('/api/license/request',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'manage-license'},body:JSON.stringify({email:licenseNode('license-email').value})});
      licenseNode('license-email').value=result.email;
      licenseNode('license-request-code').value=result.request_code;
      licenseNode('license-request-result').hidden=false;
      licenseNode('license-feedback').textContent='Anfragecode erzeugt. Er gilt für diese E-Mail und diesen Server.';
    });
  };
  licenseNode('license-copy').onclick=()=>licenseAction(async()=>{
    const field=licenseNode('license-request-code');
    if(!field.value)throw new Error('Bitte zuerst einen Anfragecode erzeugen.');
    if(navigator.clipboard&&window.isSecureContext)await navigator.clipboard.writeText(field.value);
    else{field.focus();field.select();if(!document.execCommand('copy'))throw new Error('Bitte den markierten Code manuell kopieren.');}
    licenseNode('license-feedback').textContent='Anfragecode kopiert.';
  });
  licenseNode('license-download').onclick=()=>licenseAction(async()=>{
    const code=licenseNode('license-request-code').value;
    if(!code)throw new Error('Bitte zuerst einen Anfragecode erzeugen.');
    const url=URL.createObjectURL(new Blob([code],{type:'text/plain;charset=utf-8'}));
    const link=document.createElement('a');link.href=url;link.download='alarmserver.askrequest';link.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
    licenseNode('license-feedback').textContent='Anfragedatei zum Download bereitgestellt.';
  });
  licenseNode('license-activate-form').onsubmit=event=>{
    event.preventDefault();
    licenseAction(async()=>{
      const state=await api('/api/license/activate',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'manage-license'},body:JSON.stringify({email:licenseNode('license-email').value,code:licenseNode('license-code').value})});
      renderLicense(state);licenseNode('license-code').value='';
      licenseNode('license-feedback').textContent='Lizenz erfolgreich geprüft und aktiviert.';
    });
  };
  loadLicense().catch(error=>{licenseNode('license-feedback').textContent=error.message;});
}
