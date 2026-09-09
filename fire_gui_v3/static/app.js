const $=id=>document.getElementById(id);
const escapeHtml=value=>String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
let map,marker,footprint,contextCircle,historyLayer,surfaceRequest=0,lastPrediction=null,lastContext=null;
let chatMessages=[];

if(window.L){
  map=L.map('map').setView([-3.1,105.25],7);
  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap contributors'}).addTo(map);
  historyLayer=L.layerGroup().addTo(map);
  map.on('click',e=>selectCoordinate(e.latlng.lat,e.latlng.lng,true));
  let mapResizeTimer;
  const resizeMap=()=>{clearTimeout(mapResizeTimer);mapResizeTimer=setTimeout(()=>map.invalidateSize({pan:false}),100)};
  window.addEventListener('resize',resizeMap);
  if('ResizeObserver' in window)new ResizeObserver(resizeMap).observe($('map'));
}

function selectionPayload(){
  return {longitude:+$('longitude').value,latitude:+$('latitude').value,date:$('date').value,time:$('time').value,satellite:$('satellite').value,region:$('region').value,source:$('source').value,radius_km:+$('history-radius').value,lookback_days:$('history-lookback').value};
}

function clearMapAnalysis(){
  if(!map)return;
  if(footprint){map.removeLayer(footprint);footprint=null}
  if(contextCircle){map.removeLayer(contextCircle);contextCircle=null}
  if(historyLayer)historyLayer.clearLayers();
}
function plot(lat,lon,radius,p){
  if(!map)return;
  if(marker)map.removeLayer(marker);clearMapAnalysis();
  const color=p>=.5?'#d1495b':p>=.25?'#f28e2b':'#0b8f91';
  marker=L.marker([lat,lon]).addTo(map);
  footprint=L.circle([lat,lon],{radius,color,fillColor:color,fillOpacity:.17,weight:2}).addTo(map);
  marker.bindPopup(`<b>Alert location</b><br>${lat.toFixed(5)}, ${lon.toFixed(5)}`).openPopup();
  map.fitBounds(footprint.getBounds(),{maxZoom:14,padding:[40,40]});
}
function drawHistoryContext(data){
  if(!map)return;
  if(contextCircle)map.removeLayer(contextCircle);
  if(historyLayer)historyLayer.clearLayers();
  const q=data.query;
  contextCircle=L.circle([q.latitude,q.longitude],{radius:q.radius_km*1000,color:'#3568a8',fillColor:'#3568a8',fillOpacity:.035,weight:2,dashArray:'6 7'}).addTo(map);
  data.rows.forEach(row=>{
    const fire=row.status==='Verified Fire'||row.status==='Fire inside Sitrep';
    const color=fire?'#d1495b':row.status==='Unverified'?'#8a98a5':'#0b8f91';
    L.circleMarker([row.latitude,row.longitude],{radius:4,color,fillColor:color,fillOpacity:.75,weight:1}).bindPopup(`<b>${escapeHtml(row.status)}</b><br>${escapeHtml(formatDate(row.date))}<br>${row.distance_km.toFixed(3)} km away`).addTo(historyLayer);
  });
}
function selectionMarker(lat,lon,isLand){
  if(!map)return;
  if(marker)map.removeLayer(marker);clearMapAnalysis();
  const text=isLand===undefined?'Checking surface…':isLand?'Land selected':'Water selected — probability will be 0%';
  marker=L.marker([lat,lon]).addTo(map).bindPopup(`<b>${text}</b><br>${lat.toFixed(5)}, ${lon.toFixed(5)}`).openPopup();
}
async function selectCoordinate(lat,lon,fromMap=false){
  $('latitude').value=lat.toFixed(6);$('longitude').value=lon.toFixed(6);lastPrediction=null;
  selectionMarker(lat,lon);const id=++surfaceRequest;
  try{
    const r=await fetch(`/api/surface?latitude=${encodeURIComponent(lat)}&longitude=${encodeURIComponent(lon)}`);const d=await r.json();
    if(id!==surfaceRequest)return;selectionMarker(lat,lon,d.is_land);
    if(!d.is_land){
      $('result').classList.remove('empty');
      $('result').innerHTML='<div><span class="eyebrow">LAND/WATER SCREEN</span><h2>Water — both models will be skipped</h2><div class="model-note">Natural Earth classifies this coordinate as water. Near the coastline, confirm with a higher-resolution local shoreline.</div></div>';
    }else if(fromMap){
      $('result').classList.add('empty');$('result').innerHTML='<div><span class="eyebrow">LAND SELECTED</span><h2>Ready to score</h2><p>Press Calculate research scores to run both Version 3 references.</p></div>';
    }
  }catch(_){selectionMarker(lat,lon)}
}
$('longitude').addEventListener('change',()=>selectCoordinate(+$('latitude').value,+$('longitude').value));
$('latitude').addEventListener('change',()=>selectCoordinate(+$('latitude').value,+$('longitude').value));

function formatRate(value){return value===null||value===undefined?'—':`${Number(value).toFixed(1)}%`}
function formatRadius(value){return value<1?`${Math.round(value*1000)} m`:`${Number(value).toFixed(value%1?1:0)} km`}
function formatDate(value){return new Date(value).toLocaleString([], {year:'numeric',month:'short',day:'2-digit',hour:'2-digit',minute:'2-digit'})}
function renderContext(data){
  lastContext=data;$('history-state').hidden=true;$('history-content').hidden=false;
  $('stat-reports').textContent=data.summary.reports.toLocaleString();
  $('stat-fires').textContent=data.summary.fires.toLocaleString();
  $('stat-rate').textContent=formatRate(data.summary.fire_rate);
  $('stat-nearest').textContent=data.summary.nearest_km===null?'—':formatRadius(data.summary.nearest_km);
  $('distance-rows').innerHTML=data.distance_bands.map(row=>`<tr class="${row.radius_km===data.query.radius_km?'selected-row':''}"><td>${formatRadius(row.radius_km)}</td><td>${row.reports.toLocaleString()}</td><td>${row.fires.toLocaleString()}</td><td>${formatRate(row.fire_rate)}</td></tr>`).join('');
  $('year-rows').innerHTML=data.yearly.length?data.yearly.map(row=>`<tr><td>${row.year}</td><td>${row.reports.toLocaleString()}</td><td>${row.fires.toLocaleString()}</td><td>${formatRate(row.fire_rate)}</td></tr>`).join(''):'<tr><td colspan="4" class="no-data">No reports in this window</td></tr>';
  $('report-rows').innerHTML=data.rows.length?data.rows.map(row=>`<tr><td>${escapeHtml(formatDate(row.date))}</td><td>${row.distance_km.toFixed(3)} km</td><td><span class="status ${row.status.includes('Fire')&&!row.status.includes('No fire')?'fire':'no-fire'}">${escapeHtml(row.status)}</span></td><td>${escapeHtml(row.satellite)}</td><td>${escapeHtml(row.region)}</td></tr>`).join(''):'<tr><td colspan="5" class="no-data">No nearby reports found</td></tr>';
  $('rows-note').textContent=data.rows_truncated?`${data.rows.length} closest rows shown; ${data.rows_truncated} additional rows are included in the statistics.`:`${data.rows.length} report row${data.rows.length===1?'':'s'} shown.`;
  drawHistoryContext(data);
}
async function loadHistory(){
  const state=$('history-state');state.hidden=false;state.classList.remove('error');state.textContent='Loading nearby reports…';$('history-content').hidden=true;
  try{
    const response=await fetch('/api/context',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(selectionPayload())});
    const data=await response.json();if(!response.ok)throw new Error(data.error||'Historical context failed');renderContext(data);
  }catch(error){state.classList.add('error');state.textContent=error.message}
}
$('refresh-history').addEventListener('click',loadHistory);
$('history-radius').addEventListener('change',loadHistory);
$('history-lookback').addEventListener('change',loadHistory);

$('form').addEventListener('submit',async event=>{
  event.preventDefault();const button=$('submit');button.disabled=true;button.firstChild.textContent='Calculating… ';const payload=selectionPayload();
  const historyPromise=loadHistory();
  try{
    const response=await fetch('/api/predict',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw new Error(data.error||'Prediction failed');
    lastPrediction={scores:data.scores,surface:data.surface,version:data.version};
    const warnings=data.warnings.length?`<ul class="warnings">${data.warnings.map(x=>`<li>${escapeHtml(x)}</li>`).join('')}</ul>`:'';
    const evidence=data.scores.verified_fire_evidence;const context=data.scores.operational_context_hgb;
    const card=(score,kind)=>`<article class="score-card ${kind}"><span class="eyebrow">${escapeHtml(score.model.short_label)}</span><div class="probability">${score.percent}%</div><div class="meter"><span style="width:${score.percent}%"></span></div><h3>${escapeHtml(score.model.target)}</h3><p>${escapeHtml(score.model.estimator)} · 2025 PR-AUC ${score.model.validation_2025.pr_auc.toFixed(3)} · Brier ${score.model.validation_2025.brier.toFixed(3)}</p><small>${escapeHtml(score.model.warning)}</small></article>`;
    $('result').classList.remove('empty');
    $('result').innerHTML=`<div class="score-results"><div class="result-heading"><span class="eyebrow">${data.surface==='water'?'LAND/WATER SCREEN':'VERSION 3 · DUAL RESEARCH OUTPUT'}</span><h2>${data.surface==='water'?'Models skipped for water':'Keep evidence and operational context separate'}</h2></div><div class="dual-results">${card(evidence,'evidence')}${card(context,'context')}</div>${warnings}</div>`;
    plot(payload.latitude,payload.longitude,data.radius_m,evidence.probability);
  }catch(error){$('result').classList.remove('empty');$('result').innerHTML=`<div><span class="eyebrow">INPUT ERROR</span><h2>${escapeHtml(error.message)}</h2></div>`}
  finally{
    await historyPromise;
    if(lastContext&&lastContext.query.longitude===payload.longitude&&lastContext.query.latitude===payload.latitude)drawHistoryContext(lastContext);
    button.disabled=false;button.firstChild.textContent='Calculate research scores ';
  }
});

function csvCell(value){let text=String(value??'');if(/^[=+\-@]/.test(text))text=`'${text}`;return /[",\n]/.test(text)?`"${text.replace(/"/g,'""')}"`:text}
$('download-context').addEventListener('click',()=>{
  if(!lastContext)return;
  const header=['date','distance_km','longitude','latitude','status','source','satellite','region'];
  const csv=[header.join(','),...lastContext.rows.map(row=>header.map(key=>csvCell(row[key])).join(','))].join('\n');
  const link=document.createElement('a');link.href=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));link.download='nearby_hotspot_reports.csv';link.click();URL.revokeObjectURL(link.href);
});

function updateProvider(){
  const provider=$('llm-provider').value;const baseLabel=$('base-url-label');const keyLabel=$('api-key-label');
  if(provider==='ollama'){$('llm-model').value='gemma4';$('llm-base-url').value='http://127.0.0.1:11434';baseLabel.hidden=false;keyLabel.hidden=true}
  else if(provider==='openai'){$('llm-model').value='gpt-5.6';baseLabel.hidden=true;keyLabel.hidden=false}
  else{$('llm-model').value='';$('llm-base-url').value='http://127.0.0.1:1234/v1';baseLabel.hidden=false;keyLabel.hidden=false}
}
$('llm-provider').addEventListener('change',updateProvider);
function appendChat(role,text,error=false){
  const log=$('chat-log');const placeholder=log.querySelector('.chat-placeholder');if(placeholder)placeholder.remove();
  const item=document.createElement('div');item.className=`chat-message ${role}${error?' error':''}`;
  const label=document.createElement('span');label.textContent=role==='user'?'You':'Analyst';
  const body=document.createElement('div');body.textContent=text;item.append(label,body);log.appendChild(item);log.scrollTop=log.scrollHeight;
}
$('chat-form').addEventListener('submit',async event=>{
  event.preventDefault();const input=$('chat-input');const question=input.value.trim();if(!question)return;
  appendChat('user',question);chatMessages.push({role:'user',content:question});chatMessages=chatMessages.slice(-11);input.value='';
  const button=$('chat-send');button.disabled=true;button.firstChild.textContent='Thinking… ';
  try{
    const payload={provider:$('llm-provider').value,model:$('llm-model').value,base_url:$('llm-base-url').value,api_key:$('llm-api-key').value,messages:chatMessages,selection:selectionPayload(),prediction:lastPrediction};
    const response=await fetch('/api/llm/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});const data=await response.json();if(!response.ok)throw new Error(data.error||'The AI request failed');
    appendChat('assistant',data.answer);chatMessages.push({role:'assistant',content:data.answer});chatMessages=chatMessages.slice(-12);
  }catch(error){appendChat('assistant',error.message,true)}
  finally{button.disabled=false;button.firstChild.textContent='Ask analyst '}
});
