// Optional live review. Proxy transport forwards real IGN images, never fixtures.
const {chromium,request}=require('playwright');
const fs=require('node:fs'),path=require('node:path');
(async()=>{
 const root=path.resolve(__dirname,'..'),out=path.join(root,process.env.RISKLAB_REVIEW_DIR||'work/next-live');fs.mkdirSync(out,{recursive:true});
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,headless:true,args:['--no-sandbox','--use-angle=swiftshader','--enable-unsafe-swiftshader']});
 let tileClient;
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000},locale:'es-ES'}),errors=[],tileFailures=[];
  page.on('pageerror',e=>errors.push(e.message));
  if(process.env.RISKLAB_TILE_PROXY==='1'){
   tileClient=await request.newContext({proxy:{server:process.env.HTTPS_PROXY}});
   await page.route('https://www.ign.es/wms-inspire/**',async route=>{
    try{const response=await tileClient.get(route.request().url(),{timeout:25000});if(!response.ok())tileFailures.push('HTTP '+response.status());await route.fulfill({response});}
    catch(error){tileFailures.push(error.message.split('\n')[0]);await route.abort();}
   });
  }
  const start=Date.now(),response=await page.goto(process.env.RISKLAB_REVIEW_URL||'http://127.0.0.1:8790/next/');
  if(!response.ok())throw Error('La página local respondió HTTP '+response.status());
  await page.waitForFunction(()=>globalThis.risklabNext?.state.result||document.querySelector('#data-status')?.classList.contains('error'),{},{timeout:65000});
  await page.waitForFunction(()=>document.querySelectorAll('.leaflet-tile-loaded').length>0,{},{timeout:15000}).catch(()=>{});await page.waitForTimeout(700);
  const evidence={browser:browser.version(),viewport:{width:1440,height:1000},wall_ms:Date.now()-start,errors,tileFailures,mocked:false,tileTransport:process.env.RISKLAB_TILE_PROXY==='1'?'Real IGN responses via configured cloud proxy; TLS verification enabled':'Browser direct',state:await page.evaluate(()=>({snapshot:risklabNext.state.snapshot?.snapshot_id,quality:risklabNext.state.snapshot?.quality,statistics:risklabNext.state.result?.statistics,tiles:document.querySelectorAll('.leaflet-tile-loaded').length}))};
  await page.screenshot({path:path.join(out,'desktop-live.png')});
  await page.selectOption('#profile','research');await page.waitForTimeout(200);await page.screenshot({path:path.join(out,'research-live.png')});
  await page.selectOption('#profile','citizen');await page.click('#view3d');await page.waitForFunction(()=>risklabNext.state.earth?.viewer);await page.waitForTimeout(1800);if(await page.locator('#close-context').isVisible())await page.click('#close-context');await page.screenshot({path:path.join(out,'earth-live.png')});
  await page.click('#view2d');await page.setViewportSize({width:390,height:844});await page.click('#home');await page.waitForTimeout(600);await page.screenshot({path:path.join(out,'mobile-live.png')});
  fs.writeFileSync(path.join(out,'evidence.json'),JSON.stringify(evidence,null,2));console.log(JSON.stringify(evidence));
 }finally{await tileClient?.dispose();await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
