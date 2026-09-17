from app.parser import source_hash

def test_health(client):
    assert client.get('/health').json()['status'] == 'ok'

def test_internal_boundary(client, sample):
    assert client.post('/v1/analyze', json=sample).status_code == 401

def test_config(client, headers):
    data = client.get('/v1/config', headers=headers).json()
    assert data['skill_count'] >= 70 and not data['llm_enabled']

def test_api_analysis(client, headers, sample):
    response = client.post('/v1/analyze', json=sample, headers=headers)
    assert response.status_code == 200 and response.json()['score'] == 62.5
    assert response.headers['cache-control'] == 'no-store'

def test_error_does_not_echo_input(client, headers, sample):
    response = client.post('/v1/analyze', json={**sample, 'extra': 'private-secret'}, headers=headers)
    assert response.status_code == 422
    assert 'private-secret' not in response.text

def test_rewrite_and_guard(client, headers, sample):
    request = {**sample, 'source_hash': source_hash(sample['resume_text'])}
    rewritten = client.post('/v1/rewrite', json=request, headers=headers).json()
    assert len(rewritten['items']) == 4
    block = rewritten['items'][0]['block_id']
    checked = client.post('/v1/guard', json={**request, 'block_id':block, 'candidate':'Led campaigns worth 2 crore.'}, headers=headers)
    assert checked.json()['status'] == 'rejected'

def test_stale_source_409(client, headers, sample):
    response = client.post('/v1/rewrite', json={**sample,'source_hash':'0'*64}, headers=headers)
    assert response.status_code == 409

def test_model_requires_consent(client, headers, sample):
    response = client.post('/v1/rewrite', json={**sample,'source_hash':source_hash(sample['resume_text']), 'use_llm':True}, headers=headers)
    assert response.status_code == 422

def test_anonymous_history_unavailable(client, headers):
    assert client.get('/v1/history', headers=headers).status_code == 403

def test_export_and_import_roundtrip(client, headers, sample):
    response = client.post('/v1/export/pdf', json={**sample,'source_hash':source_hash(sample['resume_text'])}, headers=headers)
    assert response.status_code == 200 and response.headers['x-text-verified'] == 'true'
    upload_headers = {**headers, 'X-Adult-Confirmed':'true', 'X-Processing-Consent':'true'}
    imported = client.post('/v1/import/pdf', files={'file':('resume.pdf',response.content,'application/pdf')}, headers=upload_headers)
    assert imported.status_code == 200
    assert 'ASHA RAO' in imported.json()['text']

def test_upload_needs_consent(client, headers):
    response = client.post('/v1/import/pdf', files={'file':('resume.pdf',b'%PDF-notreally','application/pdf')}, headers=headers)
    assert response.status_code == 422

def test_large_body_blocked(client, headers):
    response = client.post('/v1/analyze', content=b'x'*(2*1024*1024+1), headers=headers)
    assert response.status_code == 413

def test_github_disabled(client, headers):
    response = client.post('/v1/evidence/github',json={'url':'https://github.com/a/b','adult_confirmed':True,'network_consent':True},headers=headers)
    assert response.status_code == 403
