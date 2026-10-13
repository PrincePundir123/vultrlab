from guard.db import db, JobEvent
def test_export_includes_partial_measurements(client):
    job=client.post('/api/v1/tasks',json={"orders":[{"order_id":"ORD-102","expected_delivery":"2026-11-10"}]}).json()
    with db() as s:
        s.add(JobEvent(job_id=job['id'],kind='BENCHMARK_TRIAL',data={'duration_ms':42}));s.commit()
    evidence=client.get('/api/v1/tasks/'+job['id']+'/export/json').json()
    assert evidence['events'][0]['data']['duration_ms']==42
