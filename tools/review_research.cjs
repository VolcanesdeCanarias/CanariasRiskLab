// Actual app + bundled verified historical USGS response. No observation fixtures.
const {chromium,request}=require('playwright'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,'work/product01/live');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});let client;
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000},locale:'es-ES'}),errors=[],imageFailures=[];page.on('pageerror',e=>errors.push(e.message));
  if(process.env.RISKLAB_TILE_PROXY==='1'){
   client=await request.newContext({proxy:{server:process.env.HTTPS_PROXY}});
   await page.route('https://www.ign.es/wms-inspire/**',async route=>{try{const r=await client.get(route.request().url(),{timeout:25000});if(!r.ok())imageFailures.push(r.status());await route.fulfill({response:r});}catch{imageFailures.push('transport_error');await route.abort();}});
  }
  await page.goto(process.env.RISKLAB_REVIEW_URL||'http://127.0.0.1:8787/next/');await page.locator('#open-study').waitFor();await page.waitForFunction(()=>!document.querySelector('#open-study').disabled);
  await page.selectOption('#territory','Tenerife');await page.selectOption('#volcanic-system','gvp-383030');await page.click('#open-study');await page.waitForFunction(()=>globalThis.risklabNext?.study.run?.periods.current.count===11,{},{timeout:65000});
  await page.waitForFunction(()=>document.querySelectorAll('.leaflet-tile-loaded').length>0,{},{timeout:20000}).catch(()=>{});await page.waitForFunction(()=>{const images=[...document.querySelectorAll('.leaflet-tile')];return images.length>0&&images.every(i=>i.complete&&i.naturalWidth>0);},{},{timeout:25000}).catch(()=>{});await page.waitForTimeout(500);
  const result=await page.evaluate(()=>risklabNext.study.run);fs.writeFileSync(path.join(out,'run.json'),JSON.stringify(result,null,2));
  const capture=async name=>page.screenshot({path:path.join(out,name+'.jpg'),type:'jpeg',quality:86});
  await capture('01-context-desktop');await page.locator('#study-catalogue').scrollIntoViewIfNeeded();await capture('02-historical-series');
  await page.locator('#study-findings').scrollIntoViewIfNeeded();await capture('03-reproducible-analysis');
  await page.locator('#study-question').scrollIntoViewIfNeeded();await page.fill('#study-question','¿Qué limita esta cobertura?');await page.click('#study-ask');await page.waitForFunction(()=>document.querySelector('#study-answer').textContent.includes('completitud'));await capture('04-grounded-assistance');
  await page.locator('#study-territory').scrollIntoViewIfNeeded();await capture('05-territorial-context');
  const base=new URL(page.url()).origin;for(const kind of ['report.html','evidence.zip']){const r=await page.request.get(`${base}/api/v1/research/runs/${result.run_id}/export/${kind}`);if(!r.ok())throw Error(`Export ${kind}: HTTP ${r.status()}`);fs.writeFileSync(path.join(out,kind),await r.body());}
  const reportPage=await browser.newPage({viewport:{width:1280,height:1000}});await reportPage.setContent(fs.readFileSync(path.join(out,'report.html'),'utf8'));await reportPage.screenshot({path:path.join(out,'06-exported-report.jpg'),type:'jpeg',quality:86});await reportPage.close();
  await page.setViewportSize({width:390,height:844});await page.locator('#study-science').scrollIntoViewIfNeeded();await capture('07-mobile-context');await page.locator('#study-findings').scrollIntoViewIfNeeded();await capture('08-mobile-analysis');
  const evidence={browser:browser.version(),data:'Actual archived USGS ComCat; no generated observation fixtures; not real-time monitoring',dataset:result.dataset_hash,run_id:result.run_id,current:result.periods.current.count,previous:result.periods.previous.count,ratio:result.comparison.catalogue_rate_ratio,nearest_neighbour_median_km:result.spatial.nearest_neighbour_median_km,errors,imageFailures,imagesLoaded:await page.locator('.leaflet-tile-loaded').count(),tileTransport:process.env.RISKLAB_TILE_PROXY==='1'?'Authentic IGN images via configured proxy, TLS verified':'Browser direct',institutional:'not enabled'};
  fs.writeFileSync(path.join(out,'evidence.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));
 }finally{await client?.dispose();await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
