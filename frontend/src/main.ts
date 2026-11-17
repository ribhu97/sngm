import './style.css';
import { Realtime } from './realtime';
import { LocalVoice } from './local-voice';
import { runToRestore } from './entry';
import { keepPanel } from './components/reading';
import { riverWorld } from './components/river-world';
import { RiverJourney } from './river-journey';

type State={id:string;scenario:string;version:number;generation:number;status:string;profile:Record<string,string>;step:string;prompt:string;selected:string|null;currents:any[];captures:any[];draft:any;account:any;last_commit?:any;threads?:any[]};
type Guide=Realtime|LocalVoice;
let state:State|null=null, config:any, guide:Guide|null=null;
let running=false, starting=false, epoch=0, automatic:ReturnType<typeof setTimeout>|undefined;
let freshCaptureId:string|undefined;
let journey:RiverJourney|undefined;
let status='A moment to arrive', caption='', error='', queue:Promise<any>=Promise.resolve();
const root=document.querySelector<HTMLDivElement>('#app')!;
const escape=(value:any)=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
async function api(path:string,body?:any){
  const response=await fetch('/api'+path,{method:body?'POST':'GET',headers:body?{'Content-Type':'application/json'}:{},body:body?JSON.stringify(body):undefined});
  if(!response.ok){let data;try{data=await response.json();}catch{}throw new Error(typeof data?.detail==='string'?data.detail:'The guide could not connect. Please try again.');}
  return response.json();
}
function scenario(){return location.pathname==='/demo/avni'||new URLSearchParams(location.search).get('scenario')==='avni'?'avni':'diwali';}
function panels(){
 const container=document.getElementById('reading-panels');if(container)container.innerHTML=keepPanel(state?.draft,state?.captures.find(c=>c.id===freshCaptureId)||null);
}
function paint(){
 const returning=scenario()==='avni';
 const position=journey?.position||0;
 const opened=journey?.activeId;journey?.destroy();
 root.innerHTML=`<main class="sanctuary"><section class="river-space" tabindex="0" aria-label="Your family river. Use up and down arrows, wheel or drag to travel. Escape closes a memory."><div id="river-layer">${riverWorld(state,freshCaptureId)}</div></section><aside class="guide-space" aria-label="Your guide"><div class="guide-heading"><span class="tiny-line"></span>Your guide</div><div class="guide-presence" data-state="${running?escape(status.toLowerCase()):'resting'}"><svg viewBox="0 0 260 200" aria-hidden="true"><path class="presence-echo" d="M32 132 C60 141 49 56 91 64 C124 69 108 151 141 119 C178 85 188 49 228 75"/><path class="presence-ink" d="M32 132 C60 141 49 56 91 64 C124 69 108 151 141 119 C178 85 188 49 228 75"/></svg></div><div class="guide-copy"><p id="caption" class="caption" aria-live="polite">${escape(caption||(state?'Take a moment.\nWe’ll begin here.':returning?'Avni’s stories are here.\nLet’s pick up a thread.':'A place for the stories\nonly your family can tell.'))}</p><p id="guide-status" class="guide-status" role="status">${escape(status)}</p></div><button id="toggle" class="guide-toggle" aria-label="${running||starting?'Stop guide':'Start guide'}"><span class="control-icon ${running||starting?'stop':'play'}" aria-hidden="true"></span><span>${starting||running?'Stop guide':state?'Start guide':returning?'Open Avni’s river':'Start a fresh river'}</span></button>${!state?'<p class="entry-note">By entering, I confirm I am 18 or older.</p>':''}<p id="error" class="connection-note" role="alert">${escape(error)}</p><div id="reading-panels">${keepPanel(state?.draft,state?.captures.find(c=>c.id===freshCaptureId)||null)}</div></aside></main>`;
 journey=new RiverJourney(document.querySelector('.river-space')!,state,freshCaptureId,position);
 if(opened)journey.open(opened);
 document.getElementById('toggle')!.onclick=()=>{clearTimeout(automatic);if(running||starting)void stop();else if(state)void start();else void enter();};
}
function acceptState(next:State){
 if(state?.id===next.id && next.version<state.version)return;
 const prior=new Set(state?.captures.map(c=>c.id)||[]);
 const added=next.captures.find(c=>!c.seeded&&!prior.has(c.id));
 if(added)freshCaptureId=added.id;
 const facts=Object.keys(next.profile).filter(key=>state?.profile[key]!==next.profile[key]).map(key=>'profile-'+key);
 const newAccount=next.account?.id!==state?.account?.id;
 state=next;updateRiver();panels();
 journey?.announce([...facts,...(added?[added.id]:[])]);
 if(newAccount&&next.account)journey?.reveal('account-'+next.account.id);
}
function updateRiver(){
 const container=document.getElementById('river-layer');if(!container)return;
 const position=journey?.position||0,opened=journey?.activeId;journey?.destroy();
 container.innerHTML=riverWorld(state,freshCaptureId);
 journey=new RiverJourney(document.querySelector('.river-space')!,state,freshCaptureId,position);
 if(opened)journey.open(opened);
}
function setStatus(value:string){status=value;const node=document.getElementById('guide-status');if(node)node.textContent=value;const presence=document.querySelector<HTMLElement>('.guide-presence');if(presence)presence.dataset.state=value.toLowerCase();}
function setCaption(value:string){caption=value;const node=document.getElementById('caption');if(node)node.textContent=value;}
async function command(name:string,args:any={},id:string=crypto.randomUUID(),tool=false){
 const run=state!.id, generation=state!.generation;
 const task=queue.catch(()=>{}).then(async()=>{
  if(!state||state.id!==run||state.generation!==generation)throw new Error('This turn has ended.');
  const result=await api(`/demo/runs/${run}/${tool?'tool-calls':'commands'}`,{name,arguments:args,request_id:id,version:state.version,generation:state.generation});
  if(state?.id===run){acceptState(result);}return result;
 });queue=task;return task;
}
async function enter(){
 error='';try{state=await api('/demo/runs',{scenario:scenario(),adult:true,request_id:crypto.randomUUID()});sessionStorage.setItem('sngm-run',state!.id);sessionStorage.setItem('sngm-boot',config.server_instance);history.replaceState({},'','/app');paint();schedule();}catch(e){error=String(e instanceof Error?e.message:e);paint();}
}
function schedule(){clearTimeout(automatic);automatic=setTimeout(()=>void start(),5000);}
async function start(){
 if(starting||running||!state)return;
 const token=++epoch;error='';starting=true;setStatus('Connecting');paint();
 try{
  if(state.status==='route_out')throw new Error('This session has ended. Open a new river to begin again.');
  if(state.status!=='active')state=await api(`/demo/runs/${state.id}/resume`,{});
  if(token!==epoch)return;
  if(config.provider==='elevenlabs'){
   const credential=await api(`/demo/runs/${state!.id}/realtime-credential`,{});if(token!==epoch)return;
   guide=new Realtime(setStatus,async(name,args,id)=>{
    if(token!==epoch||name!=='apply_action')throw new Error('This turn has ended.');
    try{const result=await command(args.name,args.arguments,id,true);error='';document.getElementById('error')!.textContent='';return result.guide_result;}
    catch(e){error=e instanceof Error?e.message:String(e);document.getElementById('error')!.textContent='Not saved: '+error;throw e;}
   },setCaption);
   await guide.start(credential);
  }else if(config.provider==='lfm3'){
   guide=new LocalVoice(setStatus,async audio=>{
    const snapshot=state!;
    const result=await api(`/demo/runs/${snapshot.id}/voice-turn`,{name:'voice_turn',arguments:{audio},request_id:crypto.randomUUID(),version:snapshot.version,generation:snapshot.generation});
    if(token!==epoch)throw new Error('This turn has ended.');acceptState(result.state);return result.reply;
   },setCaption,message=>{if(token!==epoch)return;running=false;starting=false;guide=null;error=message;status='Ready when you are';paint();});
   await guide.start(state!.prompt);
  }else throw new Error('This experience needs a voice provider. Start the backend with ElevenLabs or LFM3.');
  if(token!==epoch){guide?.stop();return;}
  starting=false;running=true;paint();
 }catch(e){if(token!==epoch)return;guide?.stop();guide=null;starting=false;running=false;status='Ready when you are';error=e instanceof Error?e.message:String(e);paint();}
}
async function stop(){
 ++epoch;clearTimeout(automatic);guide?.stop();guide=null;running=false;starting=false;status='Paused';error='';paint();
 if(state?.status==='active'){try{await command('interrupt');}catch(e){error=e instanceof Error?e.message:String(e);paint();}}
}
window.addEventListener('pagehide',()=>{++epoch;clearTimeout(automatic);guide?.stop();journey?.destroy();});
async function init(){
 document.documentElement.dataset.theme='night';
 try{
  config=await api('/config');

  // Fresh demo routes never restore a previous identity. Ordinary /app reloads resume
  // only during the same backend boot; an explicit authorized resume remains possible.
  const run=runToRestore(location.pathname,location.search,sessionStorage.getItem('sngm-run'),sessionStorage.getItem('sngm-boot'),config.server_instance);
  if(run){state=await api(`/demo/runs/${run}`);if(state!.status!=='route_out')state=await api(`/demo/runs/${run}/resume`,{});sessionStorage.setItem('sngm-run',state!.id);sessionStorage.setItem('sngm-boot',config.server_instance);}
  else{sessionStorage.removeItem('sngm-run');sessionStorage.removeItem('sngm-boot');}
 }catch(e){error=e instanceof Error?e.message:String(e);}
 paint();if(state&&state.status==='active')schedule();
}void init();
