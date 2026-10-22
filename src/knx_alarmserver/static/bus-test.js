'use strict';
(()=>{
  const dialog=document.getElementById('bus-test-dialog');
  let plan=null,knx={},loading=false,starting=false,job={state:'idle'},selection=new Set(),singleId='',observed=false,statusTimer=null;
  const running=()=>['preparing','running','stopping'].includes(job.state);
  function controls(){
    const disabled=loading||starting||running()||!selection.size||!document.getElementById('bus-test-connection').value;
    for(const mode of ['alarm','normal','pulse'])document.getElementById('bus-test-'+mode).disabled=disabled;
    document.getElementById('bus-test-stop').disabled=!running()||job.state==='stopping';
    document.getElementById('bus-test-connection').disabled=running()||starting||document.getElementById('bus-test-connection').options.length<=1;
    for(const input of document.querySelectorAll('#bus-test-rows input'))input.disabled=running()||starting||!input.dataset.ready;
  }
  function showStatus(){
    const message=job.state==='idle'?'':`${job.sent||0} / ${job.total||0} gesendet · ${job.message||job.state}`;
    document.getElementById('bus-test-summary').textContent=message;
    const matches=!singleId||(job.mode==='pulse'&&job.alarm_ids?.includes(singleId));
    if(!loading&&message&&matches&&(!singleId||running()||observed)){
      document.getElementById('bus-test-feedback').textContent=singleId?(job.state==='complete'?'Test abgeschlossen. Mailversand bleibt ausgeschaltet.':job.state==='running'?'Test läuft …':job.message||job.state):message;
      if(singleId&&job.group_address)document.getElementById('bus-test-value').textContent=`GA ${job.group_address} · ${job.phase==='alarm'?'Alarm':'Normal'}: ${job.value}`;
    }
    controls();
  }
  function connections(){
    const select=document.getElementById('bus-test-connection'),previous=select.value;
    select.replaceChildren();
    for(const connection of knx.connections||[]){if(connection.state!=='CONNECTED')continue;const option=document.createElement('option');option.value=connection.name;option.textContent=connection.name;select.append(option);}
    if([...select.options].some(o=>o.value===previous))select.value=previous;
  }
  async function open(id=''){
    if(!access.configure)return;
    if(page==='/matrix'&&matrixDirty){document.getElementById('matrix-feedback').textContent='Vor dem Test Änderungen speichern.';return;}
    if(!dialog.open)dialog.showModal();
    singleId=id;observed=false;dialog.classList.toggle('single-bus-test',Boolean(id));
    document.getElementById('bus-test-title').textContent=id?'Alarm testen':'KNX-Testmodus · Ersteinrichtung';
    for(const node of dialog.querySelectorAll('[data-bus-test-bulk]'))node.hidden=Boolean(id);
    for(const mode of ['alarm','normal','stop'])document.getElementById('bus-test-'+mode).hidden=Boolean(id);
    document.getElementById('bus-test-pulse').hidden=!id;
    document.getElementById('bus-test-single-note').hidden=!id;document.getElementById('bus-test-value').hidden=!id;
    document.getElementById('bus-test-value').textContent='';
    loading=true;plan=null;selection.clear();document.getElementById('bus-test-rows').replaceChildren();document.getElementById('bus-test-feedback').textContent='Testwerte werden geprüft …';controls();
    try{
      plan=await api('/api/knx/test/plan'+(id?'?alarm_id='+encodeURIComponent(id):''));
      const fragment=document.createDocumentFragment();
      for(const row of plan.rows){
        const tr=document.createElement('tr'),choice=document.createElement('input');choice.type='checkbox';choice.checked=row.ready;choice.dataset.ready=row.ready?'yes':'';choice.disabled=!row.ready;choice.setAttribute('aria-label','Test für '+row.name);
        if(row.ready)selection.add(row.id);
        choice.onchange=()=>{if(choice.checked)selection.add(row.id);else selection.delete(row.id);controls();};const td=document.createElement('td');td.append(choice);tr.append(td);
        for(const value of [row.name+' · '+row.group_address,row.dpt+' · '+row.operator+' '+JSON.stringify(row.threshold)+' · H '+row.hysteresis,row.ready?row.alarm:row.reason,row.ready?row.normal:'—']){const cell=document.createElement('td');cell.textContent=value;tr.append(cell);}fragment.append(tr);
      }
      document.getElementById('bus-test-rows').replaceChildren(fragment);connections();
      document.getElementById('bus-test-feedback').textContent=`${selection.size} von ${plan.rows.length} Einträgen testbar. Pro Durchlauf ca. ${Math.max(0,selection.size-1)} Sekunden zuzüglich Übertragungszeit. Nicht testbare Einträge werden nicht gesendet.`;
      if(id){const row=plan.rows[0];document.getElementById('bus-test-value').textContent=row?`GA ${row.group_address} · Alarm: ${row.alarm||'—'} → Normal: ${row.normal||'—'}`:'';document.getElementById('bus-test-feedback').textContent=row?.ready?'':row?.reason||'Eintrag nicht verfügbar.';}
      if(running()){showStatus();pollStatus();}
    }catch(error){document.getElementById('bus-test-feedback').textContent=error.message;}
    finally{loading=false;controls();}
  }
  async function start(mode){
    if(starting||running()||!plan)return;observed=true;starting=true;controls();
    document.getElementById('bus-test-feedback').textContent='Test wird angefordert; Mailversand wird vorher deaktiviert …';
    try{
      job=await api('/api/knx/test/start',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'test-knx'},body:JSON.stringify({ids:[...selection],mode,revision:plan.revision,connection:document.getElementById('bus-test-connection').value})});
      showStatus();pollStatus();refresh();
    }catch(error){document.getElementById('bus-test-feedback').textContent=error.message;}
    finally{starting=false;controls();}
  }
  function pollStatus(){
    clearTimeout(statusTimer);
    if(!dialog.open||!running())return;
    statusTimer=setTimeout(async()=>{
      try{job=await api('/api/knx/test/status');showStatus();}catch(error){document.getElementById('bus-test-feedback').textContent=error.message;}
      pollStatus();
    },300);
  }
  dialog.addEventListener('close',()=>clearTimeout(statusTimer));
  document.getElementById('bus-test-open').onclick=()=>open();
  document.getElementById('bus-test-close').onclick=()=>dialog.close();
  document.getElementById('bus-test-connection').onchange=controls;
  for(const mode of ['alarm','normal','pulse'])document.getElementById('bus-test-'+mode).onclick=()=>start(mode);
  document.getElementById('bus-test-stop').onclick=async()=>{try{job=await api('/api/knx/test/stop',{method:'POST',headers:{'X-Alarmserver-Action':'test-knx'}});showStatus();}catch(error){document.getElementById('bus-test-feedback').textContent=error.message;}};
  window.KnxBusTest={open,status(state){knx=state;job=state.test||{state:'idle'};connections();showStatus();}};
})();
