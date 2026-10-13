from fastapi.testclient import TestClient
from sqlalchemy import select
from guard.api import app
from guard.auth import hasher
from guard.db import db, User

BODY={"username":"new-user","password":"strong-test-password-123"}

def test_signup_login_logout_and_hashed_password(client):
    response=client.post('/api/v1/auth/register',json=BODY)
    assert response.status_code==201
    assert response.json()['role']=='user'
    assert 'HttpOnly' in response.headers['set-cookie']
    with db() as s:
        user=s.scalar(select(User).where(User.username==BODY['username']))
        assert user.password_hash!=BODY['password']
        assert hasher.verify(user.password_hash,BODY['password'])
    client.headers['X-CSRF-Token']=response.json()['csrf']
    assert client.get('/api/v1/auth/me').json()['username']==BODY['username']
    assert client.post('/api/v1/auth/logout').status_code==200
    assert client.get('/api/v1/auth/me').status_code==401
    assert client.post('/api/v1/auth/login',json=BODY).status_code==200

def test_signup_validation_duplicate_origin_and_role_injection(client):
    assert client.post('/api/v1/auth/register',json={**BODY,'password':'short'}).status_code==422
    assert client.post('/api/v1/auth/register',json={**BODY,'role':'admin'}).status_code==422
    assert client.post('/api/v1/auth/register',json=BODY,headers={'Origin':'https://untrusted.example'}).status_code==403
    assert client.post('/api/v1/auth/register',json=BODY).status_code==201
    assert client.post('/api/v1/auth/register',json=BODY).status_code==409

def test_new_user_cannot_access_other_records_or_privileged_operations(client):
    job=client.post('/api/v1/tasks',json={'orders':[{'order_id':'ORD-102','expected_delivery':'2026-11-10'}]}).json()
    response=client.post('/api/v1/auth/register',json=BODY)
    client.headers['X-CSRF-Token']=response.json()['csrf']
    assert client.get('/api/v1/tasks').json()==[]
    assert client.get('/api/v1/tasks/'+job['id']).status_code==404
    assert client.get('/api/v1/tasks/'+job['id']+'/export/json').status_code==404
    assert client.post('/api/v1/operations/learn').status_code==403
    assert client.post('/api/v1/requests/prepare',json={'order_id':'ORD-102','message':'hello'}).status_code==403
    assert client.post('/api/v1/requests/no-such-draft/submit',json={'digest':'a'*64}).status_code==403
    assert client.post('/api/v1/system/inference-check').status_code==403
    task={'orders':[{'order_id':'ORD-102','expected_delivery':'2026-11-10'}]}
    assert client.post('/api/v1/tasks',json={**task,'mode':'baseline'}).status_code==403
    own=client.post('/api/v1/tasks',json=task)
    assert own.status_code==200
    assert client.get('/api/v1/tasks/'+own.json()['id']).status_code==200

def test_signup_rate_limit(client):
    for _ in range(8):
        client.post('/api/v1/auth/register',json=BODY)
    assert client.post('/api/v1/auth/register',json=BODY).status_code==429
