const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process');
const {chromium,request}=require('playwright');
const root=path.resolve(__dirname,'../..'),base='http://127.0.0.1:8766',captures=path.join(root,'work/next-captures');
let server,browser,api,page,errors=[];
test.before(async()=>{fs.mkdirSync(captures,{recursive:true});server=spawn(process.env.PYTHON||'python',['tests/next/serve.py'],{cwd:root,env:{...process.env,TEST_PORT:'8766',RISKLAB_NEXT_DB:path.join(root,'work/next-test.sqlite')}});server.stderr.on('data',()=>{});api=await request.newContext();for(let i=0;i<80;i++){try{if((await api.get(base+'/__test__/ready')).ok())break;}catch{}await new Promise(r=>setTimeout(r,100));}browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_PATH||undefined,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});console.log('Chromium',browser.version());});
test.after(async()=>{await browser?.close();await api?.dispose();server?.kill();});
test.beforeEach(async()=>{await api.post(base+'/__test__/next-scenario/IGN/ok');await api.post(base+'/__test__/next-scenario/USGS/ok');page=await browser.newPage({viewport:{width:1440,height:1000}});errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('https://**/*',r=>r.abort());await page.goto(base+'/next/');await page.waitForFunction(()=>globalThis.risklabNext?.state.result?.statistics.count===16);});
test.afterEach(async()=>{assert.deepEqual(errors,[]);await page?.close();});
async function loaded(count){await page.waitForFunction(n=>globalThis.risklabNext.state.result?.statistics.count===n,count);}
async function screenshot(name){await page.evaluate(()=>{const x=document.createElement('div');x.textContent='PRUEBA AUTOMATIZADA · DATOS DE TEST · BASE CARTOGRÁFICA EXTERNA OMITIDA';Object.assign(x.style,{position:'fixed',left:'0',bottom:'0',background:'#fff2d9',color:'#604519',padding:'3px 8px',fontSize:'9px',zIndex:9999});document.body.append(x);});await page.screenshot({path:path.join(captures,name+'.png')});}

test('2D all-islands coverage, source labels and real event selection UI',async()=>{assert.equal(await page.locator('#territory option').count(),10);const point=await page.evaluate(()=>{const e=risklabNext.state.result.events[0],p=risklabNext.map.latLngToContainerPoint([e.lat,e.lon]);return {x:p.x,y:p.y};});await page.locator('#map2d').click({position:point});assert.equal(await page.locator('#context').isVisible(),true);assert.match(await page.locator('#context-body').innerText(),/Magnitud/);await page.click('#close-context');assert.match(await page.locator('#data-status').innerText(),/IGN/);assert.equal(await page.locator('#view2d').getAttribute('aria-pressed'),'true');await screenshot('desktop-fixtures');});
test('citizen and research share exact analysis snapshot and result',async()=>{const a=await page.evaluate(()=>JSON.stringify(risklabNext.state.result));await page.selectOption('#profile','research');assert.equal(await page.locator('#research').isVisible(),true);assert.equal(await page.evaluate(()=>JSON.stringify(risklabNext.state.result)),a);await screenshot('research-fixtures');});
test('Research open resize minimize close preserve Leaflet position',async()=>{const before=await page.evaluate(()=>({center:risklabNext.map.getCenter(),zoom:risklabNext.map.getZoom()}));await page.click('#research-toggle');await page.focus('#resize');await page.keyboard.press('ArrowUp');await page.click('#minimize-research');await page.click('#close-research');const after=await page.evaluate(()=>({center:risklabNext.map.getCenter(),zoom:risklabNext.map.getZoom()}));assert.deepEqual(after,before);});
test('quick filters discard stale results and preserve shared params',async()=>{await page.selectOption('#territory','Tenerife');await page.selectOption('#territory','La Palma');await page.selectOption('#territory','La Graciosa');await loaded(0);assert.equal(await page.evaluate(()=>risklabNext.state.result.parameters.territory),'La Graciosa');assert.match(await page.locator('#data-status').innerText(),/Sin registros en los filtros/);await page.selectOption('#territory','Canarias');await loaded(16);});
test('IGN 403 never becomes zero or reassurance and recovers',async()=>{await api.post(base+'/__test__/next-scenario/IGN/error');await page.click('#refresh');await loaded(null);assert.match(await page.locator('#data-status').innerText(),/fallo/);assert.equal(await page.locator('#export').isDisabled(),true);assert.match(await page.locator('#explanation').innerText(),/no disponible/);await api.post(base+'/__test__/next-scenario/IGN/ok');await page.click('#refresh');await loaded(16);assert.equal(await page.locator('#export').isDisabled(),false);});
test('USGS failure is separate, empty is explicit, later acquisition recovers',async()=>{await api.post(base+'/__test__/next-scenario/USGS/error');await page.selectOption('#source','USGS');await loaded(null);await page.selectOption('#source','IGN');await loaded(16);await api.post(base+'/__test__/next-scenario/USGS/empty');await page.selectOption('#source','USGS');await loaded(0);assert.match(await page.locator('#data-status').innerText(),/Catálogo válido sin registros/);await api.post(base+'/__test__/next-scenario/USGS/ok');await page.click('#refresh');await page.waitForFunction(()=>risklabNext.state.result?.state!=='unavailable');});
test('empty IGN has no index and no claim of absent activity',async()=>{await api.post(base+'/__test__/next-scenario/IGN/empty');await page.click('#refresh');await loaded(0);assert.match(await page.locator('#explanation').innerText(),/No demuestra ausencia de actividad/);assert.equal(await page.evaluate(()=>risklabNext.state.result.risklab_index),undefined);});
test('institutional profile grants no server permissions',async()=>{await page.selectOption('#profile','institutional');assert.match(await page.locator('#context-title').innerText(),/no habilitado/);assert.equal((await api.get(base+'/api/v1/institutional/reports')).status(),403);});
test('3D renders hypocenters and survives dock changes without camera jumps',async()=>{await page.click('#view3d');await page.waitForFunction(()=>risklabNext.state.earth?.points.length===16);await page.evaluate(()=>risklabNext.state.earth.ready);const before=await page.evaluate(()=>JSON.stringify(risklabNext.state.earth.viewer.camera.positionWC));await page.click('#close-context');await page.click('#research-toggle');await page.focus('#resize');await page.keyboard.press('ArrowUp');await page.click('#close-research');assert.equal(await page.evaluate(()=>JSON.stringify(risklabNext.state.earth.viewer.camera.positionWC)),before);assert.ok(await page.locator('#map3d canvas').count());await screenshot('earth-3d-fixtures');});
test('mobile viewport has no horizontal overflow and retains filters/research',async()=>{await page.setViewportSize({width:390,height:844});assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);await page.selectOption('#profile','research');await page.focus('#resize');await page.keyboard.press('ArrowUp');assert.equal(await page.locator('#export').isVisible(),true);await page.click('#close-research');await screenshot('mobile-fixtures');});
test('playback and exports refer to full selected interval',async()=>{await page.click('#play');await page.waitForTimeout(180);assert.equal(await page.locator('#play').getAttribute('aria-label'),'Pausar eventos');await page.click('#play');assert.equal(await page.locator('#export').isDisabled(),false);await page.click('#research-toggle');const download=page.waitForEvent('download');await page.click('#manifest');const file=await download;assert.equal(file.suggestedFilename(),'risklab-analysis.json');});

const near=(a,b)=>Math.abs(a-b)<1e-7;
async function pose2d(){return page.evaluate(()=>({lat:risklabNext.map.getCenter().lat,lon:risklabNext.map.getCenter().lng,zoom:risklabNext.map.getZoom()}));}
function assertPose(a,b){assert.ok(near(a.lat,b.lat)&&near(a.lon,b.lon),JSON.stringify({a,b}));assert.equal(a.zoom,b.zoom);}
test('MAP-01 repeated experience changes preserve island framing at four viewport sizes',async()=>{
 for(const size of [{width:1440,height:1000},{width:1280,height:720},{width:768,height:1024},{width:390,height:844}]){
  await page.setViewportSize(size);await page.waitForTimeout(80);await page.selectOption('#territory','Tenerife');await loaded(4);await page.waitForTimeout(80);
  const before=await pose2d();assert.ok(before.lat>27&&before.lat<30&&before.lon>-18&&before.lon<-15);
  for(const profile of ['research','institutional','citizen','research','citizen']){await page.selectOption('#profile',profile);await page.waitForTimeout(60);assertPose(await pose2d(),before);}
 }
});
test('MAP-02 Research maximization, minimization and restore keep a useful map',async()=>{
 for(const size of [{width:1440,height:900},{width:390,height:844}]){
  await page.setViewportSize(size);await page.waitForTimeout(80);await page.click('#research-toggle');await page.evaluate(()=>risklabNext.height(10000));await page.waitForTimeout(80);
  assert.ok(await page.locator('#map-stage').evaluate(e=>e.clientHeight)>=(size.width<681?250:320));
  await page.click('#minimize-research');assert.ok(await page.locator('#research').evaluate(e=>e.clientHeight)<=64);
  await page.click('#restore-research');assert.ok(await page.locator('#map-stage').evaluate(e=>e.clientHeight)>=(size.width<681?250:320));await page.click('#close-research');
 }
});
test('MAP-05 2D/3D transition preserves selected event, filters and camera context',async()=>{
 await page.selectOption('#territory','Tenerife');await loaded(4);const before=await pose2d();
 const point=await page.evaluate(()=>{const e=risklabNext.state.result.events[0],p=risklabNext.map.latLngToContainerPoint([e.lat,e.lon]);return{x:p.x,y:p.y};});await page.locator('#map2d').click({position:point});
 const selection=await page.evaluate(()=>({id:risklabNext.state.selected,query:JSON.stringify(risklabNext.state.result.parameters),snapshot:risklabNext.state.snapshot.snapshot_id}));assert.ok(selection.id);
 await page.click('#view3d');await page.waitForFunction(()=>risklabNext.state.earth?.points.length===4);assert.match(await page.locator('#context-body').innerText(),/Magnitud/);
 for(const profile of ['research','institutional','citizen']){await page.selectOption('#profile',profile);await page.waitForTimeout(60);}
 await page.click('#view2d');assertPose(await pose2d(),before);
 assert.deepEqual(await page.evaluate(()=>({id:risklabNext.state.selected,query:JSON.stringify(risklabNext.state.result.parameters),snapshot:risklabNext.state.snapshot.snapshot_id})),selection);
});
test('MAP-03 official basemaps and layer failures never change acquisition statistics',async()=>{
 const before=await page.evaluate(()=>JSON.stringify(risklabNext.state.result));
 for(const id of ['pnoa','ign-hybrid','osm','ign-topo']){await page.selectOption('#basemap',id);await page.waitForTimeout(40);assert.equal(await page.evaluate(()=>JSON.stringify(risklabNext.state.result)),before);}
 await page.click('#layers-toggle');await page.check('#station-layer');assert.match(await page.locator('#layers').innerText(),/sin verificar/);assert.equal(await page.locator('#legend').isVisible(),false);
 await page.uncheck('#event-layer');assert.equal(await page.evaluate(()=>JSON.stringify(risklabNext.state.result)),before);await page.check('#event-layer');await page.click('#layers-toggle');
});
test('territorial navigation includes La Graciosa, municipalities and documentary systems',async()=>{
 await page.selectOption('#territory','La Graciosa');await loaded(0);const center=await pose2d();assert.ok(center.lat>29.2&&center.lat<29.31);assert.ok(center.zoom>=10);
 await page.selectOption('#territory','Tenerife');await loaded(4);const m=await page.evaluate(()=>risklabNext.state.result.events[0].municipality_id);await page.selectOption('#municipality',m);await loaded(4);
 assert.equal(await page.evaluate(()=>risklabNext.state.result.parameters.municipality_id),m);
 const before=await page.evaluate(()=>JSON.stringify(risklabNext.state.result));await page.selectOption('#volcanic-system','gvp-383030');assert.equal(await page.evaluate(()=>JSON.stringify(risklabNext.state.result)),before);
 assert.equal(await page.locator('#context-body a').getAttribute('href'),'https://volcano.si.edu/volcano.cfm?vn=383030');assert.match(await page.locator('#context-body').innerText(),/no recorta/);
});
test('advanced depth filters remain active with identical results in Ciudadania',async()=>{
 await page.selectOption('#profile','research');await page.fill('#min-depth','11');await page.fill('#max-depth','20');await page.click('#apply-depth');await loaded(0);
 const before=await page.evaluate(()=>JSON.stringify(risklabNext.state.result));await page.selectOption('#profile','citizen');assert.equal(await page.evaluate(()=>JSON.stringify(risklabNext.state.result)),before);
 assert.equal(await page.evaluate(()=>risklabNext.state.result.parameters.min_depth),11);
});
test('optional DEM mesh renderer accepts a clearly test-only grid without fabricating nodata',async()=>{
 await page.route('**/api/v1/terrain',r=>r.fulfill({json:{state:'documented_import',grid:{width:5,height:5,bounds:[-16.7,28.2,-16.6,28.3],values:Array(25).fill(300),metadata:{product:'TEST FIXTURE ONLY',source_resolution_m:25,vertical_datum:'TEST DATUM'}}}}));
 await page.click('#view3d');await page.waitForFunction(()=>!!risklabNext.state.earth?.terrainPrimitive);assert.match(await page.locator('#terrain-status').innerText(),/TEST FIXTURE ONLY/);
 assert.equal(await page.evaluate(()=>risklabNext.state.earth.grid.values.length),25);await page.click('#close-context');
});
test('period wholly outside source coverage is unavailable rather than zero events',async()=>{
 await page.selectOption('#profile','research');const day=await page.evaluate(()=>new Date(Date.parse(risklabNext.state.snapshot.quality.checked_at)-20*86400000).toISOString().slice(0,19));
 await page.fill('#until',day);await page.fill('#from','2020-01-01T00:00');await page.click('#apply');await loaded(null);
 assert.equal(await page.evaluate(()=>risklabNext.state.result.state),'no_coverage');assert.equal(await page.locator('#export').isDisabled(),true);assert.equal(await page.locator('#depth-chart rect').count(),0);assert.match(await page.locator('#data-status').innerText(),/no tiene cobertura/);
});

async function researchRun(){await page.click('#open-study');await page.waitForFunction(()=>risklabNext.study.run?.periods.current.count===11);}
test('PRODUCT-01 complete real historical case links science, analysis, territory and evidence',async()=>{
 await page.selectOption('#territory','Tenerife');await loaded(4);await page.selectOption('#volcanic-system','gvp-383030');await researchRun();
 assert.equal(await page.locator('#study').isVisible(),true);assert.equal(await page.locator('#context').isVisible(),false);assert.match(await page.locator('#study-eruptions').innerText(),/1798/);assert.match(await page.locator('#study-eruptions').innerText(),/1909/);
 assert.match(await page.locator('#study-dataset').innerText(),/181 registros/);assert.equal(await page.locator('#study-current-count').innerText(),'11');assert.equal(await page.locator('#study-previous-count').innerText(),'35');
 assert.match(await page.locator('#study-territorial').innerText(),/Hospital Universitario de Canarias/);assert.match(await page.locator('#study-interpretation').innerText(),/No se infiere/);
 assert.equal(await page.evaluate(()=>risklabNext.state.studyEvents.length),11);assert.equal(await page.evaluate(()=>risklabNext.study.run.comparison.inference_allowed),false);
 const downloadPromise=page.waitForEvent('download');await page.locator('#study-evidence').scrollIntoViewIfNeeded();await page.click('#study-evidence');const download=await downloadPromise;
 assert.match(download.suggestedFilename(),/evidence.zip/);assert.equal(fs.readFileSync(await download.path()).subarray(0,2).toString(),'PK');
});
test('PRODUCT-02 changed parameters invalidate export and produce a new reproducible run',async()=>{
 await researchRun();const original=await page.evaluate(()=>risklabNext.study.run.run_id);await page.locator('#study-min-mag').scrollIntoViewIfNeeded();await page.fill('#study-min-mag','2.5');
 assert.equal(await page.locator('#study-evidence').isDisabled(),true);assert.equal(await page.evaluate(()=>risklabNext.study.run),null);assert.equal(await page.locator('#study-series rect').count(),0);
 await page.click('#study-run');await page.waitForFunction(()=>risklabNext.study.run?.parameters.min_mag===2.5);
 assert.notEqual(await page.evaluate(()=>risklabNext.study.run.run_id),original);const second=await page.evaluate(()=>risklabNext.study.run.run_id);await page.click('#study-run');await page.waitForFunction(id=>risklabNext.study.run?.run_id===id,second);
});
test('PRODUCT-03 assistance cites numerical evidence and refuses eruption predictions',async()=>{
 await researchRun();await page.locator('#study-question').scrollIntoViewIfNeeded();await page.fill('#study-question','¿Cómo ha cambiado la tasa del catálogo?');await page.click('#study-ask');await page.waitForFunction(()=>document.querySelector('#study-answer').textContent.includes('11'));
 assert.match(await page.locator('#study-answer').innerText(),/35/);assert.match(await page.locator('#study-answer-evidence').innerText(),/periods.current/);
 await page.fill('#study-question','¿Va a erupcionar?');await page.click('#study-ask');await page.waitForFunction(()=>document.querySelector('#study-answer').textContent.includes('No puedo deducir'));
});
test('PRODUCT-04 research errors never export stale numbers and later recover',async()=>{
 await researchRun();await page.route('**/api/v1/research/runs',r=>r.fulfill({status:503,json:{error:'Dataset no verificable (test-only transport failure)'}}));
 await page.locator('#study-run').scrollIntoViewIfNeeded();await page.click('#study-run');await page.waitForFunction(()=>document.querySelector('#study-status').classList.contains('error'));
 assert.equal(await page.locator('#study-evidence').isDisabled(),true);assert.equal(await page.evaluate(()=>risklabNext.study.run),null);assert.equal(await page.locator('#study-current-count').innerText(),'—');
 await page.unroute('**/api/v1/research/runs');await page.click('#study-run');await page.waitForFunction(()=>risklabNext.study.run?.periods.current.count===11);
});
test('PRODUCT-05 historical research remains independent from failed live IGN acquisition',async()=>{
 await researchRun();const before=await page.evaluate(()=>risklabNext.study.run.run_id);await api.post(base+'/__test__/next-scenario/IGN/error');await page.evaluate(()=>document.querySelector('#refresh').click());
 await page.waitForFunction(()=>risklabNext.state.snapshot?.quality.state==='unavailable');assert.equal(await page.evaluate(()=>risklabNext.study.run.run_id),before);assert.equal(await page.evaluate(()=>risklabNext.state.studyEvents.length),11);
 assert.match(await page.locator('#data-status').innerText(),/Histórico USGS/);await page.click('#close-study');assert.equal(await page.evaluate(()=>risklabNext.state.studyActive),false);
});
test('PRODUCT-06 archived case works on mobile and preserves shared results across public profiles',async()=>{
 await page.setViewportSize({width:390,height:844});await researchRun();const before=await page.evaluate(()=>risklabNext.study.run.run_id);
 assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);assert.ok(await page.locator('#map-stage').evaluate(e=>e.clientHeight)>=280);
 await page.selectOption('#profile','research');assert.equal(await page.evaluate(()=>risklabNext.study.run.run_id),before);await page.selectOption('#profile','citizen');assert.equal(await page.evaluate(()=>risklabNext.study.run.run_id),before);
 await page.selectOption('#territory','La Graciosa');assert.equal(await page.locator('#study').isVisible(),false);assert.equal(await page.evaluate(()=>risklabNext.state.studyActive),false);
});

test('PRODUCT-07 delayed catalogue cannot reactivate a closed study or overwrite La Graciosa',async()=>{
 await researchRun();let release,held=false;const gate=new Promise(resolve=>release=resolve);
 await page.route('**/api/v1/research/catalogue',async route=>{const response=await route.fetch();held=true;await gate;await route.fulfill({response});});
 await page.locator('#show-study-all').scrollIntoViewIfNeeded();await page.click('#show-study-all');for(let i=0;i<50&&!held;i++)await page.waitForTimeout(20);assert.ok(held);
 await page.click('#close-study');await page.selectOption('#territory','La Graciosa');await loaded(0);release();await page.waitForTimeout(150);
 assert.equal(await page.evaluate(()=>risklabNext.study.active),false);assert.equal(await page.evaluate(()=>risklabNext.state.studyActive),false);assert.equal(await page.locator('#territory').inputValue(),'La Graciosa');
});
