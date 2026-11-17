const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const base=process.env.SNGM_TEST_URL||'http://127.0.0.1:8024';
(async()=>{
 const b=await chromium.launch({headless:true});const p=await b.newPage({viewport:{width:1440,height:900}});const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.addInitScript(()=>{
 class Socket {
 static OPEN=1;readyState=1;sent=[];
 constructor(){window.demoSocket=this;setTimeout(()=>this.onopen?.(),20);}
 send(s){this.sent.push(JSON.parse(s));}close(){this.readyState=3;}
 emit(e){this.onmessage?.({data:JSON.stringify(e)});}
 }
 window.WebSocket=Socket;
 navigator.mediaDevices.getUserMedia=async()=>{const ac=new AudioContext();return ac.createMediaStreamDestination().stream;};
 });
 await p.route('**/api/config',async route=>{const response=await route.fetch();const json=await response.json();await route.fulfill({json:{...json,provider:'elevenlabs'}});});
 await p.route('**/realtime-credential',route=>route.fulfill({json:{url:'wss://mock.invalid',value:'test-only'}}));
 await p.goto(base+'/demo/diwali');await p.locator('#toggle').click();await p.waitForTimeout(100);await p.locator('#toggle').click();await p.waitForFunction(()=>window.demoSocket?.onmessage);
 const run=await p.evaluate(()=>sessionStorage.getItem('sngm-run'));
 async function action(name,args,id){
  await p.evaluate(({name,args,id})=>{const ws=window.demoSocket;ws.emit({type:'input_audio_buffer.speech_started'});ws.emit({type:'response.created',response:{id}});ws.emit({type:'response.function_call_arguments.done',response_id:id,name:'apply_action',arguments:JSON.stringify({name,arguments:args}),call_id:'call-'+id});ws.emit({type:'response.done',response:{id}});},{name,args,id});
  await p.waitForFunction(id=>window.demoSocket.sent.some(e=>e.type==='conversation.item.create'&&e.item.call_id==='call-'+id),id);
  return p.evaluate(id=>JSON.parse(window.demoSocket.sent.find(e=>e.type==='conversation.item.create'&&e.item.call_id==='call-'+id).item.output),id);
 }
 let result=await action('record_profile',{profile:{name:'Maya'},utterance:'My name is Maya'},'name');assert.equal(result.profile.name,'Maya');await p.locator('[data-stone="profile-name"]').waitFor();
 assert.match(await p.locator('.arrival-announcement').textContent(),/saved/);
 result=await action('draft_reading',{text:'We repaired the old light together.',kind:'family'},'draft');assert.ok(result.draft?.id);await p.locator('.keep-panel.pending').waitFor();
 result=await action('request_keep',{target:'family',utterance:'keep that please'},'keep');assert.ok(result.last_commit?.capture_id);await p.locator(`[data-stone="${result.last_commit.capture_id}"]`).waitFor();
 await p.waitForTimeout(1200);await p.screenshot({path:'/tmp/sngm-journey-shots/fresh-saved.png'});
 const saved=await p.evaluate(async run=>(await fetch('/api/demo/runs/'+run)).json(),run);assert.equal(saved.captures.length,1);assert.equal(saved.profile.name,'Maya');
 await p.reload();await p.locator(`[data-stone="${saved.captures[0].id}"]`).waitFor();
 assert.deepEqual(errors,[]);console.log('PASS fresh realtime event -> profile animation -> memory draft -> spoken Keep -> durable pebble -> reload');
 await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
