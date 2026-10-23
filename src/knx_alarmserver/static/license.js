'use strict';
window.AlarmLicense={status(state){
  if(!state)return;
  const icon=document.getElementById('license-link');
  const color=state.licensed?'':state.trial_active?' status-yellow':' status-red';
  const label=state.licensed?'Lizenz aktiv':state.trial_active?'Probezeit · '+state.trial_days_remaining+' '+(state.trial_days_remaining===1?'Tag':'Tage')+' verbleibend':'Keine Lizenz · Probezeit abgelaufen';
  icon.className='icon-button license-link'+color;icon.title=label;icon.setAttribute('aria-label',label);
  if(this.render)this.render(state);
}};
// Nur auf der Lizenzseite initialisieren; alle Änderungen zusätzlich serverseitig geschützt.
if(window.location.pathname==='/license'){
  const licenseNode=id=>document.getElementById(id);
  let licenseBusy=false,licenseDefaultsSet=false;
  function renderLicense(state){
    licenseNode('license-status').textContent=state.licensed?'Lizenz aktiv':state.trial_active?'Probezeit':'Probezeit abgelaufen';
    licenseNode('license-status').className='license-status-badge'+(state.licensed?'':state.trial_active?' status-yellow':' status-red');
    licenseNode('license-status-detail').textContent=state.licensed?'Deine Dauerlizenz ist für diesen Server aktiviert.':state.trial_active?'Noch '+state.trial_days_remaining+' '+(state.trial_days_remaining===1?'Tag':'Tage')+' Probezeit.':'Für diesen Server ist keine gültige Lizenz aktiviert.';
    licenseNode('license-owner').textContent=state.license_email||'—';
    licenseNode('license-id').textContent=state.license_id||'—';
    licenseNode('license-date-label').textContent=state.licensed?'Aktiviert am':'Probezeit bis';
    const date=state.licensed?state.activated_at:state.trial_expires_at;
    licenseNode('license-activated').textContent=date?new Date(date).toLocaleString('de-DE'):'—';
    licenseNode('license-id-row').hidden=!state.licensed;
    licenseNode('license-error').textContent=[state.error,state.device_error,state.key_error,state.trial_error].filter(Boolean).join(' ');
    licenseNode('license-error').hidden=!licenseNode('license-error').textContent;
    licenseNode('license-key-note').hidden=state.trusted_keys>0;
    licenseNode('license-request').disabled=!state.device;
    licenseNode('license-activate').disabled=!state.device||!state.trusted_keys;
    licenseNode('license-import').disabled=!state.device||!state.trusted_keys;
    for(const id of ['license-email','license-activation-email'])if(state.license_email&&!licenseNode(id).value)licenseNode(id).value=state.license_email;
    if(!licenseDefaultsSet){licenseNode('license-request-step').open=!state.licensed;licenseDefaultsSet=true;}
  }
  window.AlarmLicense.render=renderLicense;
  async function loadLicense(feedback=false){
    window.AlarmLicense.status(await api('/api/license'));
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
      licenseNode('license-activation-email').value=result.email;
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
      const state=await api('/api/license/activate',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'manage-license'},body:JSON.stringify({email:licenseNode('license-activation-email').value,code:licenseNode('license-code').value})});
      window.AlarmLicense.status(state);licenseNode('license-code').value='';
      licenseNode('license-request-step').open=false;licenseNode('license-activate-step').open=false;
      licenseNode('license-feedback').textContent='Lizenz erfolgreich geprüft und aktiviert.';
    });
  };
  licenseNode('license-import').onclick=()=>licenseAction(async()=>{
    const file=licenseNode('license-file').files[0];
    if(!file)throw new Error('Bitte eine Lizenzdatei auswählen.');
    if(!file.size||file.size>8192)throw new Error('Lizenzdatei muss zwischen 1 Byte und 8 KiB groß sein.');
    const state=await api('/api/license/import',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Alarmserver-Action':'manage-license'},body:await file.arrayBuffer()});
    window.AlarmLicense.status(state);
    licenseNode('license-activation-email').value=state.license_email;
    licenseNode('license-code').value='';licenseNode('license-file').value='';
    licenseNode('license-request-step').open=false;licenseNode('license-activate-step').open=false;
    licenseNode('license-feedback').textContent='Lizenzdatei erfolgreich geprüft und aktiviert.';
  });
  loadLicense().catch(error=>{licenseNode('license-feedback').textContent=error.message;});
}
