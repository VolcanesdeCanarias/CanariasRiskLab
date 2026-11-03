// One vertical case, using backend results and citations. Never computes alternative numbers.
const $=id=>document.getElementById(id);
function node(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function table(headers,rows){const t=node('table'),head=node('tr');headers.forEach(x=>head.append(node('th',x)));t.append(head);for(const row of rows){const tr=node('tr');row.forEach(x=>tr.append(node('td',x??'No disponible')));t.append(tr);}return t;}
const fmt=x=>x===null||x===undefined?'No calculable':Number(x).toLocaleString('es-ES',{maximumFractionDigits:3});
export function setupResearch({map,frame,activate,deactivate,setResearch,chooseBase,municipalityName}){
 let catalogue=null,run=null,active=false,serial=0,allEvents=null,previousBase=null;
 const grid=L.layerGroup();
 const actions=['study-report','study-evidence','study-csv','study-ask','show-study-current'];
 function setStatus(message,error=false){$('study-status').textContent=message;$('study-status').classList.toggle('error',error);}
 function invalidate(message='Parámetros modificados: ejecuta de nuevo para obtener resultados coherentes.'){
  ++serial;run=null;actions.forEach(id=>$(id).disabled=true);grid.clearLayers();
  $('study-current-count').textContent=$('study-previous-count').textContent=$('study-rate-ratio').textContent='—';
  for(const id of ['study-current-rate','study-previous-rate','study-series','study-series-table','study-series-scope','study-municipal-context','study-spatial','study-uncertainty','study-sensitivity','study-answer','study-answer-evidence'])$(id).replaceChildren();
  $('study-interpretation').textContent=message;$('study-run-id').textContent='Sin ejecución para los parámetros actuales';
  if(active)activate([],message);
 }
 async function json(url,options){const response=await fetch(url,options),body=await response.json();if(!response.ok)throw Error(body.error||'No se pudo verificar la evidencia histórica');return body;}
 function cited(container,items){
  container.replaceChildren();for(const item of items){const p=node('p',(item.year?`${item.year} · ${item.name||'Contexto documental'}. `:'')+item.claim);for(const id of item.sources){const source=catalogue.case.sources.find(s=>s.id===id);const a=node('a',' ['+source.title+']');a.href=source.url;a.target='_blank';a.rel='noopener';p.append(a);}container.append(p);}
 }
 function renderContext(){
  cited($('study-geology'),catalogue.case.geology);cited($('study-eruptions'),catalogue.case.history);cited($('study-documentary'),catalogue.case.documented_observations);
  $('study-territorial').replaceChildren(...catalogue.case.territory.map(t=>{const box=node('article');box.append(node('h4',t.name),node('p',t.quality),node('p',t.address||'Contexto natural documentado'));for(const id of t.sources){const s=catalogue.case.sources.find(s=>s.id===id),a=node('a',s.title+' ↗');a.href=s.url;a.target='_blank';a.rel='noopener';box.append(a);}return box;}));
  $('study-source-list').replaceChildren(...catalogue.case.sources.map(s=>{const p=node('p'),a=node('a',s.title);a.href=s.url;a.target='_blank';a.rel='noopener';p.append(a,node('small',' · Consulta '+s.consulted_at));return p;}));
  $('study-missing').textContent='Pendiente: '+catalogue.case.missing_signals.join(' · ');
  const m=catalogue.manifest;$('study-dataset').textContent=`USGS ComCat · ${m.verification.geojson_rows} registros reconciliados GeoJSON/CSV/count. Ventana consultada: ${m.coverage.from.slice(0,10)} → ${m.coverage.until.slice(0,10)} (excluido). No acredita cobertura continua de detección.`;
 }
 function showAnnual(rows){
  $('study-series-scope').textContent=`Ventana histórica completa de la consulta, filtrada por área, tipo ${run.parameters.mag_type} y magnitud ≥ ${run.parameters.min_mag}; no solo el periodo comparado. Gris: sin registros seleccionados; consulta la tabla para distinguir ausencia y filtros.`;const svg=$('study-series'),ns='http://www.w3.org/2000/svg',max=Math.max(1,...rows.map(r=>r.returned_records));svg.replaceChildren();
  rows.forEach((r,i)=>{const x=8+i*580/rows.length,rect=document.createElementNS(ns,'rect');for(const[k,v]of Object.entries({x,y:110-r.returned_records/max*90,width:Math.max(2,580/rows.length-4),height:r.returned_records?Math.max(1,r.returned_records/max*90):3,fill:r.returned_records?'#1c8182':'#a1aaa5'}))rect.setAttribute(k,v);const title=node('title');title.textContent=`${r.year}: ${r.returned_records} seleccionados / ${r.catalogue_records_in_study_area} registros en área. No equivale a actividad real`;rect.append(title);svg.append(rect);if(i%5===0||i===rows.length-1){const label=document.createElementNS(ns,'text');label.setAttribute('x',x);label.setAttribute('y',132);label.textContent=r.year;svg.append(label);}});
  $('study-series-table').replaceChildren(table(['Año','Selección','Registros del área','Lectura'],rows.map(r=>[r.year,r.returned_records,r.catalogue_records_in_study_area,r.state==='filtered_empty'?'Excluidos por filtros':r.returned_records?'Registros seleccionados':'Sin registros en área; no prueba inactividad'])));
 }
 function showMap(events,message,drawGrid=true){activate(events,message);grid.clearLayers();if(catalogue)L.rectangle([[catalogue.case.study_bounds[1],catalogue.case.study_bounds[0]],[catalogue.case.study_bounds[3],catalogue.case.study_bounds[2]]],{color:'#9b713b',weight:1,dashArray:'6,6',fill:false,interactive:false}).addTo(grid);if(drawGrid&&run?.spatial)for(const c of run.spatial.cells)L.rectangle([[c.bounds[1],c.bounds[0]],[c.bounds[3],c.bounds[2]]],{color:'#267c80',weight:1,fillOpacity:.08,interactive:false}).addTo(grid);}
 function render(){
  const cur=run.periods.current,prev=run.periods.previous;
  $('study-current-count').textContent=fmt(cur.count);$('study-previous-count').textContent=fmt(prev.count);$('study-rate-ratio').textContent=fmt(run.comparison.catalogue_rate_ratio);
  $('study-current-rate').textContent=`${cur.from.slice(0,10)} → ${cur.until.slice(0,10)} · ${fmt(cur.catalogue_rate_per_year)} registros/año · ${cur.duration_days} días`;
  $('study-previous-rate').textContent=`${fmt(prev.catalogue_rate_per_year)} registros/año · ${prev.from.slice(0,10)} → ${prev.until.slice(0,10)}`;
  $('study-interpretation').textContent=run.explanation.text+' No se infiere un cambio geofísico: completitud y estabilidad de detección no acreditadas.';
  const s=run.spatial;$('study-spatial').replaceChildren(node('p',s?`${s.occupied_cells} celdas ocupadas · vecino más próximo mediano: ${fmt(s.nearest_neighbour_median_km)} km · ${s.colocated_coordinates} coordenadas repetidas. Celdas y proximidad no son focos activos ni origen volcánico.`:'Sin cobertura para calcular distribución espacial.'));
  $('study-uncertainty').textContent=`Número de registros con error informado (horizontal / profundidad / magnitud): ${cur.uncertainty_available.horizontal_km} / ${cur.uncertainty_available.depth_km} / ${cur.uncertainty_available.magnitude} de ${cur.count??'—'} registros. Ausencia de error no es error cero; no se genera una confianza estadística ficticia.`;
  $('study-sensitivity').replaceChildren(table(['Magnitud mínima','Actual','Previo'],run.magnitude_sensitivity.map(r=>[r.min_mag,r.current_count,r.previous_count])));
  $('study-municipal-context').replaceChildren(table(['Asignación geométrica','Municipio','Registros'],run.territorial_context.map(r=>[r.territory,municipalityName(r.municipality_id)||'Sin asignación / mar',r.records])),node('p','Asignación sobre polígonos heredados (vigencia pendiente de verificación); no es exposición de población ni inventario de riesgo.'));showAnnual(run.annual_series);$('study-run-id').textContent=`${run.method} · ejecución SHA256 ${run.run_id}`;actions.forEach(id=>$(id).disabled=run.state!=='available');
  showMap(cur.events,`Histórico USGS · ${cur.count??'sin cobertura'} registros seleccionados · no vigilancia actual`);
 }
 async function execute(event){event?.preventDefault();if(!catalogue)return;
  invalidate('Ejecutando método reproducible…');const sequence=serial;setStatus('Validando dataset y ejecutando análisis…');$('study-run').disabled=true;
  try{
   const result=await json('/api/v1/research/runs',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({case_id:'teide-pico-viejo',from:$('study-from').value+'T00:00:00Z',until:$('study-until').value+'T00:00:00Z',min_mag:Number($('study-min-mag').value),mag_type:$('study-mag-type').value,grid_degrees:Number($('study-grid').value)})});
   if(sequence!==serial||!active)return;run=result;render();setStatus(result.state==='available'?'Ejecución registrada. Resultados del catálogo; completitud instrumental desconocida.':'Periodo sin cobertura: no se calcula cero registros.',result.state!=='available');
  }catch(e){if(sequence===serial){$('study-interpretation').textContent='Análisis no disponible: '+e.message;activate([],'Análisis histórico no disponible: no se calcula actividad.');setStatus(e.message,true);}}
  finally{if(sequence===serial)$('study-run').disabled=false;}
 }
 async function open(){
  if(active){$('study').scrollTop=0;return;}
  if($('profile').value==='institutional'){setStatus('Espacio institucional no habilitado',true);return;}
  if($('territory').value!=='Tenerife'){$('territory').value='Tenerife';$('territory').dispatchEvent(new Event('change'));}
  $('volcanic-system').value='gvp-383030';setResearch(false);active=true;$('study').hidden=false;$('workspace').classList.add('study-open');document.body.classList.add('study-active');$('municipality').disabled=true;grid.addTo(map);
  if($('view2d').getAttribute('aria-pressed')!=='true')$('view2d').click();previousBase=$('basemap').value;chooseBase('pnoa');$('basemap').value='pnoa';
  const opening=++serial;$('context').hidden=true;activate([],'Verificando catálogo histórico oficial…');await new Promise(resolve=>requestAnimationFrame(resolve));if(opening!==serial||!active)return;map.invalidateSize({pan:false,animate:false});frame([-16.95,27.95,-16.05,28.70]);setStatus('Verificando fuentes y catálogo histórico…');
  try{const result=await json('/api/v1/research/cases');if(opening!==serial||!active)return;catalogue=result;if(catalogue.dataset_state!=='available')throw Error('El dataset histórico no supera la verificación de integridad');renderContext();await execute();}
  catch(e){invalidate('Catálogo histórico no disponible. No se infiere ausencia de actividad.');setStatus(e.message,true);}
 }
 function close(){active=false;++serial;$('study').hidden=true;$('workspace').classList.remove('study-open');document.body.classList.remove('study-active');$('municipality').disabled=false;grid.removeFrom(map);if(previousBase){chooseBase(previousBase);$('basemap').value=previousBase;}deactivate();}
 $('open-study').onclick=open;$('close-study').onclick=close;$('study-form').onsubmit=execute;
 for(const input of $('study-form').querySelectorAll('input,select'))for(const event of ['input','change'])input.addEventListener(event,()=>{invalidate();$('study-run').disabled=false;});
 $('show-study-current').onclick=()=>{if(run)showMap(run.periods.current.events,'Histórico USGS · selección analizada');};
 $('show-study-all').onclick=async()=>{
  const sequence=serial;
  try{const data=await json('/api/v1/research/catalogue');if(sequence!==serial||!active)return;if(data.manifest.dataset_hash!==catalogue.manifest.dataset_hash)throw Error('La versión del dataset cambió: vuelve a abrir el estudio.');showMap(data.events,'Histórico USGS · catálogo completo, sin filtros del análisis',false);frame(catalogue.manifest.coverage.bounds);}
  catch(e){if(sequence===serial&&active)setStatus(e.message,true);}
 };
 $('study-question-form').onsubmit=async event=>{event.preventDefault();if(!run)return;const key=run.run_id,sequence=serial;try{const reply=await json(`/api/v1/research/runs/${key}/ask`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:$('study-question').value})});if(sequence!==serial||key!==run?.run_id)return;$('study-answer').textContent=reply.text;$('study-answer-evidence').textContent='Evidencia: '+reply.evidence.join(' · ');}catch(e){if(sequence===serial&&key===run?.run_id)$('study-answer').textContent=e.message;}};
 for(const [id,kind] of [['study-report','report.html'],['study-evidence','evidence.zip'],['study-csv','events.csv']])$(id).onclick=()=>{if(run)location.href=`/api/v1/research/runs/${run.run_id}/export/${kind}`;};
 $('territory').addEventListener('change',()=>{if(active&&$('territory').value!=='Tenerife')close();});
 $('volcanic-system').addEventListener('change',()=>{if(active&&$('volcanic-system').value!=='gvp-383030')close();});
 $('profile').addEventListener('change',()=>{$('open-study').disabled=$('profile').value==='institutional';if(active&&$('profile').value==='institutional')close();});
 return {open,close,get run(){return run;},get active(){return active;}};
}
