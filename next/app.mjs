import {EarthView} from './earth.mjs';
import {setupResearch} from './research.mjs';
import {setupObservatory} from '/next/observatory.mjs';
import {setupContinuous} from '/next/continuous.mjs';
let liveController=null;
import {BaseMaps} from './cartography.mjs';
import {CANARIAS, paddedBounds, panelBudget, leafletBounds, geographicBounds} from './view-state.mjs';
const $=id=>document.getElementById(id), state={snapshot:null,result:null,catalog:null,profile:'citizen',serial:0,earth:null,playing:null,research:false,selected:null,view:'2d',dockMode:'closed',requestedHeight:280,base:null,transferBounds:null,studyActive:false,studyEvents:[]};
const depthColor=d=>d<5?'#ad6b20':d<15?'#147f83':d<30?'#7063a7':'#a65273';
const map=L.map('map2d',{zoomControl:false,preferCanvas:true}).setView([28.45,-15.6],7);
let resizing=false,last2d={center:map.getCenter(),zoom:map.getZoom()},resizeFrame,framedViewportWidth=innerWidth;
function remember2d(){if(!resizing&&!$('map2d').hidden)last2d={center:map.getCenter(),zoom:map.getZoom()};}
map.on('moveend',remember2d);
function resizeViews(){
  if(!$('map2d').hidden&&$('map2d').clientWidth>1&&$('map2d').clientHeight>1){
    const pose=last2d;resizing=true;map.invalidateSize({pan:false,animate:false});map.setView(pose.center,pose.zoom,{animate:false,reset:true});resizing=false;
  }
  if(!$('map3d').hidden)state.earth?.resize();
}
function frameArea(bounds){
  const b=paddedBounds(bounds);state.focusBounds=b.slice();state.transferBounds=null;framedViewportWidth=innerWidth;
  if(state.view==='3d')state.earth?.frame(b);
  else{map.invalidateSize({pan:false,animate:false});map.fitBounds(leafletBounds(b),{paddingTopLeft:[18,85],paddingBottomRight:[18,25],maxZoom:13,animate:false});remember2d();}
}
const frameCanarias=()=>frameArea(CANARIAS);frameCanarias();
L.control.zoom({position:'bottomright'}).addTo(map);
const bases=new BaseMaps(map,baseNotice);
const eventLayer=L.layerGroup().addTo(map),volcanoes=L.layerGroup(),infrastructures=L.layerGroup(),stations=L.layerGroup();
const observer=new ResizeObserver(()=>{
  if(state.research&&state.dockMode!=='minimized')height(state.requestedHeight,false);
  cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(resizeViews);
});observer.observe($('map-stage'));observer.observe($('workspace'));
function baseNotice(message,error){text('map-base-status',message);$('map-base-status').classList.toggle('error',error);}
function setBase(id){const config=state.catalog.cartography.basemaps.find(b=>b.id===id);if(!config)return;state.base=config;bases.set(config);state.earth?.setBase(config,baseNotice);text('base-source',`${config.name} · ${config.attribution}. Sin resolución uniforme garantizada; consultar metadatos de la fuente.`);}
function text(id,value){$(id).textContent=value;}
function status(message,error=false){if(state.studyActive)return;text('data-status',message);$('data-status').classList.toggle('error',error);}
function paragraphs(lines){$('context-body').replaceChildren(...lines.map(line=>{const p=document.createElement('p');p.textContent=line;return p;}));}
function context(title,lines,type='CONTEXTO'){text('context-title',title);text('context-type',type);paragraphs(lines);$('context').hidden=false;}
function selectEvent(e){liveController?.onEvent(e);state.selected=e.id;context(e.place||e.id,[`${e.source} · ${e.id}`,`Fecha UTC: ${e.time}`,`Magnitud: ${e.magnitude??'no disponible'} ${e.magnitude_type||'(tipo no disponible)'}`,`Profundidad de catálogo: ${e.depth_km} km`,`Coordenadas: ${e.lat}, ${e.lon}`,`Territorio por polígono: ${e.territory}`,e.depth_reference,e.uncertainty?`Errores publicados: horizontal ${e.uncertainty.horizontal_km??'no disponible'} km; profundidad ${e.uncertainty.depth_km??'no disponible'} km; magnitud ${e.uncertainty.magnitude??'no disponible'}.`:'Incertidumbre: no disponible. No equivale a incertidumbre cero.','El hipocentro 3D utiliza −profundidad desde el elipsoide como aproximación visual; no hay MDT ni batimetría validados.'],'OBSERVACIÓN · SIN INTERPRETACIÓN CAUSAL');}
function stop(){if(state.playing)clearInterval(state.playing);state.playing=null;text('play','▶');$('play').setAttribute('aria-label','Reproducir eventos');}
function draw(){const all=state.studyActive?state.studyEvents:(state.result?.events||[]),a=Date.parse(state.result?.parameters.from),b=Date.parse(state.result?.parameters.until),cursor=state.studyActive?100:Number($('cursor').value),cutoff=state.studyActive?Infinity:a+(b-a)*cursor/100;const events=all.filter(e=>Date.parse(e.time)<=cutoff);
 eventLayer.clearLayers();for(const e of events)L.circleMarker([e.lat,e.lon],{radius:Math.max(3,Math.min(10,3+(e.magnitude+1)*1.3)),color:e.latest_change==='new'?'#146b6d':e.latest_change==='revised'?'#725b9b':'#fff',weight:e.latest_change?2.5:.8,fillColor:depthColor(e.depth_km),fillOpacity:.87}).on('click',()=>selectEvent(e)).addTo(eventLayer);
 state.earth?.update(events,depthColor);text('cursor-time',cursor===100?'Todo el periodo':new Date(cutoff).toISOString().slice(0,19)+' UTC');text('selection-count',(!state.studyActive&&(!state.result||state.result.statistics.count===null))?'Recuento no disponible':`${events.length} / ${all.length} registros`);
 if(state.selected&&!events.some(e=>e.id===state.selected)){$('context').hidden=true;state.selected=null;}
}
function chart(events){const bins=new Map();for(const e of events){const day=e.time.slice(0,10);bins.set(day,(bins.get(day)||0)+1);}const entries=[...bins].sort(),svg=$('chart');svg.replaceChildren();if(!entries.length)return;const ns='http://www.w3.org/2000/svg',max=Math.max(...entries.map(e=>e[1]));entries.forEach(([day,count],i)=>{const w=480/entries.length,x=i*w+10,bar=document.createElementNS(ns,'rect');for(const [k,v]of Object.entries({x,y:85-count/max*65,width:Math.max(1,w-6),height:count/max*65,fill:'#268787',rx:2}))bar.setAttribute(k,v);const title=document.createElementNS(ns,'title');title.textContent=`${day} UTC: ${count}`;bar.append(title);svg.append(bar);if(i===0||i===entries.length-1){const t=document.createElementNS(ns,'text');t.setAttribute('x',x);t.setAttribute('y',103);t.textContent=day;svg.append(t);}});}
function isoInput(date){return date.toISOString().slice(0,19);}
function params(){const p=new URLSearchParams({territory:$('territory').value,municipality_id:$('municipality').value,min_depth:$('min-depth').value,max_depth:$('max-depth').value,min_mag:$('min-mag').value,from:new Date($('from').value+'Z').toISOString(),until:new Date($('until').value+'Z').toISOString()});return p;}
async function analyze(){if(!state.snapshot)return;const sequence=++state.serial;stop();try{const q=params(),response=await fetch(`/api/v1/analysis/${state.snapshot.snapshot_id}?${q}`);const r=await response.json();if(sequence!==state.serial)return;if(!response.ok)throw Error(r.error||'No se pudo calcular la selección.');state.result=r;$('cursor').value=100;const good=!['unavailable','no_coverage'].includes(r.state);$('export').disabled=$('manifest').disabled=!good;$('play').disabled=$('cursor').disabled=!r.events.length;text('count',r.statistics.count===null?'No disponible':`${r.statistics.count} registros`);text('explanation',r.explanation.text);text('comparison',r.comparison.state==='available'?`Periodo previo de igual duración (${r.duration_hours.toFixed(1)} h): ${r.comparison.statistics.count} registros. Comparación descriptiva; sin inferencia causal.`:'Comparación no calculada: falta cobertura nominal para dos periodos completos.');text('quality',`Estado: ${r.state}. Adquisición: ${state.snapshot.quality.checked_at}`);text('snapshot',`Evidencia SHA-256: ${r.snapshot_id}`);if(good){chart(r.events);depthChart(r.events);}else{$('chart').replaceChildren();$('depth-chart').replaceChildren();}text('active-depth-note',`Filtro de profundidad activo: ${r.parameters.min_depth}–${r.parameters.max_depth} km, compartido entre experiencias.`);$('active-depth-note').hidden=r.parameters.min_depth===-10&&r.parameters.max_depth===1000;text('active-filters',`Municipio: ${$('municipality').selectedOptions[0].textContent} · profundidad ${r.parameters.min_depth}–${r.parameters.max_depth} km`);draw();status(good?`${state.snapshot.source} · ${r.state==='partial_coverage'?'Cobertura parcial':r.state==='empty'?'Catálogo válido sin registros':r.state==='filtered_empty'?'Sin registros en los filtros':'Observaciones adquiridas'} · UTC`:r.state==='no_coverage'?'El periodo no tiene cobertura en esta adquisición; no se calcula actividad.':`${state.snapshot.source}: fallo de adquisición. No puede evaluarse la actividad.`,!good);}catch(e){if(sequence!==state.serial)return;state.result=null;if(state.studyActive)return;stop();eventLayer.clearLayers();state.earth?.update([],depthColor);$('play').disabled=$('cursor').disabled=$('export').disabled=$('manifest').disabled=true;text('selection-count','Consulta no disponible');text('count','No disponible');text('explanation',e.message);text('comparison','');$('chart').replaceChildren();$('depth-chart').replaceChildren();text('snapshot','');$('context').hidden=true;status(e.message,true);}}
async function acquire(){const sequence=++state.serial;stop();state.snapshot=null;state.result=null;stop();if(!state.studyActive){eventLayer.clearLayers();state.earth?.update([],depthColor);}$('play').disabled=$('cursor').disabled=$('export').disabled=$('manifest').disabled=true;status(`Consultando ${$('source').value}…`);if(!state.studyActive){$('context').hidden=true;state.selected=null;}text('comparison','');$('chart').replaceChildren();$('depth-chart').replaceChildren();text('quality','Adquisición pendiente');text('snapshot','');text('selection-count','Consultando fuente…');text('count','—');text('explanation','Esperando una adquisición válida.');try{const response=await fetch('/api/v1/observations/'+$('source').value),snapshot=await response.json();if(sequence!==state.serial)return;if(!snapshot.snapshot_id)throw Error('No se pudo adquirir el catálogo.');state.snapshot=snapshot;const end=new Date(snapshot.quality.checked_at),start=new Date(end-86400000);$('until').value=isoInput(end);$('from').value=isoInput(start);text('coverage',`${snapshot.coverage.coverage} ${snapshot.limitations.join(' ')}`);await analyze();}catch(e){if(sequence!==state.serial)return;status(e.message,true);text('selection-count','Fuente no disponible');text('explanation','Adquisición no disponible. No se puede inferir ausencia de actividad.');}}
function height(value,remember=true){
  if(remember)state.requestedHeight=value;
  const budget=panelBudget({height:$('workspace').clientHeight,timeline:document.querySelector('.timeline').getBoundingClientRect().height,footer:document.querySelector('footer').getBoundingClientRect().height,mobile:innerWidth<681,requested:value});
  document.documentElement.style.setProperty('--research-height',budget.height+'px');
  for(const [key,v]of Object.entries({min:budget.min,max:budget.max,now:budget.height}))$('resize').setAttribute('aria-value'+key,v);
  return budget;
}
function setResearch(open){
  remember2d();state.research=open;state.dockMode=open?'expanded':'closed';
  $('research').hidden=!open;$('research').classList.remove('minimized');$('restore-research').hidden=true;$('minimize-research').hidden=false;
  $('workspace').classList.toggle('research-open',open);$('research-toggle').setAttribute('aria-expanded',String(open));
  text('research-toggle',open?'Cerrar análisis ↓':'Ampliar análisis ↑');if(open)height(state.requestedHeight,false);
  requestAnimationFrame(resizeViews);
}
$('research-toggle').onclick=()=>setResearch(!state.research);$('close-research').onclick=()=>setResearch(false);
$('minimize-research').onclick=()=>{remember2d();state.dockMode='minimized';$('research').classList.add('minimized');$('minimize-research').hidden=true;$('restore-research').hidden=false;requestAnimationFrame(resizeViews);};
$('restore-research').onclick=()=>setResearch(true);
$('resize').onkeydown=e=>{if(['ArrowUp','ArrowDown','Home','End'].includes(e.key)){e.preventDefault();if(state.dockMode==='minimized')setResearch(true);height(e.key==='Home'?128:e.key==='End'?600:Number($('resize').getAttribute('aria-valuenow'))+(e.key==='ArrowUp'?30:-30));}};
$('resize').onpointerdown=e=>{if(state.dockMode==='minimized')setResearch(true);e.preventDefault();const start=e.clientY,h=$('research').clientHeight;$('resize').setPointerCapture(e.pointerId);$('resize').onpointermove=m=>height(h+start-m.clientY);};
const releaseResize=()=>{$('resize').onpointermove=null;};$('resize').onpointerup=releaseResize;$('resize').onpointercancel=releaseResize;
$('close-context').onclick=()=>{$('context').hidden=true;state.selected=null;};$('layers-toggle').onclick=()=>{$('layers').hidden=!$('layers').hidden;$('layers-toggle').setAttribute('aria-expanded',String(!$('layers').hidden));$('legend').hidden=!$('layers').hidden;};
$('volcano-layer').onchange=e=>e.target.checked?volcanoes.addTo(map):volcanoes.removeFrom(map);$('infra-layer').onchange=e=>e.target.checked?infrastructures.addTo(map):infrastructures.removeFrom(map);
$('station-layer').onchange=e=>e.target.checked?stations.addTo(map):stations.removeFrom(map);
$('event-layer').onchange=e=>{if(e.target.checked)eventLayer.addTo(map);else eventLayer.removeFrom(map);if(state.earth)state.earth.points.show=e.target.checked;state.earth?.viewer.scene.requestRender();};
$('basemap').onchange=()=>setBase($('basemap').value);
$('profile').onchange=()=>{state.profile=$('profile').value;if(state.profile==='institutional'){setResearch(false);context('Espacio institucional no habilitado',['Requiere autenticación y autorización en el servidor, revisión de evidencias y permisos institucionales.','No se procesan datos restringidos ni se generan instrucciones de emergencia.'],'ACCESO NO CONFIGURADO');}else{setResearch(state.profile==='research');if(state.selected){const selected=state.result?.events.find(e=>e.id===state.selected);if(selected)selectEvent(selected);}else $('context').hidden=true;}};
for(const b of document.querySelectorAll('[data-area]'))b.onclick=()=>{document.querySelectorAll('[data-area]').forEach(x=>x.classList.toggle('active',x===b));const area=b.dataset.area;if(area==='observatory'){$('context').hidden=true;}if(area==='analysis')setResearch(true);if(area==='territory')context('Territorio, con contexto',['Cobertura de ocho islas, 88 municipios y entorno marítimo. Los filtros de isla utilizan polígonos terrestres; los eventos marinos conservan categoría propia.','Inventario recuperable: 32 equipamientos manuales y 12 referencias volcánicas heredadas. Tagoro no se representa por discrepancia de coordenadas.','No se calculan exposición, vulnerabilidad, daño o riesgo sin un escenario y datos validados. Activa referencias en Capas o abre las herramientas heredadas.']);if(area==='institutional')context('Apoyo a decisiones humanas',['Área pendiente de autenticación, control de acceso, escenarios documentados y revisión humana.','La selección de este perfil no concede permisos. La API institucional rechaza las solicitudes.']);if(area==='citizen')context('Qué sabemos y qué falta',['Magnitud: medida del tamaño del evento, no del peligro de una erupción. Profundidad: valor publicado por el catálogo; la incertidumbre no está disponible en este adaptador.','La ausencia de registros no demuestra ausencia de actividad. Un fallo de adquisición impide evaluar la selección.','No hay un comunicado PEVOLCA vigente verificado en esta integración. Consulta la fuente oficial enlazada al pie.','Los niveles experimentales heredados no son niveles oficiales PEVOLCA. No se utilizan como alertas en esta experiencia.']);};
$('refresh').onclick=acquire;$('source').onchange=acquire;$('territory').onchange=()=>{populateMunicipalities();$('volcanic-system').value='';const b=state.catalog.territory_views[$('territory').value];frameArea(b||CANARIAS);text('map-title',$('territory').value==='Canarias'?'Canarias y su entorno atlántico':$('territory').value);analyze();};
$('municipality').onchange=()=>{const m=state.catalog.municipalities.find(m=>m.id===$('municipality').value);if(m){frameArea(m.bounds);text('map-title',m.name);}else frameArea(state.catalog.territory_views[$('territory').value]||CANARIAS);analyze();};
$('volcanic-system').onchange=()=>{const v=state.catalog.volcanic_catalogue.systems.find(v=>v.id===$('volcanic-system').value);if(v){frameArea(v.bounds);showSystem(v);text('map-title',v.name);}};
$('apply-depth').onclick=analyze;$('min-mag').onchange=analyze;$('apply').onclick=analyze;
$('cursor').oninput=()=>{stop();draw();};$('play').onclick=()=>{if(state.playing){stop();return;}if(Number($('cursor').value)>=100)$('cursor').value=0;text('play','Ⅱ');$('play').setAttribute('aria-label','Pausar eventos');state.playing=setInterval(()=>{$('cursor').value=Math.min(100,Number($('cursor').value)+1);draw();if(Number($('cursor').value)===100)stop();},150);};
$('export').onclick=()=>{if(state.result)location.href=`/api/v1/analysis/${state.result.snapshot_id}?${new URLSearchParams(state.result.parameters)}&format=csv`;};$('manifest').onclick=()=>{if(!state.result)return;const url=URL.createObjectURL(new Blob([JSON.stringify(state.result,null,2)],{type:'application/json'})),a=document.createElement('a');a.href=url;a.download='risklab-analysis.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
$('view3d').onclick=()=>{
  if(state.view==='3d')return;
  try{
    if(!globalThis.Cesium)throw Error('SDK 3D no disponible; instala las dependencias con npm ci.');
    remember2d();const bounds=geographicBounds(map.getBounds());state.transferBounds=bounds;
    $('map3d').hidden=false;$('map2d').hidden=true;
    const first=!state.earth;state.earth??=new EarthView('map3d',selectEvent);state.view='3d';
    state.earth.resize();state.earth.frame(bounds);if(state.base)state.earth.setBase(state.base,baseNotice);state.earth.loadTerrain().then(info=>text('terrain-status',info));state.earth.points.show=$('event-layer').checked;draw();
    $('terrain-status').hidden=false;$('view3d').setAttribute('aria-pressed','true');$('view2d').setAttribute('aria-pressed','false');
    if(first&&!state.selected)context('Exploración 3D · referencia vertical',['Base cartográfica oficial intercambiable; el globo sigue siendo elipsoidal sin un MDT importado y documentado. Una imagen de relieve no es elevación.','Los hipocentros utilizan −profundidad de catálogo: referencia aproximada sin conversión de datum. No medir distancias verticales científicas aquí.']);
  }catch(e){state.view='2d';$('map3d').hidden=true;$('map2d').hidden=false;resizeViews();status(e.message,true);}
};
$('view2d').onclick=()=>{
  if(state.view==='2d')return;
  const bounds=state.earth.bounds(),unchanged=state.transferBounds&&bounds.every((v,i)=>Math.abs(v-state.transferBounds[i])<1e-8);
  $('map3d').hidden=true;$('map2d').hidden=false;state.view='2d';resizeViews();
  if(!unchanged)frameArea(bounds);
  $('terrain-status').hidden=true;$('view2d').setAttribute('aria-pressed','true');$('view3d').setAttribute('aria-pressed','false');
};
$('home').onclick=()=>{const m=state.catalog?.municipalities.find(m=>m.id===$('municipality').value),v=state.catalog?.volcanic_catalogue.systems.find(v=>v.id===$('volcanic-system').value);frameArea(v?.bounds||m?.bounds||state.catalog?.territory_views[$('territory').value]||CANARIAS);};
function populateMunicipalities(){
  const select=$('municipality');select.replaceChildren(new Option('Todos los municipios',''));
  for(const m of state.catalog.municipalities.filter(m=>$('territory').value==='Canarias'||m.island===$('territory').value||($('territory').value==='La Graciosa'&&m.id==='35024')))select.append(new Option(m.name,m.id));
}
function showSystem(v){
  context(v.name,[`Ficha documental · GVP ${v.catalogue_id} · consulta ${state.catalog.volcanic_catalogue.reviewed_at}`,...v.facts,state.catalog.volcanic_catalogue.limitation,'Navegar aquí no recorta los registros al sistema ni modifica los filtros activos.'],'DOCUMENTACIÓN · FUENTE PRIMARIA');
  for(const source of v.sources){const a=document.createElement('a');a.href=source.url;a.textContent=source.title+' ↗';a.target='_blank';a.rel='noopener';$('context-body').append(a);}
}
function depthChart(events){
  const bins=[['<5 km',0],['5–15',0],['15–30',0],['≥30',0]];
  for(const e of events)bins[e.depth_km<5?0:e.depth_km<15?1:e.depth_km<30?2:3][1]++;
  const svg=$('depth-chart'),ns='http://www.w3.org/2000/svg',max=Math.max(1,...bins.map(b=>b[1]));svg.replaceChildren();
  bins.forEach(([label,count],i)=>{const rect=document.createElementNS(ns,'rect');for(const[k,v]of Object.entries({x:15+i*122,y:75-count/max*55,width:104,height:count/max*55,fill:depthColor([0,5,15,30][i]),rx:2}))rect.setAttribute(k,v);const t=document.createElementNS(ns,'text');t.setAttribute('x',15+i*122);t.setAttribute('y',99);t.textContent=label+' · '+count;svg.append(rect,t);});
}
const study=setupResearch({map,frame:frameArea,setResearch,chooseBase:setBase,municipalityName:id=>state.catalog?.municipalities.find(m=>m.id===id)?.name,
 activate(events,message){stop();state.studyActive=true;state.studyEvents=events;if(state.selected&&!events.some(e=>e.id===state.selected)){state.selected=null;$('context').hidden=true;}draw();text('data-status',message);$('data-status').classList.remove('error');requestAnimationFrame(resizeViews);},
 deactivate(){state.studyActive=false;state.studyEvents=[];draw();status(state.snapshot&&state.result?`${state.snapshot.source} · vista reciente · ${state.snapshot.quality.state}`:'Consulta reciente no disponible; no se puede evaluar actividad.',!state.result||!state.snapshot||state.snapshot.quality.state==='unavailable');requestAnimationFrame(resizeViews);}
});
const observatory=setupObservatory({map,frame:frameArea,selectEvent,closeStudy:()=>{if(study.active)study.close();},setResearch,getBounds:()=>state.view==='3d'?state.earth.bounds():geographicBounds(map.getBounds()),
 activate(events,message){stop();state.studyActive=true;state.studyEvents=events;draw();text('data-status',message);$('data-status').classList.remove('error');requestAnimationFrame(resizeViews);},
 deactivate(){state.studyActive=false;state.studyEvents=[];draw();status(state.result?`${state.snapshot?.source} · vista reciente`:'Datos recientes no disponibles; no se puede evaluar actividad.',!state.result);requestAnimationFrame(resizeViews);}
});
const continuous=setupContinuous({map,frame:frameArea,selectEvent,setResearch,getSelected:()=>state.selected,
 closeOthers(){if(study.active)study.close();if(observatory.active)observatory.close();},
 activate(events,message){stop();state.studyActive=true;state.studyEvents=events;draw();text('data-status',message);requestAnimationFrame(resizeViews);},
 deactivate(){state.studyActive=false;state.studyEvents=[];draw();status(state.result?`${state.snapshot?.source} · vista reciente manual`:'Fuente reciente no disponible; no se evalúa actividad.',!state.result);requestAnimationFrame(resizeViews);}
});liveController=continuous;
try{const response=await fetch('/api/v1/catalog');if(!response.ok)throw Error('No se pudo cargar el catálogo territorial.');state.catalog=await response.json();$('open-study').disabled=false;populateMunicipalities();for(const v of state.catalog.volcanic_catalogue.systems)$('volcanic-system').append(new Option(v.name,v.id));for(const base of state.catalog.cartography.basemaps)$('basemap').append(new Option(base.name,base.id));$('basemap').value='ign-topo';setBase('ign-topo');$('legend').open=innerWidth>680;const outlines=await fetch('/api/v1/territory-outlines').then(r=>r.json());for(const ring of outlines.rings)L.polygon(ring.map(p=>[p[1],p[0]]),{color:'#759b8d',weight:.6,fillColor:'#dce8d6',fillOpacity:.28,interactive:false}).addTo(map).bringToBack();for(const name of state.catalog.territories){const o=document.createElement('option');o.textContent=name;$('territory').append(o);}for(const v of state.catalog.references.volcanoes)L.circleMarker([v.lat,v.lon],{radius:6,color:'#605778',fillOpacity:.7}).on('click',()=>context(v.name,[`Referencia heredada · ${v.island}`,'Clasificación, coordenadas e historia pendientes de verificación documental. No expresa actividad actual.'])).addTo(volcanoes);for(const v of state.catalog.references.infrastructures)L.circleMarker([v.lat,v.lon],{radius:4,color:'#406670',fillOpacity:.7}).on('click',()=>context(v.nombre,[`Equipamiento heredado · ${v.tipo} · ${v.isla}`,'Ubicación y atributos pendientes de verificación. No se clasifica como infraestructura crítica.'])).addTo(infrastructures);for(const v of state.catalog.instrumentation.stations)L.circleMarker([v.lat,v.lon],{radius:5,color:'#6b7155',fillOpacity:.7}).on('click',()=>context(v.nombre,[`Referencia instrumental heredada · ${v.tipo} · ${v.isla}`,'Estado operativo no verificado. El inventario no contiene telemetría ni series observadas. No se reutiliza la etiqueta manual operativa como estado actual.'])).addTo(stations);if(new URLSearchParams(location.search).get('mode')==='continuous')await continuous.open();else await acquire();}catch(e){status(e.message,true);}
let windowWidth=innerWidth;
addEventListener('resize',()=>{if(windowWidth!==innerWidth){windowWidth=innerWidth;requestAnimationFrame(()=>{resizeViews();if(framedViewportWidth!==windowWidth)frameArea(state.focusBounds||CANARIAS);$('legend').open=innerWidth>680;});}});
// Narrow read-only diagnostics for review tests; no privileged operations.
globalThis.risklabNext={get state(){return state;},map,setResearch,height,resizeViews,study,observatory,continuous};
