from datetime import datetime, timezone
from uuid import uuid4
from copy import deepcopy
import json
from pathlib import Path
from app.corpus import account_for
from fastapi import HTTPException

PRACTICES = {'diwali': 'Lighting the home', 'ahoi_ashtami': 'The children’s fast'}


def baseline(scenario):
    state = dict(id=str(uuid4()), scenario=scenario, version=0, generation=0, status='active',
                 profile={}, step='name', currents=[], captures=[], draft=None, account=None,
                 selected=None, events=[], voice='neutral')
    if scenario == 'avni':
        fixture = json.loads((Path(__file__).resolve().parent.parent/'content/demo/avni.v2.json').read_text())
        state.update(profile=fixture['profile'], step='explore', selected='ahoi_ashtami',
                     currents=fixture['currents'], threads=fixture['threads'], fixture_version=fixture['version'])
        for entry in fixture['captures']:
            state['captures'].append(dict(**entry,seeded=True,citations=[]))
        state['prompt'] = 'Welcome back, Avni. Your gulgule memories and the old Diwali light are here. In this Ahoi Season, shall we return to your question about the children’s fast?'
    else:
        state['prompt'] = 'What would you like me to call you?'
    return state


def unknown(practice):
    return dict(id=f'{practice}.unknown.v1', kind='unknown', title='What the texts can tell us', citations=[],
        text='No reviewed passage has been supplied for this practice yet. I cannot give a sourced explanation or settle what it means in your family. Your own memories can still be kept separately.', version=1)


def command(s, name, a):
    if s['status'] != 'active':
        raise HTTPException(409, 'This session is closed. Resume from the launcher.')
    if name == 'interrupt':
        s['generation'] += 1
    elif name == 'close':
        s['status'] = 'closed'
        s['generation'] += 1
    elif name == 'guard_test':
        s['status'] = 'route_out'
        s['draft'] = None
        s['generation'] += 1
        s['prompt'] = 'The prepared demo stop has ended this session. This is a test, not an evaluated crisis assessment.'
    elif name == 'submit_turn':
        text = str(a.get('text','')).strip()[:4000]
        if not text:
            raise HTTPException(422, 'Please supply an answer or choose skip.')
        step = s['step']
        lowered = text.lower()
        if step in ('name','location','origins','festivals'):
            if 'diwali' in lowered or any(v in lowered for v in ['ahoi','hoi asthami','hoi ashtami']):
                s['step'] = 'practice'
                s['festival'] = 'diwali' if 'diwali' in lowered else 'ahoi_ashtami'
                s['prompt'] = 'Which part of that tradition would you like to understand?'
            else:
                if lowered != 'skip':
                    s['profile'][step] = text
                steps = ['name','location','origins','festivals','practice']
                s['step'] = steps[steps.index(step)+1]
                s['prompt'] = {'location':'Where do you live?', 'origins':'Where does your family come from?', 'festivals':'Which festivals do you celebrate at home?', 'practice':'Which part of Diwali would you like to explore?'}[s['step']]
        else:
            if not s['selected']:
                raise HTTPException(409, 'Choose a practice first.')
            s['draft'] = dict(id=str(uuid4()), text=text, kind='family', current=s['selected'], citations=(s['account'] or {}).get('citations', []))
            s['prompt'] = 'Here is your draft. Edit it if you wish, then choose Keep to confirm these exact words. Nothing has been saved yet.'
    elif name == 'choose_practice':
        practice = a.get('practice')
        if (practice not in PRACTICES and not any(c['id'] == practice for c in s['currents'])) or a.get('intent') not in ['Learn','Practice']:
            raise HTTPException(422, 'Choose a supported practice and Intent.')
        if s['draft']:
            raise HTTPException(409, 'Keep or decline the current draft before changing Current.')
        if not any(c['id'] == practice for c in s['currents']):
            s['currents'].append(dict(id=practice, label=PRACTICES[practice], intent=a['intent'], depth=0))
        s.update(selected=practice, step='explore', account=account_for(practice), prompt='What does this look like in your family?')
    elif name == 'get_corpus_account':
        diwali_question=any(word in str(a.get('query','')).casefold() for word in ['diwali','lakshmi','laxmi','kali','shakti','bhakti'])
        if not s['selected'] or (s['selected']=='family' and diwali_question and not s.get('draft')):
            # This tool is specifically the Diwali demo corpus. A direct lookup
            # is Learn intent, even if onboarding has not chosen a Current yet.
            if not any(c['id']=='diwali' for c in s['currents']):
                s['currents'].append(dict(id='diwali',label=PRACTICES['diwali'],intent='Learn',depth=0))
            s.update(selected='diwali',step='explore')
        try:
            s['account'] = account_for(s['selected'],a.get('query',''),a.get('account_id'))
        except ValueError as error:
            raise HTTPException(422,str(error))
        s['prompt'] = s['account'].get('spoken',s['account']['text'])
    elif name == 'get_reopening':
        s['prompt'] = 'Would you like to return to the children’s-fast why thread?' if s['scenario'] == 'avni' else 'Choose a practice to begin your river.'
    elif name == 'draft_account':
        account = s.get('account')
        if not s['selected'] or not account or account['kind'] != 'cited':
            raise HTTPException(409, 'First bring a cited reading beside your river.')
        if s.get('draft'):
            raise HTTPException(409, 'Confirm or leave the current draft before preparing another.')
        s['draft'] = dict(id=str(uuid4()),text=account['text'],kind='source',current=s['selected'],
                          title=account['title'],account_id=account['id'],account_version=account['version'],
                          citations=deepcopy(account['citations']))
        s['prompt'] = f'I can keep the source reading “{account["title"]}” with its citations. This is a source summary, not a memory of your family. Say “keep this source” to confirm, or “leave it” to cancel.'
    elif name == 'draft_reading':
        if s.get('draft') and a.get('replace_draft_id') != s['draft']['id']:
            raise HTTPException(409, 'Confirm, decline or explicitly edit the displayed draft first.')
        if not str(a.get('text','')).strip():
            raise HTTPException(422, 'Supplied memory words are required.')
        if a.get('kind','family') not in ['family','own']:
            raise HTTPException(422, 'Use family or own reading.')
        if not s['selected']:
            # A fresh visitor may share a memory before choosing a festival.
            # Preserve it without assigning an invented religious affiliation.
            s['currents'].append(dict(id='family',label='Family stories',intent='Practice',depth=0))
            s.update(selected='family',step='explore')
        s['draft'] = dict(id=str(uuid4()), text=str(a['text']).strip()[:4000], kind=a.get('kind','family'), current=s['selected'], account_id=(s['account'] or {}).get('id'), account_version=(s['account'] or {}).get('version'), citations=deepcopy((s['account'] or {}).get('citations', [])))
        s['prompt'] = 'I can keep these exact words as a '+s['draft']['kind']+' reading: “'+s['draft']['text']+'” Say “keep that” to confirm, or “leave it” to cancel.'
    elif name == 'keep_reading':
        draft = s['draft']
        if not draft or a.get('draft_id') != draft['id'] or a.get('text') != draft['text'] or a.get('confirmed') is not True:
            raise HTTPException(409, 'Confirm the exact displayed draft before keeping it.')
        capture = dict(**draft, seeded=False, provenance='Explicitly confirmed private reading', created_at=datetime.now(timezone.utc).isoformat())
        s['captures'].append(capture)
        next(c for c in s['currents'] if c['id'] == draft['current'])['depth'] += 1
        s['draft'] = None
        s['last_commit'] = {'capture_id':capture['id'],'kind':capture['kind'],'title':capture.get('title'),'text':capture['text'],'sequence':s['version']+1}
        s['prompt'] = ('The source reading and its citations are now in your Riverbed.' if capture['kind']=='source' else 'Your exact words are now kept as a '+capture['kind']+' reading in your Riverbed.')
    elif name == 'decline':
        s['draft'] = None
        s['prompt'] = 'We can leave it here. Nothing new was kept.'
    elif name == 'discard':
        s['captures'] = [c for c in s['captures'] if c['id'] != a.get('capture_id')]
    else:
        raise HTTPException(422, 'Unknown command.')
    s['version'] += 1
    s['events'].append(dict(id=str(uuid4()), sequence=s['version'], type='capture.committed' if name == 'keep_reading' else name))
    return s
