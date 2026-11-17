import { accountPanel, citations, escapeHTML as e } from './reading.ts';

export interface RiverStone {
 id:string; type:'profile'|'memory'|'account'; label:string; attachment:string;
 z:number; bank:number; value:any; fresh?:boolean;
}
const factLabels:Record<string,string>={name:'You',location:'Home now',origins:'Family roots',festivals:'Celebrations'};
export function riverStones(state:any,freshId?:string):RiverStone[]{
 const facts:RiverStone[]=Object.entries(state?.profile||{}).map(([key,value],i)=>({id:`profile-${key}`,type:'profile',label:String(value),attachment:factLabels[key]||key,z:280+i*160,bank:i%2?1:-1,value:{text:value,key}}));
 let z=950;
 const memories:RiverStone[]=[];
 const currents=state?.currents||[];
 for(const current of [...currents,{id:null,label:'Family stories'}]){
  const captures=(state?.captures||[]).filter((c:any)=>current.id?c.current===current.id:!currents.some((g:any)=>g.id===c.current));
  for(const c of captures){memories.push({id:c.id,type:'memory',label:c.title||c.text,attachment:`${current.label} · ${current.id==='diwali'?'Diwali season':current.id==='ahoi_ashtami'?'Ahoi season':'Family thread'}`,z,bank:memories.length%2?1:-1,value:c,fresh:c.id===freshId});z+=340;}
 }
 if(state?.account)memories.unshift({id:`account-${state.account.id}`,type:'account',label:state.account.title,attachment:'An explanation · not kept yet',z:820,bank:-1,value:state.account});
 return [...facts,...memories];
}
export const riverExtent=(stones:RiverStone[])=>Math.max(1200,...stones.map(s=>s.z+280));
export function riverWorld(state:any,freshId?:string){
 const stones=riverStones(state,freshId);
 return `<div class="river-journey"><canvas class="river-canvas" aria-hidden="true"></canvas><header class="journey-header"><div class="wordmark">sngm<span>${state?.scenario==='avni'?'Avni’s family river':'A family river'}</span></div><p class="journey-eyebrow">A living river of what you carry</p></header><div class="river-atmosphere" aria-hidden="true"></div><div class="river-stones">${stones.map(s=>`<button class="river-pebble ${s.type} ${s.fresh?'just-kept':''}" data-stone="${e(s.id)}" aria-expanded="false" aria-controls="river-scrapbook" aria-label="${e(s.attachment)}: ${e(s.label)}"><span class="pebble-body" aria-hidden="true"><span>${s.type==='profile'?'·':s.type==='account'?'✦':'◌'}</span></span><span class="pebble-label"><small>${e(s.attachment)}</small><span>${e(s.label)}</span></span></button>`).join('')}</div><div class="journey-intro"><span class="panel-kicker">${state?.scenario==='avni'?'Avni’s riverbed':'Every river begins somewhere'}</span><h1>${state?.scenario==='avni'?'The things we carry.':'Let the story find its course.'}</h1></div><div id="river-scrapbook" class="scrapbook-slot"></div><div class="arrival-announcement" role="status" aria-live="polite"></div><footer class="journey-compass"><span class="journey-direction">Downstream ↓</span><span class="journey-instruction">Wheel or drag to drift · hover a pebble to remember</span><span class="journey-depth">Headwaters</span></footer></div>`;
}
export function stonePhoto(stone:RiverStone){
 const text=`${stone.attachment} ${stone.label}`.toLowerCase();
 if(/gulgule|recipe|food/.test(text))return {file:'gulgule.jpg',alt:'Gulgule fritters on a plate',artist:'Suyash Dwivedi',license:'CC BY-SA 4.0',url:'https://commons.wikimedia.org/wiki/File:Gulgule.jpg',licenseUrl:'https://creativecommons.org/licenses/by-sa/4.0/'};
 if(/old|father|light brings|repairing/.test(text))return {file:'lights.jpg',alt:'Festival lights at Diwali',artist:'Ramesh NG',license:'CC BY-SA 2.0',url:'https://commons.wikimedia.org/wiki/File:Happy_Diwali_-_Festival_of_light.jpg',licenseUrl:'https://creativecommons.org/licenses/by-sa/2.0/'};
 return {file:'lamp.jpg',alt:'An earthen oil lamp burning',artist:'Joydeep',license:'CC BY-SA 3.0',url:'https://commons.wikimedia.org/wiki/File:An_oil_lamp_17_10_2010.JPG',licenseUrl:'https://creativecommons.org/licenses/by-sa/3.0/'};
}
export function scrapbook(stone:RiverStone){
 const c=stone.value,photo=stonePhoto(stone);
 const image=`<figure class="scrapbook-photo"><img src="/assets/scrapbook/${photo.file}" alt="${photo.alt}"/><figcaption>Visual context · not a family photograph</figcaption></figure>`;
 const credits=`<details class="photo-credit"><summary>Photograph credit</summary><a href="${photo.url}" target="_blank" rel="noopener noreferrer">${photo.artist}</a> · <a href="${photo.licenseUrl}" target="_blank" rel="noopener noreferrer">${photo.license}</a> · cropped for display</details>`;
 if(stone.type==='account')return `<article class="scrapbook-card" aria-label="Explanation and sources">${image}${accountPanel(c)}${credits}</article>`;
 if(stone.type==='profile')return `<article class="scrapbook-card profile-page" aria-label="Saved setup detail"><span class="scrapbook-tape" aria-hidden="true"></span><span class="panel-kicker">${e(stone.attachment)} · saved</span><h2>${e(c.text)}</h2><p class="scrapbook-note">Part of your river’s beginnings. You can tell the guide if this changes.</p><span class="scrapbook-date">Setup detail · separate from kept memories</span></article>`;
 return `<article class="scrapbook-card" aria-label="Kept memory"><span class="scrapbook-tape" aria-hidden="true"></span>${image}<span class="panel-kicker">${e(stone.attachment)}</span><span class="scrapbook-date">${c.kind==='own'?'Your interpretation':c.kind==='source'?'Source reading':'Family memory'} · ${c.seeded?'illustrative history':'kept'}</span>${c.title?`<h2>${e(c.title)}</h2>`:''}<p class="scrapbook-words">“${e(c.text)}”</p>${citations(c.citations||[])}${c.provenance?`<details class="provenance"><summary>About this memory</summary><p>${e(c.provenance)}</p><span>${e(c.created_at)}</span></details>`:''}${credits}<span class="scrapbook-page">A pebble in your riverbed</span></article>`;
}
