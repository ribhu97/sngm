import { riverStones, riverExtent, scrapbook, type RiverStone } from './components/river-world.ts';

export const clamp=(v:number,min:number,max:number)=>Math.max(min,Math.min(max,v));
export const riverCenter=(z:number)=>Math.sin(z/640)*150+Math.sin(z/1300)*95;
/** Perspective projection shared by the water and the memory anchors. */
export function projectRiver(z:number,x:number,camera:number,width:number,height:number){
 const distance=z-camera,scale=620/(620+Math.max(-200,distance));
 const center=riverCenter(camera+180);
 return {x:width/2+(x-center)*scale*width/850,y:height*.09+height*.97*scale,scale,visible:distance>-80&&distance<2800};
}
export class RiverJourney {
 position=0;private target=0;private raf=0;private last=0;private width=1;private height=1;
 private stones:RiverStone[]=[];private max=1200;private active?:string;private pinned=false;private closeTimer=0;
 private canvas:HTMLCanvasElement;private ctx:CanvasRenderingContext2D;private observer:ResizeObserver;
 private buttons=new Map<string,HTMLElement>();private reduced=matchMedia('(prefers-reduced-motion: reduce)');
 private drag?:{y:number;pointer:number};private lifetime=new AbortController();private announcementTimer=0;
 private revealTimer=0;private pointerFocus=false;
 get activeId(){return this.active;}
 private host:HTMLElement;
 constructor(host:HTMLElement,state:any,freshId?:string,position=0){
  this.host=host;
  this.position=this.target=position;this.stones=riverStones(state,freshId);this.max=riverExtent(this.stones);
  this.canvas=host.querySelector('canvas')!;this.ctx=this.canvas.getContext('2d')!;
  host.querySelectorAll<HTMLElement>('[data-stone]').forEach(n=>this.buttons.set(n.dataset.stone!,n));
  this.observer=new ResizeObserver(()=>{const rect=host.getBoundingClientRect();this.width=rect.width;this.height=rect.height;const dpr=Math.min(devicePixelRatio||1,2);this.canvas.width=rect.width*dpr;this.canvas.height=rect.height*dpr;this.ctx.setTransform(dpr,0,0,dpr,0,0);this.draw(0);});this.observer.observe(host);
  const signal=this.lifetime.signal;
  window.addEventListener('keydown',e=>{if(e.key==='Escape'&&this.active){e.preventDefault();this.close();}},{signal});
  host.addEventListener('wheel',e=>{if(e.ctrlKey||e.metaKey||this.insideCard(e.target))return;e.preventDefault();this.close();this.target=clamp(this.target+e.deltaY*(e.deltaMode===1?22:e.deltaMode===2?this.height:1)*1.2,0,this.max);},{passive:false,signal});
  host.addEventListener('pointerdown',e=>{if(!e.isPrimary||e.button>0)return;this.pointerFocus=true;if((e.target as HTMLElement).closest('button,a,summary,.scrapbook-card'))return;this.close();this.drag={y:e.clientY,pointer:e.pointerId};host.setPointerCapture(e.pointerId);},{signal});
  host.addEventListener('pointermove',e=>{if(!this.drag)return;this.target=clamp(this.target+(this.drag.y-e.clientY)*2.4,0,this.max);this.drag.y=e.clientY;},{signal});
  for(const event of ['pointerup','pointercancel'])host.addEventListener(event,()=>{this.drag=undefined;},{signal});
  host.addEventListener('keydown',e=>{
   this.pointerFocus=false;
   if(e.key==='Escape'){this.close();return;}
   if(this.insideCard(e.target)||['INPUT','TEXTAREA'].includes((e.target as HTMLElement).tagName))return;
   const delta=({ArrowDown:180,ArrowUp:-180,PageDown:550,PageUp:-550,' ':400} as Record<string,number>)[e.key];
   if(delta!==undefined||e.key==='Home'||e.key==='End'){e.preventDefault();this.close();this.target=clamp(e.key==='Home'?0:e.key==='End'?this.max:this.target+delta,0,this.max);}
  },{signal});
  host.addEventListener('pointerover',e=>{if(e.pointerType==='touch')return;const button=(e.target as HTMLElement).closest<HTMLElement>('[data-stone]');if(button){clearTimeout(this.closeTimer);this.open(button.dataset.stone!);}else if(this.insideCard(e.target))clearTimeout(this.closeTimer);},{signal});
  host.addEventListener('pointerout',e=>{if(this.pinned||!this.active)return;const next=e.relatedTarget as HTMLElement|null;if(next?.closest('[data-stone],.scrapbook-card'))return;this.closeTimer=window.setTimeout(()=>this.close(),350);},{signal});
  host.addEventListener('focusin',e=>{const button=(e.target as HTMLElement).closest<HTMLElement>('[data-stone]');if(button&&!this.pointerFocus)this.open(button.dataset.stone!);},{signal});
  host.addEventListener('focusout',e=>{const next=e.relatedTarget as HTMLElement|null;if(!next?.closest('[data-stone],.scrapbook-card'))this.close();},{signal});
  host.addEventListener('click',e=>{this.pointerFocus=false;const button=(e.target as HTMLElement).closest<HTMLElement>('[data-stone]');if(button){if(this.active===button.dataset.stone&&this.pinned){this.close();return;}this.open(button.dataset.stone!);this.pinned=true;}else if(!this.insideCard(e.target))this.close();},{signal});
  this.tick= this.tick.bind(this);this.raf=requestAnimationFrame(this.tick);
 }
 private insideCard(target:EventTarget|null){return !!(target as HTMLElement|null)?.closest?.('.scrapbook-card');}
 goTo(position:number,immediate=false){this.target=clamp(position,0,this.max);if(immediate||this.reduced.matches){this.position=this.target;this.draw(0);}}
 reveal(id:string){const stone=this.stones.find(s=>s.id===id);if(!stone)return;this.close();this.goTo(stone.z-420);clearTimeout(this.revealTimer);this.revealTimer=window.setTimeout(()=>this.open(id),this.reduced.matches?0:650);}
 announce(ids:string[]){
  const text:string[]=[];
   for(const id of ids){const button=this.buttons.get(id),stone=this.stones.find(s=>s.id===id);if(!button||!stone)continue;button.classList.add('arriving');text.push(`${stone.attachment}: ${stone.label}`);
    if(!this.reduced.matches){const flight=document.createElement('span');flight.className='river-arrival-flight';flight.textContent=stone.label;this.host.append(flight);const p=projectRiver(stone.z,riverCenter(stone.z)+stone.bank*(stone.type==='profile'?180:105),Math.max(0,stone.z-380),this.width,this.height);const animation=flight.animate([{transform:`translate(${this.width-160}px,${this.height*.4}px) scale(1)`,opacity:0},{offset:.2,opacity:1},{transform:`translate(${p.x-50}px,${p.y}px) scale(.25)`,opacity:0}],{duration:1400,easing:'cubic-bezier(.2,.7,.2,1)'});animation.onfinish=()=>flight.remove();}
   }
  if(ids.length){const stone=this.stones.find(s=>s.id===ids.at(-1));if(stone)this.goTo(stone.z-380);}
  const live=this.host.querySelector<HTMLElement>('.arrival-announcement')!;live.textContent=text.length?`${text.join(' · ')} — saved to your river`:'';
  clearTimeout(this.announcementTimer);this.announcementTimer=window.setTimeout(()=>{live.textContent='';},5500);
 }
 open(id:string){
  clearTimeout(this.closeTimer);if(id===this.active)return;
  const stone=this.stones.find(s=>s.id===id),button=this.buttons.get(id);if(!stone||!button)return;
  this.close();this.active=id;button.setAttribute('aria-expanded','true');
  const slot=this.host.querySelector<HTMLElement>('.scrapbook-slot')!;slot.innerHTML=scrapbook(stone);slot.classList.add('is-open');
  const card=slot.firstElementChild as HTMLElement;
  const origin=button.getBoundingClientRect(),bounds=this.host.getBoundingClientRect();
  const width=Math.min(350,this.width-40),left=clamp(origin.left-bounds.left-width/2,20,this.width-width-20);
  const top=clamp(origin.top-bounds.top-160,100,Math.max(100,this.height-350));
  slot.style.left=`${left}px`;slot.style.top=`${top}px`;slot.style.width=`${width}px`;
  card.style.maxHeight=`${Math.max(160,this.height-top-75)}px`;
  if(!this.reduced.matches)card.animate([{opacity:0,transform:`translate(${origin.left-bounds.left-left}px,${origin.top-bounds.top-top}px) scale(.12) rotate(-16deg)`,borderRadius:'50%'},{opacity:1,transform:'translate(0,0) scale(1) rotate(-1deg)',borderRadius:'2px'}],{duration:480,easing:'cubic-bezier(.2,.8,.2,1)',fill:'both'});
 }
 close(){clearTimeout(this.closeTimer);if(this.active)this.buttons.get(this.active)?.setAttribute('aria-expanded','false');this.active=undefined;this.pinned=false;const slot=this.host.querySelector<HTMLElement>('.scrapbook-slot');if(slot){slot.classList.remove('is-open');slot.innerHTML='';}}
 private tick(now:number){
  const dt=Math.min((now-(this.last||now))/1000,.05);this.last=now;
  if(!document.hidden){
   if(!this.active&&!this.drag&&!this.reduced.matches)this.target=clamp(this.target+dt*12,0,this.max);
   this.position=this.reduced.matches?this.target:this.position+(this.target-this.position)*(1-Math.exp(-dt*5));
   this.draw(now);
  }
  this.raf=requestAnimationFrame(this.tick);
 }
 private draw(now:number){
  const c=this.ctx,w=this.width,h=this.height;if(w<2||h<2)return;
  c.clearRect(0,0,w,h);c.fillStyle='#102c2d';c.fillRect(0,0,w,h);
  const point=(z:number,offset:number)=>projectRiver(z,riverCenter(z)+offset,this.position,w,h);
  const riverShape=(width:number,color:string)=>{
   c.beginPath();for(let i=130;i>=0;i--){const z=this.position-70+i*i*2,p=point(z,-width);if(i===130)c.moveTo(p.x,p.y);else c.lineTo(p.x,p.y);}for(let i=0;i<=130;i++){const p=point(this.position-70+i*i*2,width);c.lineTo(p.x,p.y);}c.closePath();c.fillStyle=color;c.fill();
  };
  riverShape(420,'#1c3833');riverShape(305,'#344e41');riverShape(285,'#426355');riverShape(264,'#33625d');riverShape(222,'#28534f');
  const flow=this.reduced.matches?0:now*.028;
  for(let i=0;i<110;i++){
   const z=Math.floor(this.position/2800)*2800+(i*173+flow)%2800;
   const p=point(z,Math.sin(i*71)*210);if(!p.visible)continue;
   c.strokeStyle=`rgba(196,217,184,${.08+p.scale*.1})`;c.lineWidth=.5+p.scale;
   c.beginPath();c.moveTo(p.x,p.y);const q=point(z+24+p.scale*20,Math.sin(i*71)*210);c.lineTo(q.x,q.y);c.stroke();
  }
  // Quiet, submerged stones give the riverbed texture and depth.
  for(let i=0;i<90;i++){
   const z=i*87,p=point(z,Math.sin(i*9.7)*230);if(!p.visible)continue;
   c.fillStyle=i%3?'#b1b48c18':'#d4c69a24';c.beginPath();c.ellipse(p.x,p.y,Math.max(1,8*p.scale),Math.max(1,4*p.scale),i,0,Math.PI*2);c.fill();
  }
  const glow=c.createLinearGradient(0,0,0,h*.5);glow.addColorStop(0,'#102c2d');glow.addColorStop(.4,'#142f2d99');glow.addColorStop(1,'#142f2d00');c.fillStyle=glow;c.fillRect(0,0,w,h*.5);
  for(const stone of this.stones){const p=point(stone.z,stone.bank*(stone.type==='profile'?180:105));const button=this.buttons.get(stone.id)!;button.style.left=`${p.x}px`;button.style.top=`${p.y}px`;button.style.setProperty('--stone-scale',String(clamp(p.scale,.7,1.15)));const visible=p.visible&&p.y>110&&p.y<h-55;button.style.visibility=visible?'visible':'hidden';button.classList.toggle('distant',p.scale<.48);button.tabIndex=0;button.style.zIndex=String(Math.round(p.scale*30));}
  const intro=this.host.querySelector<HTMLElement>('.journey-intro');if(intro){intro.style.opacity=String(clamp(1-this.position/500,0,1));intro.style.transform=`translateY(${-this.position*.08}px)`;}
  const depth=this.host.querySelector('.journey-depth');if(depth)depth.textContent=this.position<180?'Headwaters':`${Math.round(this.position/this.max*100)}% downstream`;
 }
 destroy(){cancelAnimationFrame(this.raf);clearTimeout(this.closeTimer);clearTimeout(this.announcementTimer);clearTimeout(this.revealTimer);this.host.querySelectorAll('.river-arrival-flight').forEach(n=>n.remove());this.observer.disconnect();this.lifetime.abort();}
}
