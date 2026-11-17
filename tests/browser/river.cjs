const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs');
const base=process.env.SNGM_TEST_URL||'http://127.0.0.1:8024';
(async()=>{
 const browser=await chromium.launch({headless:true});const out='/tmp/sngm-journey-shots';fs.mkdirSync(out,{recursive:true});
 for(const width of [1440,390]){
 const page=await browser.newPage({viewport:{width,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'/demo/avni');await page.locator('#toggle').click();await page.waitForSelector('[data-stone="avni.gulgule.v2"]');await page.waitForTimeout(400);
 await page.screenshot({path:`${out}/avni-${width}.png`});
 const pebble=page.locator('[data-stone="avni.gulgule.v2"]');await pebble.hover({force:true});await page.waitForTimeout(550);await page.locator('.scrapbook-card').waitFor({state:'visible'});
 await page.screenshot({path:`${out}/scrapbook-${width}.png`});
 if(!await page.locator('.scrapbook-card img').evaluate(n=>n.complete&&n.naturalWidth>0))throw Error('missing image');
 await page.keyboard.press('Escape');
 const before=await pebble.boundingBox();const riverBounds=await page.locator('.river-space').boundingBox();await page.mouse.move(riverBounds.width*.15,riverBounds.height*.75);await page.mouse.wheel(0,550);await page.waitForTimeout(750);const after=await pebble.boundingBox();
 if(before&&after&&Math.abs(before.y-after.y)<20)throw Error('camera did not move');
 if(await page.locator('.river-space').evaluate(n=>n.scrollHeight>n.clientHeight))throw Error('river still has document scroll');
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('horizontal overflow');
 if(errors.length)throw Error(errors.join('\n'));console.log(`PASS ${width}: hover card, bundled image, camera travel, no river scroll/overflow`);await page.close();
 }
 const touch=await browser.newPage({viewport:{width:390,height:844},hasTouch:true,isMobile:true,reducedMotion:'reduce'});
 await touch.goto(base+'/demo/avni');await touch.locator('#toggle').click();
 const stone=touch.locator('[data-stone="avni.gulgule.v2"]');await stone.waitFor();
 await stone.tap();await touch.locator('.scrapbook-card').waitFor({state:'visible'});
 await touch.locator('.journey-header').tap({force:true});
 await touch.locator('.scrapbook-card').waitFor({state:'detached'});
 await touch.locator('.river-space').focus();
 const still=await stone.boundingBox();await touch.waitForTimeout(200);const same=await stone.boundingBox();
 if(Math.abs(still.y-same.y)>1)throw Error('reduced motion drifted');
 await touch.keyboard.press('ArrowDown');await touch.waitForTimeout(70);const moved=await stone.boundingBox();
 if(Math.abs(same.y-moved.y)<10)throw Error('keyboard camera did not move');
 await touch.close();console.log('PASS touch tap/outside close, keyboard navigation, reduced motion');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
