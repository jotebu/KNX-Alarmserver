'use strict';
(()=>{
  const dialog=document.getElementById('bus-test-dialog');
  let plan=null,knx={},loading=false,starting=false,job={state:'idle'},selection=new Set();
  const running=()=>['preparing','running','stopping'].includes(job.state);
  function controls(){
    const disabled=loading||starting||running()||!selection.size||!document.getElementById('bus-test-connection').value;
    for(const mode of ['alarm','normal'])document.getElementById('bus-test-'+mode).disabled=disabled;
    document.getElementById('bus-test-stop').disabled=!running()||job.state==='stopping';
    document.getElementById('bus-test-connection').disabled=running()||starting;
    for(const input of document.querySelectorAll('#bus-test-rows input'))input.disabled=running()||starting||!input.dataset.ready;
  }
  function showStatus(){
    const message=job.state==='idle'?'':`${job.sent||0} / ${job.total||0} gesendet · ${job.message||job.state}`;
    document.getElementById('bus-test-summary').textContent=message;
    if(!loading&&message)document.getElementById('bus-test-feedback').textContent=message;
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
      if(running())showStatus();
    }catch(error){document.getElementById('bus-test-feedback').textContent=error.message;}
    finally{loading=false;controls();}
  }
  async function start(mode){
    if(starting||running()||!plan)return;starting=true;controls();
    document.getElementById('bus-test-feedback').textContent='Test wird angefordert; Mailversand wird vorher deaktiviert …';
    try{
      job=await api('/api/knx/test/start',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'test-knx'},body:JSON.stringify({ids:[...selection],mode,revision:plan.revision,connection:document.getElementById('bus-test-connection').value})});
      showStatus();refresh();
    }catch(error){document.getElementById('bus-test-feedback').textContent=error.message;}
    finally{starting=false;controls();}
  }
  document.getElementById('bus-test-open').onclick=()=>open();
  document.getElementById('bus-test-close').onclick=()=>dialog.close();
  document.getElementById('bus-test-connection').onchange=controls;
  for(const mode of ['alarm','normal'])document.getElementById('bus-test-'+mode).onclick=()=>start(mode);
  document.getElementById('bus-test-stop').onclick=async()=>{try{job=await api('/api/knx/test/stop',{method:'POST',headers:{'X-Alarmserver-Action':'test-knx'}});showStatus();}catch(error){document.getElementById('bus-test-feedback').textContent=error.message;}};
  window.KnxBusTest={open,status(state){knx=state;job=state.test||{state:'idle'};connections();showStatus();}};
})();
