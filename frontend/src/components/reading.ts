/** One source renderer is shared by the live account, pending Keep and Riverbed. */
export interface Citation { id:string; title:string; author:string; kind:string; locator:string; url:string; excerpt?:string; summary?:string }
export interface Reading { id:string; kind:string; text:string; title?:string; citations:Citation[]; current?:string; seeded?:boolean; provenance?:string; created_at?:string }
export const escapeHTML=(v:unknown)=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]!));
const e=escapeHTML;
const typeName=(kind:string)=>kind==='source'?'Source reading':kind==='own'?'Own interpretation':'Family memory';
export function citations(items:Citation[],expanded=false){
 if(!items?.length)return '';
 return `<details class="citations" ${expanded?'open':''}><summary>${items.length} ${items.length===1?'source':'sources'} · follow the evidence</summary><ol>${items.map(c=>`<li><span class="source-kind">${e(c.kind)}</span><a href="${e(/^https:\/\//.test(c.url)?c.url:'#')}" target="_blank" rel="noopener noreferrer">${e(c.title)} <span aria-hidden="true">↗</span></a><span class="source-author">${e(c.author)}</span><span class="source-locator">${e(c.locator)}</span>${c.excerpt?`<blockquote lang="${/[\u0900-\u097f]/.test(c.excerpt)?'sa':'en'}">${e(c.excerpt)}</blockquote>`:''}${c.summary?`<p>${e(c.summary)}</p>`:''}</li>`).join('')}</ol></details>`;
}
export function accountPanel(account:any){
 if(!account)return '';
 const quote=(account.citations||[]).find((c:Citation)=>c.excerpt&&c.kind.startsWith('Primary'));
 const illustration='<svg class="reading-illustration" viewBox="0 0 120 100" role="img" aria-label="Editorial illustration of a lamp on water"><path d="M15 64 Q60 104 105 64 Z M60 61 C35 42 65 31 62 10 C87 35 85 54 60 61Z M9 91 Q35 85 60 91 T113 91" fill="none" stroke="currentColor" stroke-width="1.5"/><circle cx="60" cy="54" r="3" fill="currentColor"/></svg>';
 return `<section class="reading-panel" aria-label="Reading and citations"><span class="panel-kicker">${account.kind==='cited'?'From the Corpus · demo selection':'An open question'}</span>${illustration}<h2>${e(account.title)}</h2>${quote?`<blockquote class="scripture-quote">${e(quote.excerpt)}<cite>${e(quote.title)} · ${e(quote.locator)}</cite></blockquote>`:''}<span class="interpretation-label">Interpretation · editorial reading</span><p class="reading-text">${e(account.text)}</p>${account.limits?`<p class="reading-limit">${e(account.limits)}</p>`:''}${citations(account.citations||[],true)}${account.kind==='cited'?'<p class="source-invitation">To keep this with its sources, say “keep this reading.”</p>':''}</section>`;
}
export function keepPanel(draft:Reading|null,last:Reading|null){
 if(draft)return `<section class="keep-panel pending" aria-live="polite" aria-label="Reading awaiting your confirmation"><span class="panel-kicker">Not saved yet · ${e(typeName(draft.kind))}</span><h2>This is what I’ll keep</h2>${draft.title?`<h3>${e(draft.title)}</h3>`:''}<p class="draft-words">“${e(draft.text)}”</p><p class="keep-explanation">${draft.kind==='source'?'The source summary and its citations will be saved together. This does not describe your family’s beliefs.':'Your exact words will be saved as a private '+e(typeName(draft.kind).toLowerCase())+'. The sources below are context, not proof of your memory.'}</p>${citations(draft.citations||[])}<p class="spoken-action">Say <strong>“${draft.kind==='source'?'keep this source':'keep that'}”</strong> to confirm, or “leave it” to cancel.</p></section>`;
 if(last)return `<section class="keep-panel committed" role="status"><span class="panel-kicker">Kept in your Riverbed · ${e(typeName(last.kind))}</span><p>${e(last.title||last.text)}</p><span class="commit-note">Saved with ${last.citations?.length||0} source references. It is now anchored to the river.</span></section>`;
 return '';
}
export function riverbed(readings:Reading[],freshId?:string){
 if(!readings?.length)return '';
 return `<section class="riverbed" aria-label="The Riverbed"><div class="riverbed-title"><h2>The Riverbed</h2><span>${readings.length} kept ${readings.length===1?'reading':'readings'}</span></div><p class="riverbed-intro">${readings.every(c=>c.seeded)?'Illustrative stored history, ready to return to.':'Confirmed readings stay here. Setup details above are separate.'}</p><div class="riverbed-entries">${readings.slice().reverse().map(c=>`<article class="riverbed-entry ${c.id===freshId?'just-kept':''}"><span class="panel-kicker">${e(typeName(c.kind))}${c.seeded?' · illustrative demo history':''}</span>${c.title?`<h3>${e(c.title)}</h3>`:''}<p>${e(c.text)}</p>${citations(c.citations||[])}${c.provenance?`<details class="provenance"><summary>About this reading</summary><p>${e(c.provenance)}</p><span>${e(c.created_at)}</span></details>`:''}</article>`).join('')}</div></section>`;
}
