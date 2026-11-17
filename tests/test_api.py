from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from app.api import create_app


def setup(tmp_path, scenario='diwali'):
    client = TestClient(create_app(str(tmp_path/'test.sqlite3'), 'rehearsal'))
    state = client.post('/api/demo/runs',json={'scenario':scenario,'adult':True,'request_id':'start'}).json()
    return client,state


def send(client,s,name,args=None,key=None):
    return client.post(f"/api/demo/runs/{s['id']}/commands",json={'name':name,'arguments':args or {},'request_id':key or f"{name}-{s['version']}",'version':s['version'],'generation':s['generation']})


def draft(client,s):
    s=send(client,s,'choose_practice',{'practice':'diwali','intent':'Learn'}).json()
    return send(client,s,'draft_reading',{'text':'We light the old lamp together.','kind':'family'}).json()


def test_entry_and_isolation(tmp_path):
    c,s=setup(tmp_path)
    assert s['captures']==s['currents']==[]
    other=TestClient(c.app)
    assert other.get(f"/api/demo/runs/{s['id']}").status_code==401
    other.post('/api/demo/runs',json={'scenario':'avni','adult':True,'request_id':'start'})
    assert other.get(f"/api/demo/runs/{s['id']}").status_code==404
    assert c.post('/api/demo/runs',json={'scenario':'diwali','adult':False,'request_id':'child'}).status_code==403
    assert c.post('/api/demo/runs',json={'scenario':'diwali','adult':True,'request_id':'start'}).json()['id']==s['id']


def test_keep_exact_once_and_persistent(tmp_path):
    c,s=setup(tmp_path)
    s=draft(c,s)
    args={'draft_id':s['draft']['id'],'text':s['draft']['text'],'confirmed':True}
    assert send(c,s,'keep_reading',dict(args,text='Changed')).status_code==409
    with ThreadPoolExecutor(2) as pool:
        responses=list(pool.map(lambda _:send(c,s,'keep_reading',args,'one-keep'),range(2)))
    assert all(r.status_code==200 for r in responses)
    saved=responses[0].json()
    assert len(saved['captures'])==1 and saved['currents'][0]['depth']==1
    assert saved['captures'][0]['citations'][0]['id']=='ucla-diwali'
    new=TestClient(create_app(str(tmp_path/'test.sqlite3'),'rehearsal'))
    new.cookies.update(c.cookies)
    assert new.get(f"/api/demo/runs/{s['id']}").json()==saved
    removed=send(c,saved,'discard',{'capture_id':saved['captures'][0]['id']}).json()
    assert not removed['captures'] and removed['currents'][0]['depth']==1


def test_stop_wins_and_agent_cannot_keep(tmp_path):
    c,s=setup(tmp_path)
    s=draft(c,s)
    body={'name':'keep_reading','arguments':{},'request_id':'agent','version':s['version'],'generation':s['generation']}
    assert c.post(f"/api/demo/runs/{s['id']}/tool-calls",json=body).status_code==403
    stopped=send(c,s,'guard_test').json()
    assert stopped['status']=='route_out'
    assert send(c,s,'keep_reading').status_code==409
    assert c.post(f"/api/demo/runs/{s['id']}/resume").status_code==409


def test_avni_and_onboarding(tmp_path):
    c,s=setup(tmp_path,'avni')
    assert len(s['currents'])==3 and len(s['captures'])==5
    assert s['selected']=='ahoi_ashtami' and s['step']=='explore'
    assert all(capture['seeded'] for capture in s['captures'])
    c2=TestClient(c.app)
    s=c2.post('/api/demo/runs',json={'scenario':'diwali','adult':True,'request_id':'fresh'}).json()
    s=send(c2,s,'submit_turn',{'text':'I celebrate Diwali'}).json()
    assert s['step']=='practice' and s['festival']=='diwali'
    assert 'name' not in s['profile']
    assert not s['currents']


def test_stale_turn_and_cross_origin(tmp_path):
    c,s=setup(tmp_path)
    updated=send(c,s,'interrupt').json()
    assert updated['generation']==1
    assert send(c,s,'submit_turn',{'text':'old response'}).status_code==409
    assert c.post('/api/demo/runs',headers={'Origin':'https://untrusted.example'},json={'scenario':'avni','adult':True,'request_id':'attack'}).status_code==403


def test_missing_live_key_is_explicit(tmp_path,monkeypatch):
    monkeypatch.delenv('ELEVENLABS_API_KEY',raising=False)
    c=TestClient(create_app(str(tmp_path/'live.sqlite3'),'elevenlabs'))
    s=c.post('/api/demo/runs',json={'scenario':'diwali','adult':True,'request_id':'start'}).json()
    assert c.post(f"/api/demo/runs/{s['id']}/realtime-credential").status_code==503


def test_live_credential_config_and_secret_boundary(tmp_path,monkeypatch):
    import httpx
    monkeypatch.setenv('ELEVENLABS_API_KEY','private-workspace-key')
    captured={}
    async def mock_post(self,url,**kwargs):
        captured.update(kwargs)
        assert url=='https://api.elevenlabs.io/v1/convai/realtime/client_secrets'
        return httpx.Response(200,json={'value':'ephemeral-only'},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.AsyncClient,'post',mock_post)
    c=TestClient(create_app(str(tmp_path/'live.sqlite3'),'elevenlabs'))
    s=c.post('/api/demo/runs',json={'scenario':'diwali','adult':True,'request_id':'start'}).json()
    r=c.post(f"/api/demo/runs/{s['id']}/realtime-credential")
    assert r.status_code==200 and r.json()['value']=='ephemeral-only'
    assert 'private-workspace-key' not in r.text
    session=captured['json']['session']
    assert session['audio']['input']['format']['rate']==24000
    assert 'keep_reading' not in session['tools'][0]['parameters']['properties']['name']['enum']
    arguments=session['tools'][0]['parameters']['properties']['arguments']['properties']
    assert arguments['text']['type']=='string'
    assert arguments['kind']['enum']==['family','own']
    assert arguments['draft_id']['type']=='string'
    assert captured['headers']['xi-api-key']=='private-workspace-key'


def test_seed_recipe_current_is_selectable(tmp_path):
    c,s=setup(tmp_path,'avni')
    updated=send(c,s,'choose_practice',{'practice':'recipes','intent':'Practice'})
    assert updated.status_code==200
    assert updated.json()['selected']=='recipes'


def test_conversational_facts_update_immediately_without_capture(tmp_path):
    c,s=setup(tmp_path)
    response=send(c,s,'record_profile',{'profile':{'name':'Maya','location':'Pune'},'utterance':'My name is Maya. I live in Pune.'})
    assert response.status_code==200
    s=response.json()
    assert s['profile']=={'name':'Maya','location':'Pune'}
    assert s['step']=='origins' and s['currents']==[] and s['captures']==[]
    bad=send(c,s,'record_profile',{'profile':{'origins':'Delhi'},'utterance':'My family comes from Lucknow.'})
    assert bad.status_code==422
    correction=send(c,s,'record_profile',{'profile':{'name':'Maia'},'utterance':'Actually, call me Maia.'})
    assert correction.json()['profile']['name']=='Maia'


def test_voice_confirmation_is_bound_to_current_draft(tmp_path):
    c,s=setup(tmp_path)
    s=draft(c,s)
    def tool(utterance,draft_id):
        return c.post(f"/api/demo/runs/{s['id']}/tool-calls",json={'name':'confirm_reading','arguments':{'utterance':utterance,'draft_id':draft_id},'request_id':utterance,'version':s['version'],'generation':s['generation']})
    assert tool('maybe someday',s['draft']['id']).status_code==422
    assert tool('yes','old-draft').status_code==409
    r=tool('Yes, keep that.',s['draft']['id'])
    assert r.status_code==200
    assert len(r.json()['captures'])==1
    assert r.json()['captures'][0]['text']=='We light the old lamp together.'


def test_local_audio_turn_is_atomic_and_idempotent(tmp_path,monkeypatch):
    import base64,io,wave,httpx
    f=io.BytesIO()
    with wave.open(f,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(b'\x00\x00'*2400)
    calls=[]
    async def mock_post(self,url,**kwargs):
        calls.append(kwargs['json'])
        text='My name is Maya. I live in Pune.' if len(calls)==1 else '{"profile":{"name":"Maya","location":"Pune"},"practice":"","intent":"","memory":""}'
        return httpx.Response(200,json={'choices':[{'message':{'content':text}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.AsyncClient,'post',mock_post)
    c=TestClient(create_app(str(tmp_path/'audio.sqlite3'),'lfm3'))
    s=c.post('/api/demo/runs',json={'scenario':'diwali','adult':True,'request_id':'start'}).json()
    body={'name':'voice_turn','arguments':{'audio':base64.b64encode(f.getvalue()).decode()},'request_id':'turn-1','version':s['version'],'generation':s['generation']}
    r=c.post(f"/api/demo/runs/{s['id']}/voice-turn",json=body)
    assert r.status_code==200
    assert r.json()['state']['profile']=={'name':'Maya','location':'Pune'}
    assert r.json()['state']['step']=='origins'
    assert c.post(f"/api/demo/runs/{s['id']}/voice-turn",json=body).json()==r.json()
    assert len(calls)==2
    stopped=send(c,r.json()['state'],'interrupt').json()
    body.update(request_id='turn-2')
    assert c.post(f"/api/demo/runs/{s['id']}/voice-turn",json=body).status_code==409
    assert stopped['generation']==1


def test_local_model_cannot_invent_practice_or_intent(tmp_path,monkeypatch):
    import base64,io,wave,httpx
    f=io.BytesIO()
    with wave.open(f,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(24000);wav.writeframes(b'\x00\x00'*2400)
    calls=[]
    async def mock_post(self,url,**kwargs):
        calls.append(kwargs)
        text='My name is Maya. I live in Pune.' if len(calls)==1 else '{"profile":{"name":"Maya","location":"Pune"},"practice":"diwali","intent":"Learn","memory":"My name is Maya."}'
        return httpx.Response(200,json={'choices':[{'message':{'content':text}}]},request=httpx.Request('POST',url))
    monkeypatch.setattr(httpx.AsyncClient,'post',mock_post)
    c=TestClient(create_app(str(tmp_path/'bounded.sqlite3'),'lfm3'))
    s=c.post('/api/demo/runs',json={'scenario':'diwali','adult':True,'request_id':'start'}).json()
    body={'name':'voice_turn','arguments':{'audio':base64.b64encode(f.getvalue()).decode()},'request_id':'turn-1','version':s['version'],'generation':s['generation']}
    r=c.post(f"/api/demo/runs/{s['id']}/voice-turn",json=body)
    assert r.status_code==200
    saved=r.json()['state']
    assert saved['step']=='origins' and saved['selected'] is None
    assert saved['currents']==[] and saved['draft'] is None


def test_corpus_selection_and_scoped_sources(tmp_path):
    c,s=setup(tmp_path)
    for query,expected in [('Lakshmi puja','lakshmi'),('Kali Puja','kali'),('Lakshmi versus Kali','comparison'),('Shaktism vs bhaktism','shakti-bhakti'),('What makes an offering meaningful?','offering')]:
        account=c.get('/api/corpus',params={'query':query}).json()
        assert account['id']==f'diwali.{expected}.v1'
        assert account['kind']=='cited' and account['citations']
        assert all(source['url'].startswith('https://') and source['locator'] for source in account['citations'])
    assert c.get('/api/corpus',params={'practice':'ahoi_ashtami'}).json()['kind']=='unknown'
    s=send(c,s,'choose_practice',{'practice':'diwali','intent':'Learn'}).json()
    assert send(c,s,'get_corpus_account',{'account_id':'invented'}).status_code==422


def test_spoken_source_keep_preview_and_immutable_snapshot(tmp_path):
    c,s=setup(tmp_path)
    s=send(c,s,'choose_practice',{'practice':'diwali','intent':'Learn'}).json()
    s=send(c,s,'get_corpus_account',{'query':'Lakshmi versus Kali'}).json()
    account=s['account']
    s=send(c,s,'request_keep',{'target':'source','utterance':'I want to keep this reading.'}).json()
    assert s['draft']['kind']=='source' and not s['captures']
    assert s['draft']['text']==account['text']
    draft_id=s['draft']['id']
    # Changing the displayed account cannot change a previously proposed draft.
    s=send(c,s,'get_corpus_account',{'query':'bhakti'}).json()
    assert s['draft']['citations']==account['citations']
    kept=send(c,s,'confirm_reading',{'draft_id':draft_id,'utterance':'keep this source'},key='spoken-source-keep').json()
    assert len(kept['captures'])==1
    capture=kept['captures'][0]
    assert capture['account_id']==account['id'] and capture['text']==account['text']
    assert capture['citations']==account['citations']
    assert kept['last_commit']['capture_id']==capture['id']
    assert capture['kind']=='source'
    assert send(c,kept,'confirm_reading',{'draft_id':draft_id,'utterance':'yes'}).status_code==409


def test_source_draft_cannot_be_saved_by_ambiguous_first_request(tmp_path):
    c,s=setup(tmp_path)
    s=send(c,s,'choose_practice',{'practice':'diwali','intent':'Learn'}).json()
    assert send(c,s,'request_keep',{'target':'source','utterance':'interesting'}).status_code==422
    s=send(c,s,'request_keep',{'target':'source','utterance':'keep that'}).json()
    assert not s['captures'] and s['draft']
    assert send(c,s,'confirm_reading',{'draft_id':s['draft']['id'],'utterance':'maybe keep it later'}).status_code==422
    s=send(c,s,'decline').json()
    assert not s['draft'] and not s['captures'] and s['currents'][0]['depth']==0


def test_fresh_runs_do_not_restore_and_boot_id_changes(tmp_path):
    c,s=setup(tmp_path,'avni')
    boot=c.get('/api/config').json()['server_instance']
    new=c.post('/api/demo/runs',json={'scenario':'diwali','adult':True,'request_id':'fresh-new-run'}).json()
    assert new['id']!=s['id'] and new['profile']=={} and not new['captures']
    assert len(c.get(f"/api/demo/runs/{s['id']}").json()['captures'])==5
    restarted=TestClient(create_app(str(tmp_path/'test.sqlite3'),'rehearsal'))
    assert restarted.get('/api/config').json()['server_instance']!=boot


def test_local_name_cannot_be_filled_with_a_residence(tmp_path):
    c,s=setup(tmp_path)
    r=send(c,s,'record_profile',{'profile':{'name':'New Delhi','location':'New Delhi'},'utterance':'I live in New Delhi.'})
    assert r.status_code==422
    assert c.get(f"/api/demo/runs/{s['id']}").json()['profile']=={}


def test_negative_source_request_and_accidental_draft_replacement_are_rejected(tmp_path):
    c,s=setup(tmp_path)
    s=send(c,s,'choose_practice',{'practice':'diwali','intent':'Learn'}).json()
    assert send(c,s,'request_keep',{'target':'source','utterance':"I don't want to keep that"}).status_code==422
    s=send(c,s,'draft_reading',{'text':'The lamp reminds me of home.'}).json()
    assert send(c,s,'draft_reading',{'text':'A different reading without asking.'}).status_code==409
    updated=send(c,s,'draft_reading',{'text':'Our old lamp reminds me of home.','replace_draft_id':s['draft']['id']}).json()
    assert updated['draft']['text']=='Our old lamp reminds me of home.'


def test_profile_duplicates_and_skip_do_not_repeat_setup(tmp_path):
    from app.conversation import apply_conversation, guide_result
    _,s=setup(tmp_path)
    s=apply_conversation(s,'record_profile',{'profile':{'name':'Maya'},'utterance':'My name is Maya'})
    version=s['version']
    s=apply_conversation(s,'record_profile',{'profile':{'name':'Maya'},'utterance':'My name is Maya'})
    assert s['version']==version
    s=apply_conversation(s,'skip_profile',{'field':'location'})
    assert s['step']=='origins'
    context=guide_result(s)
    assert 'name' not in context['unanswered_fields']
    assert 'location' not in context['unanswered_fields']
    assert 'skip' not in context['next_question'].lower()


def tool(c,s,name,args,key):
    response=c.post(f"/api/demo/runs/{s['id']}/tool-calls",json={'name':name,'arguments':args,'request_id':key,'version':s['version'],'generation':s['generation']})
    assert response.status_code==200,response.text
    return response.json()


def test_fresh_memory_keep_before_practice_selection(tmp_path):
    c,s=setup(tmp_path)
    s=tool(c,s,'record_profile',{'profile':{'name':'Maya'},'utterance':'My name is Maya'},'name')
    assert s['profile']['name']=='Maya' and not s['captures']
    s=tool(c,s,'draft_reading',{'text':'We repaired the old light together.','kind':'family'},'draft')
    assert s['selected']=='family' and not s['captures']
    assert s['guide_result']['draft']['id']==s['draft']['id']
    version=s['version']
    # request_keep is also a valid confirmation when a matching draft is pending.
    s=tool(c,s,'request_keep',{'target':'family','utterance':'keep that please'},'keep')
    assert len(s['captures'])==1 and s['draft'] is None
    assert s['captures'][0]['text']=='We repaired the old light together.'
    assert s['last_commit']['capture_id']==s['captures'][0]['id']
    persisted=c.get(f"/api/demo/runs/{s['id']}").json()
    assert persisted['captures']==s['captures']
    repeated=c.post(f"/api/demo/runs/{s['id']}/tool-calls",json={'name':'request_keep','arguments':{'target':'family','utterance':'keep that please'},'request_id':'keep','version':version,'generation':s['generation']})
    assert repeated.status_code==200 and len(repeated.json()['captures'])==1
    s=tool(c,s,'get_corpus_account',{'query':'What does Lakshmi Puja mean?'},'later-source')
    assert s['selected']=='diwali' and s['account']['kind']=='cited'
    assert len(s['captures'])==1 and s['captures'][0]['current']=='family'


def test_fresh_source_lookup_and_keep_without_onboarding(tmp_path):
    c,s=setup(tmp_path)
    s=tool(c,s,'get_corpus_account',{'query':'Lakshmi Puja'},'lookup')
    assert s['selected']=='diwali' and s['account']['kind']=='cited'
    s=tool(c,s,'request_keep',{'target':'source','utterance':'keep this reading'},'prepare')
    draft_id=s['draft']['id']
    for phrase in ['maybe keep that','do not keep that','yes but not yet']:
        r=c.post(f"/api/demo/runs/{s['id']}/tool-calls",json={'name':'confirm_reading','arguments':{'utterance':phrase},'request_id':phrase,'version':s['version'],'generation':s['generation']})
        assert r.status_code==422
    s=tool(c,s,'confirm_reading',{'draft_id':draft_id,'utterance':'keep this source please'},'confirm')
    assert len(s['captures'])==1 and s['captures'][0]['citations']
    assert s['captures'][0]['kind']=='source'


def test_request_keep_yes_confirms_only_an_existing_draft(tmp_path):
    c,s=setup(tmp_path)
    s=tool(c,s,'draft_reading',{'text':'We make sweets together.','kind':'family'},'draft')
    s=tool(c,s,'request_keep',{'target':'family','utterance':'yes'},'yes')
    assert len(s['captures'])==1
    r=c.post(f"/api/demo/runs/{s['id']}/tool-calls",json={'name':'request_keep','arguments':{'target':'family','utterance':'yes'},'request_id':'another-yes','version':s['version'],'generation':s['generation']})
    assert r.status_code==422
