import { test } from 'node:test';
import assert from 'node:assert/strict';
import { runToRestore } from '../../frontend/src/entry.ts';
import { accountPanel, keepPanel, riverbed } from '../../frontend/src/components/reading.ts';

test('a backend restart never restores the old browser run',()=>{
 assert.equal(runToRestore('/app','', 'old-run','old-boot','new-boot'),null);
 assert.equal(runToRestore('/app','', 'same-run','boot','boot'),'same-run');
 for(const path of ['/','/demo','/demo/diwali','/demo/avni'])assert.equal(runToRestore(path,'','old-run','boot','boot'),null);
 assert.equal(runToRestore('/app','?scenario=avni','old-run','boot','boot'),null);
 assert.equal(runToRestore('/app','?resume=chosen','old-run','old','new'),'chosen');
});

test('pending and saved states explain the specific Keep target',()=>{
 const citation={id:'text',title:'A primary text',author:'An author',kind:'Primary text',locator:'Chapter 7',url:'https://example.org/text'};
 const draft={id:'draft',kind:'source',text:'Exact canonical summary',title:'A source reading',citations:[citation]};
 const pending=keepPanel(draft,null);
 assert.match(pending,/Not saved yet/);assert.match(pending,/keep this source/);assert.match(pending,/Exact canonical summary/);
 assert.match(pending,/not describe your family/);
 const saved=riverbed([{...draft,id:'capture'}],'capture');
 assert.match(saved,/Exact canonical summary/);assert.match(saved,/Chapter 7/);assert.match(saved,/just-kept/);
 assert.doesNotMatch(saved,/Not saved yet/);
});

test('rendered source content stays text and citation URLs cannot execute script',()=>{
 const html=accountPanel({kind:'cited',title:'<script>bad</script>',text:'<img onerror=bad>',citations:[{title:'Unsafe',author:'a',kind:'b',locator:'c',url:'javascript:bad()'}]});
 assert.doesNotMatch(html,/<script>|<img|href="javascript:/);
 assert.match(html,/&lt;script&gt;/);
});

import { ToolTurns } from '../../frontend/src/tool-turns.ts';
test('multiple tool calls produce one continuation and duplicate calls stop',async()=>{
 const turns=new ToolTurns();let calls=0;
 assert.equal(turns.register('response','profile',async()=>{calls++;}),true);
 assert.equal(turns.register('response','account',async()=>{calls++;}),true);
 assert.equal(turns.register('response','profile',async()=>{calls++;}),false);
 assert.equal(await turns.complete('response'),true);
 assert.equal(await turns.complete('response'),false);
 assert.equal(calls,2);
});
test('interrupted work cannot restart the guide after a new user turn',async()=>{
 const turns=new ToolTurns();let release!:()=>void;
 turns.register('old','tool',()=>new Promise<void>(resolve=>{release=resolve;}));
 const completion=turns.complete('old');await Promise.resolve();
 turns.newUserTurn();release();assert.equal(await completion,false);
});
test('tool chains stop after four rounds until new speech arrives',async()=>{
 const turns=new ToolTurns();
 for(let i=0;i<4;i++){assert.equal(turns.register(String(i),String(i),async()=>{}),true);assert.equal(await turns.complete(String(i)),true);}
 assert.equal(turns.register('loop','loop',async()=>{}),false);
 turns.newUserTurn();assert.equal(turns.register('next','loop',async()=>{}),true);
});

import { riverWorld, riverStones, scrapbook } from '../../frontend/src/components/river-world.ts';
import { readFileSync } from 'node:fs';
test('all Avni memories are anchored within named river reaches',()=>{
 const avni=JSON.parse(readFileSync(new URL('../../content/demo/avni.v2.json',import.meta.url),'utf8'));
 const html=riverWorld({...avni,scenario:'avni'});
 const stones=riverStones({...avni,scenario:'avni'});
 assert.equal(stones.filter(s=>s.type==='memory').length,5);
 assert.equal((html.match(/class="river-pebble memory/g)||[]).length,5);
 for(const c of avni.captures){const stone=stones.find(s=>s.id===c.id)!;assert.ok(stone.attachment);assert.ok(scrapbook(stone).includes(c.text.replace(/&/g,'&amp;')));}
 assert.match(html,/river-canvas/);assert.match(html,/Ahoi season/);assert.match(html,/Diwali season/);
 assert.doesNotMatch(html,/riverbed-entries|river-card memory-card/);
});
test('explanations distinguish quoted scripture from interpretation',()=>{
 const html=accountPanel({title:'A reading',text:'Our interpretation',citations:[{kind:'Primary text',title:'Scripture',excerpt:'A quoted passage',locator:'Verse 1',url:'https://example.org'}]});
 assert.match(html,/scripture-quote/);assert.match(html,/A quoted passage/);assert.match(html,/Interpretation · editorial reading/);assert.match(html,/Editorial illustration/);
});

import { projectRiver, riverCenter } from '../../frontend/src/river-journey.ts';
test('moving downstream changes perspective while keeping anchors on the river',()=>{
 const z=950,x=riverCenter(z);
 const before=projectRiver(z,x,0,900,800),after=projectRiver(z,x,400,900,800);
 assert.ok(after.y>before.y);assert.ok(after.scale>before.scale);
 assert.equal(projectRiver(z,x,1100,900,800).visible,false);
});
test('fresh setup and confirmed memories have separate pebbles and safe scrapbook content',()=>{
 const stones=riverStones({profile:{name:'Maya'},currents:[{id:'family',label:'Family stories'}],captures:[{id:'m',current:'family',kind:'family',text:'<script>bad</script>',citations:[]}]},'m');
 assert.equal(stones[0].type,'profile');assert.match(scrapbook(stones[0]),/saved/);
 const memory=stones.find(s=>s.id==='m')!;assert.equal(memory.fresh,true);
 assert.match(scrapbook(memory),/&lt;script&gt;/);assert.doesNotMatch(scrapbook(memory),/<script>/);
 assert.match(scrapbook(memory),/Photograph credit/);assert.match(scrapbook(memory),/not a family photograph/);
});
