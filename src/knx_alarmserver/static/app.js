'use strict';
const $ = id => document.getElementById(id);
const labels = {unknown:'Unbekannt',active:'Störung aktiv',active_ack:'Aktiv · quittiert',clear_pending:'Gegangen · unquittiert',normal:'Normal'};
let view = 'alarms', data = {alarms:[],history:[],telegrams:[]}, busy = false;
const date = value => value ? new Date(value).toLocaleString('de-DE') : '—';
const text = (tag, value, cls) => {const node=document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node;};
async function api(path, options={}) {
  const response=await fetch(path,{...options,cache:'no-store',credentials:'same-origin'});
  if(!response.ok) throw new Error(response.status===401?'Anmeldung abgelaufen. Seite neu laden.':`Anfrage fehlgeschlagen (${response.status})`);
  return response.json();
}
function failure(error) {$('error').hidden=false;$('error').textContent=`Keine aktuellen Daten: ${error.message}. Die angezeigten Werte können veraltet sein.`;}
function render(){
  $('filter-wrap').hidden=view!=='alarms';
  const titles={alarms:'Meldungen',history:'Historie',telegrams:'Telegramme'};
  $('view-title').textContent=titles[view];
  const heads={alarms:['Status','Meldung / Bereich','Wert / Regel','Letzter Empfang','Quittierung'],history:['Zeitpunkt','Meldung','Ereignis','Benutzer / Quelle'],telegrams:['Zeitpunkt','Verbindung','Quelle → Ziel','Dienst / DPT','Wert']};
  const head=document.createElement('tr');for(const label of heads[view])head.append(text('th',label));$('table-head').replaceChildren(head);
  const query=$('search').value.toLocaleLowerCase('de');
  const rows=data[view].filter(r=>JSON.stringify(r).toLocaleLowerCase('de').includes(query)).filter(r=>view!=='alarms'||!$('open-only').checked||r.status!=='normal'||r.quality!=='ok');
  if(view==='alarms')rows.sort((a,b)=>({active:0,clear_pending:1,active_ack:2,unknown:3,normal:4}[a.status]-{active:0,clear_pending:1,active_ack:2,unknown:3,normal:4}[b.status]));
  const body=document.createDocumentFragment();
  for(const row of rows){
    const tr=document.createElement('tr');
    const cell=(value)=>{const td=text('td',value);tr.append(td);return td;};
    if(view==='alarms'){
      const state=cell('');state.append(text('span',labels[row.status],'badge '+row.status));
      if(!row.fresh)state.append(text('small',row.last_seen?'Wert vor Neustart':'Noch kein Wert empfangen'));
      if(row.decode_error)state.append(text('small','DPT-/Regelfehler: '+row.decode_error));
      const name=cell(row.name);name.append(text('small',`${row.area} · ${row.priority}`));
      const value=cell(row.display_value===null?'—':`${row.display_value}${row.unit?' '+row.unit:''}`);
      value.append(text('small',`${row.group_address} · DPT ${row.dpt}`));
      value.append(text('small',row.operator==='monitor'?'Nur Anzeige':`${row.field?row.field+' ':''}${row.operator} ${JSON.stringify(row.threshold)}${row.hysteresis?' · Hysterese '+row.hysteresis:''}`));
      cell(date(row.last_seen));
      const ack=cell(row.acknowledged_by?`${row.acknowledged_by} · ${date(row.acknowledged_at)}`:'—');
      if(row.pending){ack.textContent='';const button=text('button','Quittieren','ack');button.onclick=async()=>{button.disabled=true;try{await api(`/api/alarms/${encodeURIComponent(row.id)}/acknowledge`,{method:'POST',headers:{'X-Alarmserver-Action':'acknowledge'}});await refresh();}catch(e){failure(e);}finally{button.disabled=false;}};ack.append(button);}
    }else if(view==='history'){
      cell(date(row.timestamp));cell(row.alarm_name);cell({active:'Störung gekommen',clear:'Störung gegangen',acknowledge:'Quittiert'}[row.kind]||row.kind);cell(row.username||row.source||'—');
    }else{cell(date(row.timestamp));cell(row.connection);cell(`${row.source} → ${row.destination}`);cell(row.service+(row.dpt?' · '+row.dpt:''));cell(row.error||row.display||(row.raw===undefined?'—':JSON.stringify(row.raw)));}
    body.append(tr);
  }
  $('table-body').replaceChildren(body);$('empty').hidden=rows.length>0;
  $('empty').textContent=view==='alarms'&&!data.alarms.length?'Noch keine Alarmmatrix hinterlegt. alarms.csv einrichten und Dienst neu starten.':'Keine passenden Einträge.';
  $('hint').textContent={alarms:'Nach einem Neustart bleiben gespeicherte Zustände als alte Werte gekennzeichnet, bis ein neues Telegramm eintrifft. „Normal“ bedeutet zuletzt empfangener Normalwert; es ist keine zyklische Erreichbarkeitsprüfung.',history:'Die letzten 200 Ereignisse. Quittierungen ändern ausschließlich den lokalen Alarmstatus.',telegrams:'Die letzten 250 empfangenen Gruppentelegramme im Arbeitsspeicher. Routing bestätigt keine Erreichbarkeit eines bestimmten Routers.'}[view];
}
async function refresh(){
  if(busy)return;busy=true;
  try{
    const status=await api('/api/status');
    // Sequential authenticated calls avoid a burst of expensive password verifications.
    data.alarms=await api('/api/alarms');
    data[view]=view==='alarms'?data.alarms:await api('/api/'+view);
    $('identity').textContent=`${status.user} · Version ${status.version}`;
    $('active').textContent=data.alarms.filter(r=>r.status==='active').length;
    $('acked').textContent=data.alarms.filter(r=>r.status==='active_ack').length;
    $('pending').textContent=data.alarms.filter(r=>r.status==='clear_pending').length;
    $('unknown').textContent=data.alarms.filter(r=>r.quality!=='ok').length;
    $('connection-status').textContent=!status.knx.enabled?'KNX deaktiviert':status.knx.ready?'Verbindungen bereit':'Verbindung gestört / wird aufgebaut';
    $('connection-detail').textContent=status.knx.connections.map(c=>`${c.name}: ${c.state} · letzter Empfang ${date(c.last_received)}`).join(' | ')||'KNX-Empfang in der Konfiguration noch nicht aktiviert.';
    if(status.knx.storage_error)$('connection-detail').textContent+=' | FEHLER beim Speichern; Dienstprotokoll prüfen.';
    $('clock').textContent='Aktualisiert: '+new Date().toLocaleTimeString('de-DE');$('error').hidden=true;render();
  }catch(error){failure(error);}finally{busy=false;}
}
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{view=button.dataset.view;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('selected',b===button));render();refresh();});
$('search').oninput=render;$('open-only').onchange=render;
refresh();setInterval(refresh,5000);
