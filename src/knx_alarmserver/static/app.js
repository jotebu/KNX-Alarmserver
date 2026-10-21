'use strict';
const $ = id => document.getElementById(id);
const labels = {unknown:'Unbekannt',active:'Störung aktiv',active_ack:'Aktiv · quittiert',clear_pending:'Gegangen · unquittiert',normal:'Normal'};
const page=window.location.pathname;
const managementPages=['/knx','/ets','/users','/priorities'];
let pageInitialized=false, newerVersionKnown=false, checkingVersionStatus=false;
let access = {role:null,configure:false,acknowledge:false};
let view = page==='/telegrams'?'telegrams':'alarms', data = {alarms:[],history:[],telegrams:[]}, busy = false;
let listing=null, listGeneration=0, alarmStatusFilter='';
let listFilters={search:'',from:'',until:''};
function listQuery(selected){
  let query='&list_mode=true&search='+encodeURIComponent(listFilters.search);
  if(selected==='alarms'&&alarmStatusFilter)query+='&status_filter='+encodeURIComponent(alarmStatusFilter);
  if(listFilters.from)query+='&from_time='+encodeURIComponent(listFilters.from);
  if(listFilters.until)query+='&until_time='+encodeURIComponent(listFilters.until);
  return query;
}
const date = value => value ? new Date(value).toLocaleString('de-DE') : '—';
const text = (tag, value, cls) => {const node=document.createElement(tag);node.textContent=value;if(cls)node.className=cls;return node;};
async function api(path, options={}) {
  const controller=new AbortController();
  const timeoutMs=options.method && options.method!=='GET'?30000:path.startsWith('/api/version')||path==='/api/update'?20000:10000;
  const deadline=setTimeout(()=>controller.abort(),timeoutMs);
  try{
    const response=await fetch(path,{...options,cache:'no-store',credentials:'same-origin',signal:controller.signal});
    if(!response.ok){if(response.status===401)window.location.replace('/login');let message;try{message=(await response.json()).detail;}catch(error){if(controller.signal.aborted)throw error;}throw new Error(response.status===401?'Anmeldung erforderlich. Seite neu laden.':message||`Anfrage fehlgeschlagen (${response.status})`);}
    return await response.json();
  }catch(error){
    if(controller.signal.aborted)throw new Error(`Server antwortet seit ${timeoutMs/1000} Sekunden nicht. Verbindung wird erneut geprüft.`);
    throw error;
  }finally{clearTimeout(deadline);}
}
let pollTimer=null, refreshFailures=0;
function scheduleRefresh(){
  clearTimeout(pollTimer);
  if(document.hidden)return;
  const delay=Math.min(30000,5000*2**Math.min(refreshFailures,3));
  pollTimer=setTimeout(()=>refresh(),delay);
}
function failure(error) {$('error').hidden=false;$('error').textContent=`Keine aktuellen Daten: ${error.message}. Die angezeigten Werte können veraltet sein.`;}
function render(){
  if(settingsOpen)return;
  for(const card of document.querySelectorAll('[data-status-filter]')){const selected=view==='alarms'&&card.dataset.statusFilter===alarmStatusFilter;card.classList.toggle('selected',selected);card.setAttribute('aria-pressed',String(selected));}
  const filterable=view!=='telegrams';
  $('filter-toggle').hidden=!filterable;
  $('list-filters').hidden=filterable&&!filtersOpen;
  $('date-filters').hidden=!filterable;
  $('date-hint').textContent=view==='history'?'Filter: Ereigniszeitpunkt':'Filter: Zeitstempel; ohne Empfangszeit nicht im Datumsfilter enthalten';
  const active=Boolean(listFilters.search||listFilters.from||listFilters.until||(view==='alarms'&&alarmStatusFilter));
  $('filter-toggle').textContent=(filtersOpen?'Filter ausblenden':'Filter anzeigen')+(active?' · aktiv':'');
  $('filter-toggle').setAttribute('aria-expanded',String(filtersOpen));
  $('list-summary').textContent=listing?(view==='history'?`${listing.shown} von ${listing.total} Treffern · höchstens 500 neueste Einträge`:`${listing.total} Meldungen${alarmStatusFilter?' · '+({active:'Aktiv · offen',active_ack:'Aktiv · quittiert',clear_pending:'Gegangen · offen',unknown:'Unbekannt'})[alarmStatusFilter]:''}`):'';
  const titles={alarms:'Meldungen',history:'Historie',telegrams:'Telegramme'};
  $('view-title').textContent=titles[view];
  const heads={alarms:['Status','Meldung / Bereich','Status','Zeitstempel','Quittierung'],history:['Zeitpunkt','Meldung','Ereignis','Benutzer / Quelle'],telegrams:['Zeitpunkt','Verbindung','Quelle → Ziel','Dienst / DPT','Wert']};
  $('message-table').className=view==='alarms'?'alarm-list-table':'';
  const head=document.createElement('tr');for(const label of heads[view])head.append(text('th',label));$('table-head').replaceChildren(head);
  const query=$('search').value.toLocaleLowerCase('de');
  const rows=listing&&view!=='telegrams'?data[view]:data[view].filter(r=>JSON.stringify(r).toLocaleLowerCase('de').includes(query)).filter(r=>view!=='alarms'||(alarmStatusFilter?r.status===alarmStatusFilter:['active','active_ack','clear_pending'].includes(r.status)));
  if(view==='alarms'&&!listing)rows.sort((a,b)=>Number(a.priority)-Number(b.priority)||(Date.parse(b.last_seen)||0)-(Date.parse(a.last_seen)||0)||String(a.id).localeCompare(String(b.id)));
  const body=document.createDocumentFragment();
  for(const row of rows){
    const tr=document.createElement('tr');
    const cell=(value)=>{const td=text('td',value);tr.append(td);return td;};
    if(view==='alarms'){
      const state=cell('');state.append(text('span',labels[row.status],'badge '+row.status));
      if(row.decode_error)state.append(text('small','DPT-/Regelfehler: '+row.decode_error));
      const name=cell(row.name);name.append(text('small',`${row.area} · Priorität ${row.priority}${row.priority_name?' · '+row.priority_name:''}`));
      const value=cell(row.display_value===null?'—':`${row.display_value}${row.unit?' '+row.unit:''}`);
      name.append(text('small',`${row.group_address} · DPT ${row.dpt}`));
      cell(date(row.last_seen));
      const ack=cell(row.acknowledged_by?`${row.acknowledged_by} · ${date(row.acknowledged_at)}`:'—');
      if(row.pending && access.acknowledge){ack.textContent='';const button=text('button','Quittieren','ack');button.onclick=async()=>{button.disabled=true;try{await api(`/api/alarms/${encodeURIComponent(row.id)}/acknowledge`,{method:'POST',headers:{'X-Alarmserver-Action':'acknowledge'}});await refresh();}catch(e){failure(e);}finally{button.disabled=false;}};ack.append(button);}
    }else if(view==='history'){
      cell(date(row.timestamp));cell(row.alarm_name);cell({active:'Störung gekommen',clear:'Störung gegangen',acknowledge:'Quittiert',matrix_added:'Alarm angelegt',matrix_updated:'Alarmkonfiguration geändert',matrix_removed:'Alarm entfernt'}[row.kind]||row.kind);cell(row.username||row.source||'—');
    }else{cell(date(row.timestamp));cell(row.connection);const target=cell(`${row.source} → ${row.destination}`);if(row.name)target.append(text('small',row.name));if(row.ets_warning)target.append(text('small',row.ets_warning));cell(row.service+(row.dpt?' · '+row.dpt:''));cell(row.error||(row.display!==undefined?row.display+(row.unit?' '+row.unit:''):(row.raw===undefined?'—':JSON.stringify(row.raw))));}
    body.append(tr);
  }
  $('table-body').replaceChildren(body);$('empty').hidden=rows.length>0;
  $('empty').textContent=view==='alarms'&&!data.alarms.length?'Noch keine Alarmmatrix hinterlegt. Admins und User können Alarme im Bereich Alarmmatrix einrichten.':view==='alarms'?(alarmStatusFilter==='unknown'?'Keine unbekannten Meldungen.':'Keine aktiven oder noch zu quittierenden Meldungen.'):'Keine passenden Einträge.';
  $('hint').textContent={alarms:'Aktive oder noch zu quittierende Alarme und Störungen. Sortierung: Priorität, danach neuester Zeitstempel.',history:'Die neuesten 500 passenden Ereignisse. Filter durchsuchen die gesamte gespeicherte Historie. Quittierungen ändern ausschließlich den lokalen Alarmstatus. Die konfigurierte Aufbewahrungsdauer gilt weiterhin.',telegrams:'Die letzten 250 empfangenen Gruppentelegramme im Arbeitsspeicher. Routing bestätigt keine Erreichbarkeit eines bestimmten Routers.'}[view];
}
async function refresh(){
  if(busy)return;
  clearTimeout(pollTimer);busy=true;
  const generation=listGeneration;
  try{
    const requestedView=settingsOpen?'alarms':view;
    const snapshot=await api('/api/dashboard?view='+encodeURIComponent(requestedView)+(!settingsOpen&&requestedView!=='telegrams'?listQuery(requestedView):''));
    if(generation!==listGeneration)return;
    listing=snapshot.list_info||null;
    const status=snapshot.status;
    access={role:status.role,matrix:['admin','user'].includes(status.role),...status.permissions};
    applyAccess();
    data.alarms=snapshot.alarms;
    if(requestedView!=='alarms')data[requestedView]=snapshot[requestedView];
    $('identity').textContent=({admin:'Admin',user:'User',viewer:'Viewer'})[status.role]||'';
    $('profile-user').textContent=status.user;
    $('update-version').textContent=status.version;
    $('version-link').textContent='Version '+status.version;
    $('active').textContent=snapshot.counts?snapshot.counts.active:data.alarms.filter(r=>r.status==='active').length;
    $('acked').textContent=snapshot.counts?snapshot.counts.acked:data.alarms.filter(r=>r.status==='active_ack').length;
    $('pending').textContent=snapshot.counts?snapshot.counts.pending:data.alarms.filter(r=>r.status==='clear_pending').length;
    $('unknown').textContent=snapshot.counts?snapshot.counts.unknown:data.alarms.filter(r=>r.status==='unknown').length;
    $('connection-status').textContent=!status.knx.enabled?'KNX deaktiviert':status.knx.ready?'Verbindungen bereit':'Verbindung gestört / wird aufgebaut';
    $('connection-detail').textContent=status.knx.connections.map(c=>`${c.name}: ${c.state} · letzter Empfang ${date(c.last_received)}`).join(' | ')||'KNX-Empfang in der Konfiguration noch nicht aktiviert.';
    if(status.knx.storage_error)$('connection-detail').textContent+=' | FEHLER beim Speichern; Dienstprotokoll prüfen.';
    const knxColor=status.knx.storage_error?'red':!status.knx.enabled?'yellow':status.knx.ready?'green':'red';
    setKnxIndicator(knxColor,$('connection-status').textContent);
    renderReadStatus(status.knx);
    if(!pageInitialized){pageInitialized=true;await initializePage();}
    $('clock').textContent='Aktualisiert: '+new Date().toLocaleTimeString('de-DE');$('error').hidden=true;refreshFailures=0;render();
  }catch(error){refreshFailures+=1;setKnxIndicator('red','Server nicht erreichbar; KNX-Status unbekannt');failure(error);}finally{busy=false;if(generation!==listGeneration)refresh();else scheduleRefresh();}
}
let settingsOpen=managementPages.includes(page)||page==='/account/password'||page==='/versions'||page==='/matrix', knxConfig=null, knxRevision=null, editingConnection=null, savingKnx=false;
function knxFeedback(message){$('knx-feedback').textContent=message;}
function renderKnx(){
  $('knx-enabled').checked=knxConfig.enabled;
  const list=document.createDocumentFragment();
  if(!knxConfig.connections.length)list.append(text('p','Noch keine Verbindung eingerichtet. Klicke auf „Verbindung hinzufügen“.'));
  for(const [index, connection] of knxConfig.connections.entries()){
    const row=document.createElement('article');row.className='knx-connection';
    row.append(text('strong',connection.name));
    row.append(text('p',`${connection.type==='routing'?'Routing':'Tunneling'} · ${connection.gateway_ip||connection.multicast_group||'224.0.23.12'} · ${connection.enabled===false?'Deaktiviert':'Aktiv'}`));
    const edit=text('button','Bearbeiten');edit.type='button';edit.onclick=()=>openKnxForm(index);
    const remove=text('button','Löschen');remove.type='button';remove.onclick=async()=>{
      if(!confirm(`Verbindung „${connection.name}“ löschen?`))return;
      const next=structuredClone(knxConfig);next.connections.splice(index,1);
      if(!next.connections.some(c=>c.enabled!==false))next.enabled=false;
      await saveKnx(next);
    };
    row.append(edit,remove);list.append(row);
  }
  $('knx-list').replaceChildren(list);
}
async function loadKnx(){
  try{const result=await api('/api/knx/config');knxConfig=result.config;knxRevision=result.revision;renderKnx();$('knx-form').hidden=true;knxFeedback('Konfiguration geladen.');}
  catch(error){knxFeedback(error.message);}
}
function switchKnxType(){const routing=$('knx-type').value==='routing';$('knx-routing-fields').hidden=!routing;$('knx-routing-fields').disabled=!routing;$('knx-tunnel-fields').hidden=routing;$('knx-tunnel-fields').disabled=routing;}
function openKnxForm(index=null){
  if(!knxConfig)return;
  editingConnection=index;const c=index===null?{}:knxConfig.connections[index];
  $('knx-form-title').textContent=index===null?'Neue Verbindung':'Verbindung bearbeiten';
  $('knx-name').value=c.name||'';$('knx-type').value=c.type||'tunneling';$('knx-connection-enabled').checked=c.enabled!==false;
  $('knx-gateway').value=c.gateway_ip||'';$('knx-port').value=c.gateway_port||3671;$('knx-local').value=c.local_ip||'';
  $('knx-individual').value=c.individual_address||'';$('knx-multicast').value=c.multicast_group||'224.0.23.12';
  switchKnxType();$('knx-form').hidden=false;$('knx-name').focus();
}
async function saveKnx(next){
  if(savingKnx)return;savingKnx=true;
  const controls=[...$('knx-settings').querySelectorAll('button,input,select')];const disabled=controls.map(c=>c.disabled);controls.forEach(c=>c.disabled=true);
  try{
    const result=await api('/api/knx/config',{method:'PUT',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'configure-knx'},body:JSON.stringify({config:next,revision:knxRevision})});
    knxConfig=result.config;knxRevision=result.revision;renderKnx();$('knx-form').hidden=true;
    knxFeedback('Gespeichert. Verbindungen werden neu aufgebaut; Status am KNX-Symbol und Telegrammempfang prüfen.');await refresh();
  }catch(error){knxFeedback(error.message+' Bei fehlender Speicherbestätigung bitte Neu laden und den gespeicherten Stand prüfen.');}
  finally{controls.forEach((c,i)=>c.disabled=disabled[i]);savingKnx=false;switchKnxType();}
}
$('knx-add').onclick=()=>openKnxForm();$('knx-cancel').onclick=()=>{$('knx-form').hidden=true;};$('knx-type').onchange=switchKnxType;
$('knx-reload').onclick=loadKnx;
$('knx-apply').onclick=()=>{if(knxConfig){const next=structuredClone(knxConfig);next.enabled=$('knx-enabled').checked;saveKnx(next);}};
$('knx-form').onsubmit=event=>{
  event.preventDefault();if(!knxConfig)return;
  const c={name:$('knx-name').value.trim(),type:$('knx-type').value,enabled:$('knx-connection-enabled').checked};
  if($('knx-local').value.trim())c.local_ip=$('knx-local').value.trim();
  if(c.type==='tunneling'){c.gateway_ip=$('knx-gateway').value.trim();c.gateway_port=Number($('knx-port').value);}
  else{c.individual_address=$('knx-individual').value.trim();c.multicast_group=$('knx-multicast').value.trim();}
  const next=structuredClone(knxConfig);next.enabled=$('knx-enabled').checked;
  if(editingConnection===null)next.connections.push(c);else next.connections[editingConnection]=c;
  saveKnx(next);
};
document.querySelectorAll('[data-status-filter]').forEach(card=>card.onclick=()=>{
  alarmStatusFilter=alarmStatusFilter===card.dataset.statusFilter?'':card.dataset.statusFilter;
  view='alarms';listing=null;listGeneration++;
  document.querySelectorAll('[data-view]').forEach(button=>button.classList.toggle('selected',button.dataset.view==='alarms'));
  refresh();
});
document.querySelectorAll('[data-view]').forEach(button=>button.onclick=()=>{view=button.dataset.view;listing=null;listGeneration++;document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('selected',b===button));refresh();});
let etsRows=[], etsPage=0, etsPreview=null, etsFile=null, etsBusy=false;
function resetEtsPreview(){etsPreview=null;etsFile=null;$('ets-apply').disabled=true;}
function renderEts(){
  const query=$('ets-search').value.toLocaleLowerCase('de');
  const rows=etsRows.filter(r=>JSON.stringify(r).toLocaleLowerCase('de').includes(query));
  const pages=Math.max(1,Math.ceil(rows.length/100));etsPage=Math.min(etsPage,pages-1);
  const body=document.createDocumentFragment();
  for(const row of rows.slice(etsPage*100,(etsPage+1)*100)){
    const tr=document.createElement('tr');tr.append(text('td',row.address));
    const name=text('td',row.name);if(row.description)name.append(text('small',row.description));tr.append(name);
    tr.append(text('td',row.dpts.join(', ')||row.dpt_source||'—'));
    const detail=text('td',row.warnings.join('; ')||'OK');
    if(row.change)detail.append(text('small',({new:'Neu',updated:'Wird aktualisiert',unchanged:'Unverändert'})[row.change]));
    tr.append(detail);body.append(tr);
  }
  $('ets-rows').replaceChildren(body);$('ets-page').textContent=`Seite ${etsPage+1} / ${pages} · ${rows.length} Adressen`;
  $('ets-prev').disabled=etsPage===0;$('ets-next').disabled=etsPage===pages-1;
}
async function loadEts(){
  if(etsBusy)return;
  resetEtsPreview();
  try{const result=await api('/api/ets');etsRows=result.entries;etsPage=0;renderEts();$('ets-summary').textContent=`${result.count} Gruppenadressen gespeichert.`;$('ets-feedback').textContent='Gespeicherter Katalog geladen.';}
  catch(error){$('ets-feedback').textContent=error.message;}
}
async function etsAction(action){
  if(etsBusy)return;
  const file=action==='preview'?$('ets-file').files[0]:etsFile;
  if(!file){$('ets-feedback').textContent='Bitte zuerst eine XML- oder CSV-Datei wählen und Vorschau prüfen.';return;}
  if(file.size>4*1024*1024){$('ets-feedback').textContent='Die Datei darf höchstens 4 MiB groß sein.';return;}
  const mode=$('ets-mode').value;
  if(action==='import' && mode==='replace' && !confirm('Den gesamten gespeicherten ETS-Katalog durch diese Datei ersetzen? Alarmregeln bleiben erhalten.'))return;
  etsBusy=true;
  const controls=[...$('ets-panel').querySelectorAll('button,input,select')];controls.forEach(c=>c.disabled=true);
  try{
    let url='/api/ets/'+action+'?filename='+encodeURIComponent(file.name);
    if(action==='import')url+='&mode='+mode+'&revision='+etsPreview.revision+'&digest='+etsPreview.digest;
    const result=await api(url,{method:'POST',headers:{'Content-Type':'application/octet-stream','X-Alarmserver-Action':'import-ets'},body:await file.arrayBuffer()});
    if(action==='preview'){
      etsFile=file;etsPreview=result;etsRows=result.entries;etsPage=0;
      $('ets-summary').textContent=`Vorschau: ${result.count} Adressen, davon ${result.warnings} mit Hinweisen. Bisher gespeichert: ${result.existing_count}.`;
      $('ets-feedback').textContent='Noch nichts gespeichert. Prüfe die Vorschau und wähle anschließend „Vorschau übernehmen“.';
    }else{
      resetEtsPreview();
      $('ets-summary').textContent=`Gespeichert: ${result.added} neu, ${result.updated} aktualisiert, ${result.removed} entfernt; insgesamt ${result.count} Adressen.`;
      etsRows=etsRows.map(({change,...row})=>row);
      $('ets-feedback').textContent='Import übernommen. Namen und DPT gelten für neu empfangene Telegramme. Der gespeicherte Gesamtkatalog kann oben geladen werden.';
    }
  }catch(error){if(action==='preview')resetEtsPreview();$('ets-feedback').textContent=error.message+' Bei fehlender Speicherbestätigung zuerst den gespeicherten Katalog laden und prüfen.';}
  finally{etsBusy=false;controls.forEach(c=>c.disabled=false);$('ets-apply').disabled=!etsPreview;renderEts();}
}
$('ets-form').onsubmit=event=>{event.preventDefault();etsAction('preview');};
$('ets-file').onchange=()=>{resetEtsPreview();$('ets-feedback').textContent='Datei gewählt. Bitte Vorschau prüfen.';};
$('ets-apply').onclick=()=>etsAction('import');$('ets-reload').onclick=loadEts;
$('ets-search').oninput=()=>{etsPage=0;renderEts();};
$('ets-prev').onclick=()=>{etsPage--;renderEts();};$('ets-next').onclick=()=>{etsPage++;renderEts();};

let priorityEntries=[], priorityRevision=null, prioritiesBusy=false, prioritiesDirty=false;
function renderPriorities(){
  const fragment=document.createDocumentFragment();
  for(const entry of priorityEntries){
    const tr=document.createElement('tr'),number=document.createElement('input'),name=document.createElement('input');
    number.type='number';number.min='1';number.max='999';number.step='1';number.value=entry.priority;
    number.setAttribute('aria-label','Prioritätsnummer');name.setAttribute('aria-label','Bezeichnung');
    name.value=entry.name;name.maxLength=80;
    const changed=()=>{prioritiesDirty=true;$('priorities-feedback').textContent='Ungespeicherte Änderungen.';};
    number.oninput=()=>{entry.priority=Number(number.value);changed();};name.oninput=()=>{entry.name=name.value;changed();};
    for(const input of [number,name]){const td=document.createElement('td');td.append(input);tr.append(td);}
    const remove=text('button','Entfernen');remove.type='button';remove.onclick=()=>{priorityEntries=priorityEntries.filter(row=>row!==entry);changed();renderPriorities();};
    const td=document.createElement('td');td.append(remove);tr.append(td);fragment.append(tr);
  }
  $('priorities-rows').replaceChildren(fragment);
}
async function prioritiesOperation(work){
  if(prioritiesBusy)return;prioritiesBusy=true;
  const controls=[...$('priorities-panel').querySelectorAll('input,button')];controls.forEach(node=>node.disabled=true);
  try{await work();}catch(error){$('priorities-feedback').textContent=error.message;}
  finally{prioritiesBusy=false;controls.forEach(node=>node.disabled=false);}
}
function prioritiesReceived(result){priorityEntries=result.entries;priorityRevision=result.revision;prioritiesDirty=false;renderPriorities();}
async function loadPriorities(){
  if(prioritiesDirty&&!confirm('Ungespeicherte Prioritätsänderungen verwerfen?'))return;
  await prioritiesOperation(async()=>{prioritiesReceived(await api('/api/priorities'));$('priorities-feedback').textContent='Prioritäten geladen.';});
}
$('priorities-add').onclick=()=>{if(prioritiesBusy)return;priorityEntries.push({priority:Math.max(0,...priorityEntries.map(row=>row.priority))+1,name:''});prioritiesDirty=true;renderPriorities();};
$('priorities-reload').onclick=loadPriorities;
$('priorities-save').onclick=()=>prioritiesOperation(async()=>{
  if(priorityRevision===null)throw Error('Zuerst Prioritäten laden.');
  prioritiesReceived(await api('/api/priorities',{method:'PUT',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'manage-priorities'},body:JSON.stringify({entries:priorityEntries,revision:priorityRevision})}));
  $('priorities-feedback').textContent='Prioritäten gespeichert. Bezeichnungen werden im Dashboard sofort aktualisiert.';
});
window.addEventListener('beforeunload',event=>{if(prioritiesDirty){event.preventDefault();event.returnValue='';}});

let matrixRows=[], matrixRevision=null, matrixBusy=false, matrixDirty=false, matrixPage=0;
let matrixPriorities=[];
const matrixFields=['name','group_address','dpt','operator','threshold','hysteresis','field','area','priority'];
function matrixChanged(){matrixDirty=true;$('matrix-feedback').textContent='Ungespeicherte Änderungen.';}
function renderMatrix(){
  const fragment=document.createDocumentFragment();
  const query=$('matrix-search').value.trim().toLowerCase();
  const matching=matrixRows.filter(row=>[row.id,row.name,row.area,row.group_address,row.dpt].join(' ').toLowerCase().includes(query));
  matrixPage=Math.max(0,Math.min(matrixPage,Math.ceil(matching.length/100)-1));
  $('matrix-prev').disabled=matrixPage===0;$('matrix-next').disabled=(matrixPage+1)*100>=matching.length;
  $('matrix-page').textContent='Seite '+(matrixPage+1)+' / '+Math.max(1,Math.ceil(matching.length/100));
  for(const row of matching.slice(matrixPage*100,(matrixPage+1)*100)){
    const tr=document.createElement('tr');tr.append(text('td',row.id||'Wird vergeben'));
    for(const field of matrixFields){
      const td=document.createElement('td');
      const choices=field==='operator'?['eq','ne','gt','ge','lt','le','between','outside','contains','in','monitor']:field==='priority'?matrixPriorities.map(entry=>String(entry.priority)):null;
      const input=document.createElement(choices?'select':'input');
      if(choices)for(const choice of choices){const label=field==='priority'?choice+' · '+matrixPriorities.find(entry=>String(entry.priority)===choice).name:choice;const option=text('option',label);option.value=choice;input.append(option);}
      else{input.type='text';input.maxLength=field==='name'?200:2048;}
      input.value=row[field];input.setAttribute('aria-label',field+' · '+(row.id||'neuer Alarm'));
      input.oninput=()=>{row[field]=input.value;matrixChanged();};td.append(input);tr.append(td);
    }
    const td=document.createElement('td'),remove=text('button','Entfernen');remove.type='button';
    remove.onclick=()=>{if(row.id&&!confirm('Alarm „'+row.name+'“ aus der Matrix entfernen? Die Historie bleibt erhalten.'))return;matrixRows=matrixRows.filter(item=>item!==row);matrixChanged();renderMatrix();};td.append(remove);tr.append(td);fragment.append(tr);
  }
  $('matrix-rows').replaceChildren(fragment);$('matrix-count').textContent=matrixRows.length+' Alarme';
}
function matrixReceived(result){matrixRows=result.rows;matrixRevision=result.revision;matrixPriorities=result.priorities||[];matrixDirty=false;renderMatrix();}
async function loadMatrix(){
  if(matrixBusy)return;
  if(matrixDirty&&!confirm('Ungespeicherte Änderungen verwerfen?'))return;
  await matrixOperation(async()=>{matrixReceived(await api('/api/matrix'));$('matrix-feedback').textContent='Gespeicherte Matrix geladen.';});
}
async function matrixOperation(work){
  if(matrixBusy)return;matrixBusy=true;
  const controls=[...$('matrix-panel').querySelectorAll('button,input,select')];controls.forEach(node=>node.disabled=true);
  try{await work();}catch(error){$('matrix-feedback').textContent=error.message+' Bei fehlender Speicherbestätigung den gespeicherten Stand laden und prüfen.';}
  finally{matrixBusy=false;controls.forEach(node=>node.disabled=false);renderMatrix();}
}
$('matrix-add').onclick=()=>{
  if(matrixBusy)return;
  $('matrix-search').value='';matrixPage=Math.floor(matrixRows.length/100);
  matrixRows.push({id:'',name:'',group_address:'',dpt:'1.005',operator:'eq',threshold:'true',hysteresis:'0',field:'',area:'',priority:String(matrixPriorities.find(entry=>entry.priority===2)?.priority||matrixPriorities.at(-1)?.priority||2)});
  matrixChanged();renderMatrix();
};
$('matrix-search').oninput=()=>{matrixPage=0;renderMatrix();};
$('matrix-prev').onclick=()=>{matrixPage--;renderMatrix();};
$('matrix-next').onclick=()=>{matrixPage++;renderMatrix();};
$('matrix-reload').onclick=loadMatrix;
$('matrix-save').onclick=()=>matrixOperation(async()=>{
  if(matrixRevision===null)throw Error('Zuerst gespeicherte Matrix laden.');
  const result=await api('/api/matrix',{method:'PUT',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'manage-matrix'},body:JSON.stringify({rows:matrixRows,revision:matrixRevision})});
  matrixReceived(result);$('matrix-feedback').textContent='Alarmmatrix gespeichert und sofort aktiviert.';
});
$('matrix-import-form').onsubmit=event=>{
  event.preventDefault();
  if(matrixDirty){$('matrix-feedback').textContent='Manuelle Änderungen vor dem CSV-Import speichern oder verwerfen.';return;}
  matrixOperation(async()=>{
    if(matrixRevision===null)throw Error('Zuerst gespeicherte Matrix laden.');
    const file=$('matrix-file').files[0];if(!file)throw Error('CSV-Datei auswählen.');
    if(file.size>2*1024*1024)throw Error('CSV-Datei darf maximal 2 MiB groß sein.');
    const result=await api('/api/matrix/import',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'manage-matrix'},body:JSON.stringify({csv:await file.text(),revision:matrixRevision})});
    matrixReceived(result);$('matrix-file').value='';$('matrix-feedback').textContent='CSV vollständig übernommen; neue Alarme sofort aktiviert.';
  });
};
window.addEventListener('beforeunload',event=>{if(page==='/matrix'&&matrixDirty){event.preventDefault();event.returnValue='';}});

let startingRead=false;
function renderReadStatus(knx){
  const allowed=page==='/telegrams'&&view==='telegrams'&&access.configure;
  $('knx-read-controls').hidden=!allowed;$('knx-read-feedback').hidden=!allowed;
  if(!allowed)return;
  const select=$('knx-read-connection'),selected=select.value;
  const options=document.createDocumentFragment();const automatic=text('option','Erste aktive Verbindung');automatic.value='';options.append(automatic);
  for(const connection of knx.connections.filter(row=>row.state==='CONNECTED')){const option=text('option',connection.name);option.value=connection.name;options.append(option);}
  select.replaceChildren(options);select.value=[...select.options].some(option=>option.value===selected)?selected:'';
  const job=knx.read||{state:'idle'},running=job.state==='running';
  $('knx-read-start').disabled=startingRead||running||!knx.enabled||!knx.connections.some(row=>row.state==='CONNECTED');
  if(running)$('knx-read-feedback').textContent=`Statusabfrage: ${job.sent} / ${job.total} Leseanfragen gesendet; ${job.answered} gültige Antworten.`;
  else if(job.state==='complete')$('knx-read-feedback').textContent=`Statusabfrage beendet: ${job.sent} Anfragen, ${job.answered} gültige Antworten. Nicht beantwortete Adressen behalten ihren bisherigen Zustand.`;
  else if(job.state==='failed'||job.state==='cancelled')$('knx-read-feedback').textContent=job.message;
  else $('knx-read-feedback').textContent='Liest die Gruppenadressen der Alarmmatrix. Antworten erfordern das Lesen-Flag in ETS; Werte werden nicht geschrieben.';
}
$('knx-read-start').onclick=async()=>{
  if(startingRead||$('knx-read-start').disabled)return;startingRead=true;$('knx-read-start').disabled=true;
  try{
    await api('/api/knx/read',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'read-knx'},body:JSON.stringify({mode:$('knx-read-mode').value,connection:$('knx-read-connection').value})});
    $('knx-read-feedback').textContent='Statusabfrage gestartet.';
    await refresh();
  }catch(error){$('knx-read-feedback').textContent=error.message;}
  finally{startingRead=false;}
};

function applyAccess(){
  $('settings-menu').hidden=!access.configure&&!access.matrix;
  $('matrix-link').hidden=!access.matrix;
  for(const id of ['telegrams-link','knx-settings-tab','ets-tab','users-tab','priorities-link'])$(id).hidden=!access.configure;
  if(page==='/matrix'&&!access.matrix)window.location.replace('/');
  $('update-panel').hidden=page!=='/versions'||!access.configure||!newerVersionKnown;
  if(!access.configure && (managementPages.includes(page)||page==='/telegrams'))window.location.replace('/');
}
function setKnxIndicator(color,label){
  const icon=$('knx-status-icon');icon.className='icon-button status-'+color;icon.title=label;icon.setAttribute('aria-label',label);
}
async function initializePage(){
  if(page==='/matrix'&&access.matrix)await loadMatrix();
  else if(page==='/knx')await loadKnx();
  else if(page==='/ets')await loadEts();
  else if(page==='/users')await loadUsers();
  else if(page==='/priorities')await loadPriorities();
  else if(page==='/versions'){await loadVersions();if(access.configure)await loadUpdate();}
}
function layoutPage(){
  const names={'/priorities':['Prioritäten','Rangfolge und Bezeichnungen der Alarmprioritäten festlegen.'],
    '/matrix':['Alarmmatrix','Alarmregeln manuell bearbeiten oder als CSV ergänzen.'],
    '/telegrams':['Telegramme','Empfangene KNX-Gruppentelegramme und decodierte Werte.'],
    '/knx':['KNX Verbindungen','Verbindungen zum KNX-Netz verwalten.'],
    '/ets':['ETS-Import','Gruppenadressen und Datenpunkttypen importieren.'],
    '/users':['Benutzerverwaltung','Benutzerkonten, Kennwörter und Zugriffsrechte verwalten.'],
    '/account/password':['Kennwort ändern','Dein persönliches Kennwort aktualisieren.'],
    '/versions':['Versionshistorie','Änderungen, Softwarestand und verfügbare Updates.']};
  document.body.classList.toggle('scroll-list-page',!settingsOpen);
  const separate=page!=='/';
  $('counters').hidden=separate;$('main-nav').hidden=separate;$('back-dashboard').hidden=!separate;
  if(names[page]){$('page-title').textContent=names[page][0];$('page-description').textContent=names[page][1];document.title=names[page][0]+' · KNX Alarmserver';}
  $('data-panel').hidden=settingsOpen;
  $('knx-settings').hidden=page!=='/knx';$('ets-panel').hidden=page!=='/ets';$('users-panel').hidden=page!=='/users';
  $('priorities-panel').hidden=page!=='/priorities';
  $('matrix-panel').hidden=page!=='/matrix';
  $('password-panel').hidden=page!=='/account/password';$('versions-panel').hidden=page!=='/versions';
  $('update-panel').hidden=page!=='/versions'||!access.configure||!newerVersionKnown;
}
let editingUser=null, usersBusy=false;
function openUser(account=null){
  editingUser=account?account.username:null;
  $('users-form-title').textContent=account?'Benutzer bearbeiten':'Benutzer hinzufügen';
  $('users-name').value=editingUser||'';$('users-name').disabled=!!account;
  $('users-role').value=account?account.role:'viewer';
  for(const id of ['users-password','users-confirm']){$(id).value='';$(id).required=!account;}
  $('users-form').hidden=false;
}
async function loadUsers(){
  try{
    const accounts=await api('/api/users'),rows=document.createDocumentFragment();
    for(const account of accounts){
      const tr=document.createElement('tr');tr.append(text('td',account.username),text('td',{admin:'Admin',user:'User',viewer:'Viewer'}[account.role]));
      const td=document.createElement('td'),edit=text('button','Bearbeiten'),remove=text('button','Löschen');
      edit.type=remove.type='button';edit.onclick=()=>openUser(account);
      remove.onclick=async()=>{
        if(usersBusy||!confirm(`Benutzer „${account.username}“ löschen?`))return;
        await saveUser('/api/users/'+encodeURIComponent(account.username),'DELETE');
      };
      td.append(edit,remove);tr.append(td);rows.append(tr);
    }
    $('users-rows').replaceChildren(rows);
  }catch(error){$('users-feedback').textContent=error.message;}
}
async function saveUser(url,method,payload){
  if(usersBusy)return;usersBusy=true;
  const controls=[...$('users-panel').querySelectorAll('button,input,select')],disabled=controls.map(c=>c.disabled);
  controls.forEach(c=>c.disabled=true);
  try{
    await api(url,{method,headers:{'Content-Type':'application/json','X-Alarmserver-Action':'manage-users'},...(payload?{body:JSON.stringify(payload)}:{})});
    $('users-form').hidden=true;$('users-password').value='';$('users-confirm').value='';
    $('users-feedback').textContent='Gespeichert. Geänderte Konten müssen sich erneut anmelden.';
    await refresh();if(access.configure)await loadUsers();
  }catch(error){$('users-feedback').textContent=error.message+' Bei fehlender Bestätigung bitte Neu laden und den Stand prüfen.';}
  finally{controls.forEach((c,i)=>c.disabled=disabled[i]);usersBusy=false;}
}
$('users-add').onclick=()=>openUser();$('users-reload').onclick=loadUsers;
$('users-cancel').onclick=()=>{$('users-form').hidden=true;$('users-password').value='';$('users-confirm').value='';};
$('users-form').onsubmit=event=>{
  event.preventDefault();const password=$('users-password').value;
  if(password!==$('users-confirm').value){$('users-feedback').textContent='Passwörter stimmen nicht überein.';return;}
  const payload={role:$('users-role').value};
  if(editingUser===null){payload.username=$('users-name').value;payload.password=password;}else if(password)payload.password=password;
  saveUser('/api/users'+(editingUser===null?'':'/'+encodeURIComponent(editingUser)),editingUser===null?'POST':'PUT',payload);
};
$('logout').onclick=async()=>{try{await api('/api/logout',{method:'POST',headers:{'X-Alarmserver-Action':'logout'}});window.location.replace('/login');}catch(error){failure(error);}};

$('password-form').onsubmit=async event=>{
  event.preventDefault();
  if($('password-new').value!==$('password-confirm').value){$('password-feedback').textContent='Kennwörter stimmen nicht überein.';return;}
  $('password-save').disabled=true;
  try{
    await api('/api/account/password',{method:'POST',headers:{'Content-Type':'application/json','X-Alarmserver-Action':'change-password'},
      body:JSON.stringify({current_password:$('password-current').value,new_password:$('password-new').value})});
    $('password-form').reset();window.location.replace('/login');
  }catch(error){$('password-feedback').textContent=error.message;}
  finally{$('password-save').disabled=false;}
};
function renderVersionCheck(result){
  newerVersionKnown=Boolean(result.check_ok&&result.update_available);
  if(page==='/versions'&&result.check_ok){
    $('versions-feedback').textContent=result.update_available?'Neue Version '+result.latest_version+' verfügbar.':'Installierte Version ist aktuell.';
  }
  $('update-panel').hidden=page!=='/versions'||!access.configure||!newerVersionKnown;
  const link=$('version-link');link.textContent='Version '+result.current_version;
  link.classList.toggle('update-available',result.check_ok&&result.update_available);
  link.title=!result.check_ok?'Versionshistorie öffnen':result.update_available?'Neue Version '+result.latest_version+' verfügbar; Historie öffnen':'Aktuelle Version; Historie öffnen';
}
async function checkVersion(){
  try{renderVersionCheck(await api('/api/version?refresh=true'));}
  catch(error){$('version-link').title='Versionshistorie öffnen';}
}
async function loadVersions(force=false){
  try{
    const result=await api('/api/versions?refresh=true');renderVersionCheck(result);
    $('versions-feedback').textContent=!result.check_ok?(force?'Versionsstatus konnte nicht aktualisiert werden. Bitte später erneut prüfen.':''):result.update_available?'Neue Version '+result.latest_version+' verfügbar.':'Installierte Version ist aktuell.';
    if(force&&result.check_ok)$('versions-feedback').textContent+=' Geprüft: '+date(result.checked_at)+'.';
    if(result.history_source==='local')$('versions-feedback').textContent+=' Lokale Versionshistorie.';
    const history=document.createDocumentFragment();let list=null;
    for(const line of result.changelog.split('\n')){
      if(line.startsWith('# '))continue;
      if(line.startsWith('## ')){list=null;history.append(text('h3',line.slice(3)));}
      else if(line.startsWith('- ')){if(!list){list=document.createElement('ul');history.append(list);}list.append(text('li',line.slice(2)));}
      else if(line.trim()){list=null;history.append(text('p',line));}
    }
    $('versions-history').replaceChildren(history);
    return result.check_ok;
  }catch(error){
    newerVersionKnown=false;$('update-panel').hidden=true;$('update-start').disabled=true;
    $('version-link').classList.remove('update-available');
    $('versions-feedback').textContent=force?'Versionsstatus konnte nicht aktualisiert werden. Bitte später erneut prüfen.':'Versionshistorie konnte nicht geladen werden.';
    return false;
  }
}
async function checkVersionStatus(){
  if(checkingVersionStatus)return;
  checkingVersionStatus=true;
  const button=$('update-reload');button.disabled=true;button.textContent='Wird geprüft …';
  $('versions-panel').setAttribute('aria-busy','true');
  $('versions-feedback').textContent='Versionsstatus wird geprüft …';
  $('update-start').disabled=true;
  try{
    const checked=await loadVersions(true);
    if(access.configure&&checked)await loadUpdate();
  }finally{
    checkingVersionStatus=false;button.disabled=false;button.textContent='Status prüfen';
    $('versions-panel').setAttribute('aria-busy','false');
  }
}
let updatePoll=null;
let updateObserved=false;
let updateReloadTimer=null;
async function loadUpdate(){
  clearTimeout(updatePoll);
  try{
    const state=await api('/api/update');
    const active=['queued','fetching','installing'].includes(state.state);
    if(active)updateObserved=true;
    const showSuccess=state.state==='success'&&updateObserved;
    renderVersionCheck(state);
    $('update-version').textContent=state.current_version;
    $('update-start').disabled=!state.available||active||!state.check_ok||!state.update_available;
    $('update-refresh').hidden=!showSuccess;
    $('update-feedback').textContent=(state.state==='success'&&!showSuccess?'':state.message)||((newerVersionKnown&&!state.available)?'Update-Dienst fehlt. Bitte einmalig per PuTTY aktualisieren.':'');
    $('update-detail').textContent=state.target_version?'Zielversion: '+state.target_version+(state.updated_at?' · '+date(state.updated_at):''):'';
    if(showSuccess&&updateReloadTimer===null){
      updateReloadTimer=setTimeout(()=>window.location.reload(),500);
    }
    if(active)updatePoll=setTimeout(loadUpdate,3000);
  }catch(error){$('update-start').disabled=true;$('update-feedback').textContent='Verbindung unterbrochen. Der Status wird nach dem Neustart erneut geprüft.';updatePoll=setTimeout(loadUpdate,5000);}
}
$('update-start').onclick=async()=>{
  if($('update-start').disabled)return;
  $('update-start').disabled=true;
  try{
    const result=await api('/api/update',{method:'POST',headers:{'X-Alarmserver-Action':'update-server'}});
    updateObserved=true;
    $('update-feedback').textContent=result.message;await loadUpdate();
  }catch(error){$('update-feedback').textContent=error.message+' Bitte den Status prüfen, bevor du erneut startest.';await loadUpdate();}
};
$('update-reload').onclick=checkVersionStatus;
$('update-refresh').onclick=()=>window.location.reload();
// Native details menus support mouse, keyboard and touch; only one stays open.
const menus=[...document.querySelectorAll('.header-menu')];
for(const menu of menus)menu.addEventListener('toggle',()=>{if(menu.open)for(const other of menus)if(other!==menu)other.open=false;});
document.addEventListener('click',event=>{for(const menu of menus)if(!menu.contains(event.target))menu.open=false;});
document.addEventListener('keydown',event=>{if(event.key==='Escape')for(const menu of menus)menu.open=false;});
layoutPage();
if(page!=='/versions')checkVersion();
let searchTimer=null, filtersOpen=false;
$('filter-toggle').onclick=()=>{filtersOpen=!filtersOpen;render();};
function applyListFilters(){
  try{
    const from=$('date-from').value,until=$('date-until').value;
    if(from&&until&&from>until)throw Error('Von darf nicht nach Bis liegen.');
    const after=until?new Date(until+'T00:00:00'):null;if(after)after.setDate(after.getDate()+1);
    listFilters={search:$('search').value,
      from:from?new Date(from+'T00:00:00').toISOString():'',until:after?after.toISOString():''};
    listGeneration++;refresh();
  }catch(error){failure(error);}
}
$('search').oninput=()=>{if(view==='telegrams')render();else{clearTimeout(searchTimer);searchTimer=setTimeout(applyListFilters,300);}};
$('date-apply').onclick=applyListFilters;
$('date-clear').onclick=()=>{alarmStatusFilter='';$('date-from').value='';$('date-until').value='';$('search').value='';applyListFilters();};
document.addEventListener('visibilitychange',()=>{clearTimeout(pollTimer);if(!document.hidden)refresh();});
refresh();

