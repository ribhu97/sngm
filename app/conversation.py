"""Shared conversational onboarding; supplied facts are distinct from kept readings."""
import re
from fastapi import HTTPException
from app.domain import command

FIELDS = ('name', 'location', 'origins', 'festivals')
QUESTIONS = {
    'name': 'Welcome. I’m here to help you follow the traditions your family carries. What would you like me to call you?',
    'location': 'And where do you call home these days?',
    'origins': 'Where does your family come from?',
    'festivals': 'Which festivals feel most like home to you?',
    'practice': 'What part of that tradition would you like to explore? And would you like to understand it, or try practising it?',
    'explore': 'What does this look like in your family? Is there a memory that comes to mind?',
}


def next_question(s):
    if s.get('draft') and s['draft']['kind']=='source':
        return s['prompt']
    if s.get('draft'):
        return f'You said: “{s["draft"]["text"]}” Would you like me to keep those exact words in your river?'
    if s.get('selected'):
        return QUESTIONS['explore']
    for field in FIELDS:
        if not s['profile'].get(field) and field not in s.get('skipped', []):
            s['step'] = field
            return QUESTIONS[field]
    s['step'] = 'practice'
    return QUESTIONS['practice']


def record_profile(s, a):
    values = a.get('profile', {})
    utterance = str(a.get('utterance', '')).strip()
    if not utterance or not isinstance(values, dict):
        raise HTTPException(422, 'Supplied user words are required.')
    for field, value in values.items():
        if field not in FIELDS or not isinstance(value,str) or not value.strip() or len(value)>500:
            raise HTTPException(422, 'Invalid supplied profile field.')
        if field == 'name' and re.search(r'\b(live|based|come from)\b',utterance,re.I) and not re.search(r'\b(name|call me)\b',utterance,re.I):
            raise HTTPException(422,'A place of residence must not be recorded as a name.')
        if field == 'name' and s['step'] != 'name' and not re.search(r'\b(name|call me|actually|correction)\b',utterance,re.I):
            raise HTTPException(422,'A name correction must be explicit.')
        if value.strip().casefold() not in utterance.casefold():
            raise HTTPException(422, 'Record only details present in the supplied words.')
    if not values:
        raise HTTPException(422, 'No supplied facts.')
    supplied={key:value.strip() for key,value in values.items()}
    if all(s['profile'].get(key)==value for key,value in supplied.items()):
        return s
    s['profile'].update(supplied)
    s['prompt'] = next_question(s)
    s['version'] += 1
    s['events'].append({'id':__import__('uuid').uuid4().hex,'sequence':s['version'],'type':'profile.updated'})
    return s


def confirm_reading(s,a):
    phrase = ' '.join(re.sub(r'[^a-z\s]', '', str(a.get('utterance','')).lower()).split())
    if not re.fullmatch(r'(?:yes|yes please|(?:yes |please |yes please )?(?:keep|save) (?:that|it|those words|this source|this reading|this memory|this)(?: in (?:my|the) (?:river|riverbed))?(?: please)?)', phrase):
        raise HTTPException(422, 'An explicit spoken Keep confirmation is required.')
    draft = s.get('draft')
    # The request's version/generation already binds an omitted ID to the visible
    # draft. An explicitly supplied stale ID must still be rejected.
    if not draft or a.get('draft_id',draft['id']) != draft['id']:
        raise HTTPException(409, 'Confirm the current draft.')
    return command(s,'keep_reading',{'draft_id':draft['id'],'text':draft['text'],'confirmed':True})


def apply_conversation(s,name,a):
    if s['status'] != 'active':
        raise HTTPException(409, 'Session is closed.')
    if name == 'record_profile':
        return record_profile(s,a)
    if name == 'skip_profile':
        field=a.get('field',s['step'])
        if field not in FIELDS or s['profile'].get(field):
            raise HTTPException(422,'Skip only a currently unanswered setup field.')
        if field in s.get('skipped',[]):
            return s
        s.setdefault('skipped',[]).append(field)
        s['prompt']=next_question(s)
        s['version']+=1
        return s
    if name == 'request_keep':
        utterance = str(a.get('utterance','')).casefold()
        if s.get('draft'):
            target=a.get('target')
            if target and target != s['draft']['kind']:
                raise HTTPException(409,'The requested kind does not match the displayed draft.')
            return confirm_reading(s,a)
        if re.search(r"\b(don't|dont|do not|not|never)\b",utterance) or not re.search(r'\b(keep|save)\b',utterance):
            raise HTTPException(422,'A request to keep a specific item is required.')
        if a.get('target') != 'source':
            if not str(a.get('text','')).strip():
                raise HTTPException(422,'Supply the exact memory words to prepare a family or own draft.')
            return command(s,'draft_reading',dict(a,kind=a.get('target','family')))
        return command(s,'draft_account',{})
    if name == 'confirm_reading':
        return confirm_reading(s,a)
    return command(s,name,a)


def guide_result(s):
    """Compact, authoritative tool context; no seed history or replayed welcome."""
    unanswered=[field for field in FIELDS if not s['profile'].get(field) and field not in s.get('skipped',[])]
    return dict(version=s['version'],step=s['step'],profile=s['profile'],
                unanswered_fields=unanswered,selected=s['selected'],
                next_question=s['prompt'],account=s.get('account'),draft=s.get('draft'),
                last_commit=s.get('last_commit'),
                instruction='Use the result once. Do not thank, recap setup, repeat answered questions or offer skip reminders. For a draft read its exact words and ask for Keep, then wait. After a commit say it is saved, then wait. A necessary follow-up lookup may use the same supplied question; never repeat the same action.')
