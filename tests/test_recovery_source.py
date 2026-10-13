from guard.db import db,Job,User
from sqlalchemy import select
def test_repair_rejects_unowned_or_invalid_source(client):
    assert client.post('/api/v1/operations/get_order_status/repair?source_job_id=missing').status_code==404
    with db() as s:
        owner=s.scalar(select(User));job=Job(owner_id=owner.id,kind="read",state="VERIFIED",payload={});s.add(job);s.commit();key=job.id
    assert client.post('/api/v1/operations/get_order_status/repair?source_job_id='+key).status_code==409
    with db() as s:
        s.get(Job,key).state="PORTAL_CHANGED";s.commit()
    result=client.post('/api/v1/operations/get_order_status/repair?source_job_id='+key)
    assert result.status_code==200
    assert result.json()['payload']['source_job_id']==key
    with db() as s:
        s.add(User(id='another-owner',username='another',password_hash='unused',role='user'));s.commit();s.get(Job,key).owner_id='another-owner';s.commit()
    assert client.post('/api/v1/operations/get_order_status/repair?source_job_id='+key).status_code==404
