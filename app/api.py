import json
import os
import secrets
from pathlib import Path
from uuid import uuid4

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field

from app.domain import baseline, command
from app.conversation import apply_conversation, next_question, FIELDS, guide_result
from app.store import Store
from app.corpus import DATA, account_for
from app.voices import selected_voice

load_dotenv()
ROOT = Path(__file__).resolve().parent.parent


class RunInput(BaseModel):
    scenario: str
    adult: bool
    request_id: str = Field(min_length=1, max_length=100)


class CommandInput(BaseModel):
    name: str
    arguments: dict = Field(default_factory=dict)
    request_id: str = Field(min_length=1, max_length=100)
    version: int
    generation: int


def create_app(db_path=None, provider=None):
    app = FastAPI(title='Sngm local demo')
    server_instance = uuid4().hex
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=['localhost','127.0.0.1','testserver'])
    store = Store(db_path or os.getenv('SNGM_DB', str(ROOT / 'data/sngm.sqlite3')))
    provider = provider or os.getenv('SNGM_PROVIDER','elevenlabs')
    if provider not in ['elevenlabs','lfm3','rehearsal']:
        raise ValueError('SNGM_PROVIDER must be elevenlabs, lfm3 or rehearsal')

    @app.middleware('http')
    async def browser_boundary(request: Request, call_next):
        origin = request.headers.get('origin')
        if origin and origin != f'{request.url.scheme}://{request.headers.get("host")}' and origin not in ['http://localhost:5173','http://127.0.0.1:5173']:
            return Response('Cross-origin access denied', status_code=403)
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    def owner(request):
        value = request.cookies.get('sngm_owner')
        if not value:
            raise HTTPException(401, 'Start a demo run first.')
        return value

    def load(db, run, request):
        state = store.load(db, run, owner(request))
        if not state:
            raise HTTPException(404, 'Run not found.')
        return state

    @app.get('/api/config')
    def config():
        return dict(provider=provider, voice=selected_voice(), server_instance=server_instance, voice_label='Viraj · Indian English' if selected_voice()=='fPIfC3elMLbN9tNwMXkw' else 'Configured Reading voice',
            voice_ready=bool(os.getenv('ELEVENLABS_API_KEY')) if provider == 'elevenlabs' else provider == 'lfm3',
            content_ready=True, corpus_version=DATA['version'], guard='Prepared demo stop only; no evaluated independent audio Guard.')

    @app.get('/api/corpus')
    def corpus(practice: str = 'diwali', query: str = ''):
        return account_for(practice, query[:1000])

    @app.get('/api/demo/scenarios')
    def scenarios():
        return [dict(id='diwali', label='Start my river', version=1), dict(id='avni', label='Open Avni’s river', version=1)]

    @app.post('/api/demo/runs')
    def new_run(body: RunInput, request: Request, response: Response):
        if not body.adult:
            raise HTTPException(403, 'This demo is for adults aged 18 and over.')
        if body.scenario not in ['diwali','avni']:
            raise HTTPException(422, 'Unknown scenario.')
        who = request.cookies.get('sngm_owner') or secrets.token_urlsafe(32)
        response.set_cookie('sngm_owner', who, httponly=True, samesite='strict', max_age=86400*30)
        with store.connect() as db:
            previous = db.execute('SELECT result FROM requests WHERE run=? AND key=?', (who,body.request_id)).fetchone()
            if previous:
                return json.loads(previous[0])
            state = baseline(body.scenario)
            db.execute('INSERT INTO runs VALUES(?,?,?)',(state['id'],who,json.dumps(state)))
            db.execute('INSERT INTO requests VALUES(?,?,?)',(who,body.request_id,json.dumps(state)))
            return state

    @app.get('/api/demo/runs')
    def runs(request: Request):
        with store.connect() as db:
            rows = db.execute('SELECT state FROM runs WHERE owner=?',(owner(request),)).fetchall()
            return [dict(id=s['id'],scenario=s['scenario'],captures=len(s['captures']),status=s['status']) for s in map(lambda r:json.loads(r[0]),rows)]

    @app.get('/api/demo/runs/{run}')
    def get_run(run: str, request: Request):
        with store.connect() as db:
            return load(db,run,request)

    @app.post('/api/demo/runs/{run}/resume')
    def resume(run: str, request: Request):
        with store.connect() as db:
            state = load(db,run,request)
            if state['status'] == 'route_out':
                raise HTTPException(409, 'Start a fresh run after the prepared stop.')
            state.update(status='active', generation=state['generation']+1, version=state['version']+1)
            store.save(db,state)
            return state

    @app.post('/api/demo/runs/{run}/commands')
    def execute(run: str, body: CommandInput, request: Request):
        with store.connect() as db:
            state = load(db,run,request)
            previous = db.execute('SELECT result FROM requests WHERE run=? AND key=?',(run,body.request_id)).fetchone()
            if previous:
                return json.loads(previous[0])
            if body.version != state['version'] or body.generation != state['generation']:
                raise HTTPException(409, 'State changed. Reload before retrying.')
            result = apply_conversation(state,body.name,body.arguments)
            store.save(db,result)
            db.execute('INSERT INTO requests VALUES(?,?,?)',(run,body.request_id,json.dumps(result)))
            return result

    @app.post('/api/demo/runs/{run}/voice-turn')
    async def voice_turn(run: str, body: CommandInput, request: Request):
        if provider != 'lfm3':
            raise HTTPException(409, 'Local voice is not enabled.')
        with store.connect() as db:
            state = load(db,run,request)
            previous = db.execute('SELECT result FROM requests WHERE run=? AND key=?',(run,body.request_id)).fetchone()
            if previous:
                return json.loads(previous[0])
        if state['status'] != 'active' or body.generation != state['generation'] or body.version != state['version']:
            raise HTTPException(409, 'This voice turn has expired.')
        audio = body.arguments.get('audio','')
        if not isinstance(audio,str) or not 40 < len(audio) < 2_000_000:
            raise HTTPException(422, 'Supply a short WAV audio turn.')
        import base64
        try:
            decoded = base64.b64decode(audio,validate=True)
            if decoded[:4] != b'RIFF' or decoded[8:12] != b'WAVE':
                raise ValueError()
        except ValueError:
            raise HTTPException(422, 'Invalid WAV audio.')
        headers = {'Authorization':'Bearer '+os.environ['LFM3_API_KEY']} if os.getenv('LFM3_API_KEY') else {}
        url = os.getenv('LFM3_BASE_URL','http://127.0.0.1:9931').rstrip('/')+'/v1/chat/completions'
        schema = {'type':'object','properties':{
            'profile':{'type':'object','properties':{key:{'type':'string'} for key in FIELDS},'additionalProperties':False},
            'practice':{'type':'string','enum':['','diwali','ahoi_ashtami']},
            'intent':{'type':'string','enum':['','Learn','Practice']},
            'memory':{'type':'string'}},'required':['profile','practice','intent','memory'],'additionalProperties':False}
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                result = await client.post(url,headers=headers,json={'model':os.getenv('LFM3_MODEL','lfm3-omni'),
                    'messages':[{'role':'system','content':'Transcribe only the words spoken in this audio. Do not answer, introduce yourself, or add explanations. If silence, return an empty string.'},
                    {'role':'user','content':[{'type':'input_audio','input_audio':{'data':audio,'format':'wav'}}]}], 'max_tokens':400})
                result.raise_for_status()
                transcript = result.json()['choices'][0]['message']['content'].strip()
                if not transcript:
                    return {'state':state,'reply':'I didn’t catch that. Would you say it again?'}
                result = await client.post(url,headers=headers,json={'model':os.getenv('LFM3_MODEL','lfm3-omni'),
                    'messages':[{'role':'system','content':
                    'Extract facts from the user utterance as JSON. Profile keys: name, location (current home), origins (family roots), festivals. '
                    'Every profile value MUST be an exact substring of the utterance. Omit unsupplied fields. No inference. '
                    'Return practice only if user explicitly selects Diwali lighting or Ahoi fast. Return intent only if they choose learning/understanding or practising. '
                    'Return memory as an exact substring ONLY if they supply a family memory or personal meaning while at explore step, otherwise empty. '
                    'Do not treat questions as memories. Current step: '+state['step']},
                    {'role':'user','content':transcript}], 'response_format':{'type':'json_schema','json_schema':{'name':'facts','schema':schema}},'max_tokens':400})
                result.raise_for_status()
                facts = json.loads(result.json()['choices'][0]['message']['content'])
                if not isinstance(facts,dict) or not isinstance(facts.get('profile'),dict):
                    raise ValueError('Malformed facts')
        except (httpx.HTTPError, KeyError, IndexError, ValueError):
            raise HTTPException(502, 'I couldn’t hear you through the local guide. Check LFM3 audio support and try again.')
        with store.connect() as db:
            latest = load(db,run,request)
            if latest['status'] != 'active' or latest['generation'] != state['generation'] or latest['version'] != state['version']:
                raise HTTPException(409, 'Voice turn cancelled.')
            state = latest
            was_exploring = state['step'] == 'explore'
            if state.get('draft'):
                import re
                normalized = re.sub(r'[^a-z\s]','',transcript.lower()).strip()
                if normalized in ['no','no thanks','dont keep that','leave it']:
                    state = command(state,'decline',{})
                else:
                    try:
                        state = apply_conversation(state,'confirm_reading',{'utterance':transcript,'draft_id':state['draft']['id']})
                    except HTTPException:
                        state['prompt'] = next_question(state)
            else:
                import re
                spoken = transcript.casefold()
                topic = any(word in spoken for word in ['diwali','lakshmi','laxmi','kali','shakt','bhakt','sri sukta'])
                question = any(word in spoken for word in ['why','what','how','tell me','explain','difference','compare','understand','learn','read','about'])
                short_keep = bool(re.fullmatch(r'(?:please )?(?:keep|save) (?:that|it|this|this reading|this source)[.!]?',spoken.strip()))
                explicit_source = bool(re.search(r'\b(keep|save)\b',spoken)) and any(word in spoken for word in ['source','citation','reading']) and not facts.get('memory')
                wants_source = (short_keep or explicit_source) and not re.search(r"\b(dont|don't|do not|not|never)\b",spoken) and bool(state.get('account')) and state['account']['kind']=='cited'
                if wants_source:
                    state = apply_conversation(state,'request_keep',{'target':'source','utterance':transcript})
                    store.save(db,state)
                    payload = {'state':state,'reply':state['prompt']}
                    db.execute('INSERT INTO requests VALUES(?,?,?)',(run,body.request_id,json.dumps(payload)))
                    return payload
                if topic and question:
                    if state.get('selected') != 'diwali':
                        state = command(state,'choose_practice',{'practice':'diwali','intent':'Learn'})
                    state = command(state,'get_corpus_account',{'query':transcript})
                    store.save(db,state)
                    payload = {'state':state,'reply':state['prompt']}
                    db.execute('INSERT INTO requests VALUES(?,?,?)',(run,body.request_id,json.dumps(payload)))
                    return payload
                profile = {key:value for key,value in facts.get('profile',{}).items()
                           if key in FIELDS and isinstance(value,str) and value.strip() and value.casefold() in transcript.casefold()}
                if 'name' in profile and re.search(r'\b(live|based|come from)\b',transcript,re.I) and not re.search(r'\b(name|call me)\b',transcript,re.I):
                    profile.pop('name')
                if profile:
                    state = apply_conversation(state,'record_profile',{'profile':profile,'utterance':transcript})
                if transcript.lower().strip(' .!') in ['skip','skip that','rather not say'] and state['step'] in FIELDS:
                    state.setdefault('skipped',[]).append(state['step'])
                    state['prompt'] = next_question(state)
                import re
                spoken = transcript.casefold()
                practice = facts.get('practice') or ''
                named = ('diwali' in spoken) if practice == 'diwali' else any(alias in spoken for alias in ['ahoi','hoi ashtami','hoi asthami'])
                contextual = practice == state.get('festival') or practice in state['profile'].get('festivals','').casefold()
                related = any(word in spoken for word in (['light','diya','lamp'] if practice == 'diwali' else ['fast','children']))
                if not (named or (contextual and related)):
                    practice = ''
                intent = facts.get('intent')
                if intent == 'Learn' and not re.search(r'\b(learn|understand|why|meaning|know)\b', spoken):
                    intent = ''
                if intent == 'Practice' and not re.search(r'\b(practice|practise|try|do it|carry)\b', spoken):
                    intent = ''
                if practice and intent:
                    state = command(state,'choose_practice',{'practice':practice,'intent':intent})
                memory = facts.get('memory','')
                if was_exploring and state.get('selected') and memory and memory.casefold() in transcript.casefold() and not transcript.rstrip().endswith('?'):
                    state = command(state,'draft_reading',{'text':memory,'kind':'family'})
                    state['prompt'] = next_question(state)
                elif not profile and not practice:
                    state['prompt'] = next_question(state)
            state['version'] += 1
            store.save(db,state)
            payload = {'state':state,'reply':state['prompt']}
            db.execute('INSERT INTO requests VALUES(?,?,?)',(run,body.request_id,json.dumps(payload)))
            return payload

    @app.post('/api/demo/runs/{run}/local-guide')
    async def local_guide(run: str, body: CommandInput, request: Request):
        if provider != 'lfm3':
            raise HTTPException(409, 'Local guide is not enabled.')
        with store.connect() as db:
            state = load(db,run,request)
        if state['status'] != 'active':
            raise HTTPException(409, 'Session is closed.')
        text = str(body.arguments.get('text','')).strip()[:4000]
        if not text:
            raise HTTPException(422, 'Supply a question for the local guide.')
        prompt = ('You are Sngm, a concise family-tradition guide. Ask one question at a time. '
                  'Do not invent sources, scripture or family facts. No reviewed passages are available. '
                  'Never claim to save anything. The human interface handles drafts and confirmation. '
                  'Help the user reflect on supplied family practice. Authorized app context: ' + json.dumps(state))
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                headers = {}
                if os.getenv('LFM3_API_KEY'):
                    headers['Authorization'] = 'Bearer ' + os.environ['LFM3_API_KEY']
                result = await client.post(os.getenv('LFM3_BASE_URL','http://127.0.0.1:9931').rstrip('/')+'/v1/chat/completions',
                    headers=headers, json={'model':os.getenv('LFM3_MODEL','lfm3-omni'),
                    'messages':[{'role':'system','content':prompt},{'role':'user','content':text}], 'max_tokens':250})
                result.raise_for_status()
                reply = result.json()['choices'][0]['message']['content']
        except (httpx.HTTPError, KeyError, IndexError):
            raise HTTPException(502, 'Local LFM3 request failed. Check the server on port 9931; no fallback was substituted.')
        # A response begun before a close or interrupt cannot affect the current session.
        with store.connect() as db:
            latest = load(db,run,request)
            if latest['generation'] != state['generation'] or latest['status'] != 'active':
                raise HTTPException(409, 'Local response cancelled.')
        return {'reply':reply, 'disclosure':'Local LFM3 turn-based text; no realtime audio transport.'}

    @app.post('/api/demo/runs/{run}/realtime-credential')
    async def credential(run: str, request: Request):
        with store.connect() as db:
            state = load(db,run,request)
        if state['status'] != 'active':
            raise HTTPException(409,'Session is closed.')
        instructions = ('You are Sngm, a thoughtful conversational guide. Speak plainly and briefly, one question per turn, then WAIT. '
            'Never start responses with thanks, thank you, wonderful, lovely or repeated acknowledgement. Go directly to the next relevant thought. '
            'Never repeat a setup question whose field is already supplied or skipped. Never repeat that the person can skip questions. '
            'Silence is a valid wait, not permission to restart onboarding. A tool result is not a new user turn. '
            'Do not call the same tool twice with the same facts. If a tool fails, ask one clarification and wait rather than retrying in a loop. '
            'Never invent religious sources, personal facts or memories. A compact sourced Diwali corpus is available through get_corpus_account. '
            'Call get_corpus_account with query BEFORE explaining Diwali, Lakshmi, Kali, Shaktism or bhakti so the actual citations appear on screen before you speak. '
            'Use only the returned account and its limits for religious explanations. A direct question about a supported practice indicates Learn intent. '
            'Shaktism and bhakti overlap; never present them as opposing religions. Corpus texts do not establish the user’s family beliefs. '
            'Speak natural Indian English, warm and measured, with Indian pronunciation of names and Sanskrit terms. Do not perform a caricatured accent. '
            'Use apply_action to record each supplied setup answer or draft. Never claim a draft is saved. '
            'The Riverbed shows exact saved readings, and a separate pending draft panel names what a spoken Keep will save. '
            'Call record_profile ONLY when a user supplies new setup facts or an explicit correction. Do not call it for questions, confirmations, silence or already-stored details. '
            'Call record_profile immediately as name, location, origins or festivals arrive; each value must be a substring of utterance. '
            'record_profile arguments look like {profile:{name: Maya}, utterance: My name is Maya}; use actual JSON strings. '
            'Ask only the next unanswered setup field in order: name, location, origins, festivals. If asked to skip use skip_profile with that field; do not announce the skip option. '
            'When they choose a supported practice, call choose_practice with practice diwali or ahoi_ashtami and their chosen Learn or Practice intent. '
            'A person may share a memory before setup is complete. Call draft_reading with text containing their exact memory words and kind family or own; no prior practice selection is required. Read back the draft and ask whether to keep it. '
            'If the user wants to keep a SOURCE reading, call request_keep with target source and their verbatim utterance. This prepares a source draft with citation snapshot. '
            'Explain whether the draft is a source summary, family memory or own interpretation. Read the displayed wording back. '
            'Do not change or replace an existing draft without the user requesting an edit or declining it. '
            'When a draft is pending and they say yes or keep that, call confirm_reading with its draft_id and verbatim utterance. Do not draft it again or call request_keep for a different kind. Never infer consent. '
            'At connection, ask the next unanswered question once, or continue the active reading. Welcome only a genuinely fresh person, once. Do not restart or reintroduce yourself when tools return. '
            'Do not provide medical, financial or spiritual authority. Current authorized state: '+json.dumps(state))
        tool = dict(type='function',name='apply_action',description='Record supplied profile facts with verbatim utterance, advance onboarding, choose a practice, draft a reading or confirm an explicit spoken Keep.',
            parameters=dict(type='object',properties={'name':{'type':'string','enum':['record_profile','submit_turn','choose_practice','get_corpus_account','get_reopening','draft_reading','request_keep','confirm_reading','decline','skip_profile']},'arguments':{'type':'object','description':'Arguments for the named action. Use exact user words for utterance and memory text.', 'properties':{
                'profile':{'type':'object','properties':{field:{'type':'string'} for field in FIELDS},'additionalProperties':False},
                'utterance':{'type':'string','description':'Verbatim user speech; required for record_profile, request_keep and confirm_reading.'},
                'text':{'type':'string','description':'Exact user memory words for draft_reading; never a generated paraphrase.'},
                'kind':{'type':'string','enum':['family','own'],'description':'Memory draft kind.'},
                'target':{'type':'string','enum':['source','family','own'],'description':'What request_keep targets.'},
                'draft_id':{'type':'string','description':'ID of the displayed pending draft; use for confirm_reading.'},
                'replace_draft_id':{'type':'string','description':'Only when the user explicitly edits the pending draft.'},
                'practice':{'type':'string','enum':['diwali','ahoi_ashtami','recipes']},
                'intent':{'type':'string','enum':['Learn','Practice']},
                'query':{'type':'string','description':'The user religious question for get_corpus_account.'},
                'field':{'type':'string','enum':list(FIELDS)}
            }}},required=['name','arguments']))
        session = dict(type='realtime', model=os.getenv('ELEVENLABS_MODEL','eleven_realtime_v1_mini'), instructions=instructions,
            output_modalities=['audio'], tools=[tool], audio={'input':{'format':{'type':'audio/pcm','rate':24000},'turn_detection':{'type':'semantic_vad','eagerness':'medium'}},'output':{'format':{'type':'audio/pcm'},'voice':selected_voice()}})
        if provider != 'elevenlabs':
            raise HTTPException(409,'Rehearsal mode uses typed input only.')
        key = os.getenv('ELEVENLABS_API_KEY')
        if not key:
            raise HTTPException(503,'The guide is not configured yet. Set ELEVENLABS_API_KEY in the backend .env and restart.')
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                result = await client.post('https://api.elevenlabs.io/v1/convai/realtime/client_secrets',headers={'xi-api-key':key},json={'session':session,'expires_after':{'anchor':'created_at','seconds':600}})
                result.raise_for_status()
                value = result.json()['value']
        except (httpx.HTTPError, KeyError):
            raise HTTPException(502,'ElevenLabs could not issue a realtime credential. Check workspace access, voice and model settings.')
        return dict(provider=provider,value=value,url='wss://api.elevenlabs.io/v1/convai/realtime',session=session)

    @app.post('/api/demo/runs/{run}/tool-calls')
    def tool_calls(run: str, body: CommandInput, request: Request):
        if body.name not in ['record_profile','submit_turn','choose_practice','get_corpus_account','get_reopening','draft_reading','request_keep','confirm_reading','decline','skip_profile']:
            raise HTTPException(403,'Use confirm_reading with explicit spoken consent and the current draft ID.')
        result=execute(run,body,request)
        return {**result,'guide_result':guide_result(result)}

    dist = ROOT / 'frontend/dist'
    if dist.exists():
        app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
        @app.get('/{path:path}')
        def frontend(path: str):
            if path.startswith('api/'):
                raise HTTPException(404)
            return FileResponse(dist/'index.html')
    return app
