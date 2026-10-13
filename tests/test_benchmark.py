from guard.benchmark import summarize
from guard.config import settings

def test_failures_not_hidden_and_learning_amortized():
    rows=[{"mode":"baseline","status":"VERIFIED","duration_ms":100},
          {"mode":"reusable","status":"VERIFIED","duration_ms":10},
          {"mode":"reusable","status":"FAILED","duration_ms":30}]
    result=summarize(rows,200)
    assert result["groups"]["reusable"]=={"attempts":2,"successes":1,"success_rate":.5,"median_ms":10,"p95_ms":10}
    assert result["amortized_reuse_ms_per_attempt"]==120
    assert summarize([],200)["groups"]["baseline"]["median_ms"] is None

def test_missing_provider_does_not_create_fake_benchmark(client,monkeypatch):
    monkeypatch.setattr(settings(),"vultr_inference_api_key","")
    r=client.post('/api/v1/benchmarks',json={"pairs":2,"orders":[{"order_id":"ORD-102","expected_delivery":"2026-11-10"}]})
    assert r.status_code==409
    assert not client.get('/api/v1/tasks').json()

async def test_paired_order_and_payload_restoration(monkeypatch):
    from types import SimpleNamespace
    from guard import benchmark
    monkeypatch.setattr(benchmark,'usage',lambda *args:{"last_event":0})
    class Fake:
        job=SimpleNamespace(id='test',payload={"pairs":2,"orders":[]})
        seen=[]
        async def learn(self): return {"status":"VERIFIED"}
        async def read_orders(self):
            self.seen.append(self.job.payload['mode'])
            return {"status":"VERIFIED"}
        def record(self,*args): pass
        def checkpoint(self): pass
    r=Fake();original=r.job.payload
    result=await benchmark.run_benchmark(r)
    assert r.seen==['baseline','reusable','reusable','baseline']
    assert r.job.payload is original
    assert len(result['trials'])==4
