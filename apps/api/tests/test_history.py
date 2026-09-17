import datetime as dt
import json
import pytest
import jwt
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from app.config import DEV_SECRET
from app.main import app, request_times
from app.storage import get_engine

@pytest.fixture
def history_client(monkeypatch, tmp_path):
    key = Fernet.generate_key().decode()
    path = tmp_path / 'history.db'
    monkeypatch.setenv('ENABLE_HISTORY', 'true')
    monkeypatch.setenv('HISTORY_ENCRYPTION_KEY', key)
    monkeypatch.setenv('DATABASE_URL', f'sqlite:///{path}')
    request_times.clear()
    with TestClient(app) as client:
        yield client, path
    get_engine.cache_clear()

def auth(subject='github:123', expired=False):
    now = dt.datetime.now(dt.timezone.utc)
    token = jwt.encode({'sub':subject,'iat':now,'exp':now + dt.timedelta(seconds=-60 if expired else 60), 'iss':'resume-web','aud':'resume-api'},DEV_SECRET,algorithm='HS256')
    return {'X-Internal-Key':DEV_SECRET,'Authorization':'Bearer '+token}

def payload(sample):
    return {'title':'Private job search','storage_consent':True, 'workspace':{'resume_text':sample['resume_text'],'job_description':sample['job_description']}}

def test_encrypted_history_owner_isolation(history_client, sample):
    client, path = history_client
    response = client.post('/v1/history',json=payload(sample),headers=auth())
    assert response.status_code == 201
    identifier = response.json()['id']
    assert client.get('/v1/history/'+identifier,headers=auth('github:999')).status_code == 404
    assert len(client.get('/v1/history',headers=auth()).json()['items']) == 1
    assert client.get('/v1/history/'+identifier,headers=auth()).json()['workspace']['resume_text'] == sample['resume_text']
    raw = path.read_bytes()
    assert b'ASHA RAO' not in raw and b'Private job search' not in raw
    assert client.delete('/v1/history/'+identifier,headers=auth('github:999')).status_code == 404
    assert client.delete('/v1/history/'+identifier,headers=auth()).json()['deleted']
    assert client.get('/v1/history/'+identifier,headers=auth()).status_code == 404

def test_storage_consent_required(history_client, sample):
    client, _ = history_client
    body = payload(sample); body['storage_consent'] = False
    assert client.post('/v1/history',json=body,headers=auth()).status_code == 422

@pytest.mark.parametrize('expired,subject',[(True,'github:123'),(False,'attacker')])
def test_bad_session_rejected(history_client, expired, subject):
    client, _ = history_client
    assert client.get('/v1/history',headers=auth(subject, expired)).status_code == 401

def test_delete_all(history_client, sample):
    client, _ = history_client
    client.post('/v1/history',json=payload(sample),headers=auth())
    assert client.delete('/v1/history',headers=auth()).json()['deleted'] == 1
    assert client.get('/v1/history',headers=auth()).json()['items'] == []

def test_expiry_removes_record(history_client, sample):
    from sqlalchemy import update
    from sqlalchemy.orm import Session
    from app.storage import Draft
    from app.config import settings
    client, _ = history_client
    response = client.post('/v1/history',json=payload(sample),headers=auth())
    identifier = response.json()['id']
    with Session(get_engine(settings().database_url)) as db:
        db.execute(update(Draft).where(Draft.id==identifier).values(expires_at=dt.datetime(2000,1,1)))
        db.commit()
    assert client.get('/v1/history/'+identifier,headers=auth()).status_code == 404
    assert client.get('/v1/history',headers=auth()).json()['items'] == []
