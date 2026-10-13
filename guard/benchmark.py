"""Serial paired measurements; no generated or projected performance results."""
import math
import statistics
import time
from sqlalchemy import select
from guard.db import db, JobEvent

def summarize(trials, learning_ms):
    groups = {}
    for mode in ("baseline", "reusable"):
        runs = [r for r in trials if r["mode"] == mode]
        durations = sorted(r["duration_ms"] for r in runs if r["status"] == "VERIFIED")
        groups[mode] = {"attempts": len(runs), "successes": len(durations),
            "success_rate": len(durations)/len(runs) if runs else None,
            "median_ms": statistics.median(durations) if durations else None,
            "p95_ms": durations[math.ceil(.95*len(durations))-1] if durations else None}
    reuse = [r for r in trials if r["mode"] == "reusable"]
    return {"groups": groups, "initial_learning_ms": learning_ms,
        "amortized_reuse_ms_per_attempt": (learning_ms+sum(r["duration_ms"] for r in reuse))/len(reuse) if reuse else None,
        "note": "Median and nearest-rank p95 use successful trials only; failures remain in success rates and raw trials. Durations include browser startup and verification, exclude queue time. Small samples are exploratory; no generalized speedup claim."}

def usage(job_id, after):
    with db() as s:
        rows = list(s.scalars(select(JobEvent).where(JobEvent.job_id==job_id, JobEvent.id>after).order_by(JobEvent.id)))
    calls = [r.data for r in rows if r.kind=="INFERENCE"]
    return {"successful_responses":len(calls), "failed_attempts":sum(r.kind=="INFERENCE_ERROR" for r in rows),
        "reported_usage":[r.get("usage") for r in calls], "models":sorted({r["model"] for r in calls}),
        "last_event":rows[-1].id if rows else after}

async def run_benchmark(runtime):
    original = runtime.job.payload
    trials = []
    start = time.monotonic()
    learning = await runtime.learn()
    learning_ms = round((time.monotonic()-start)*1000)
    learning_usage = usage(runtime.job.id, 0)
    cursor = learning_usage["last_event"]
    runtime.record("BENCHMARK_LEARNING", {"duration_ms":learning_ms,"usage":learning_usage,"result":learning})
    try:
        for pair in range(original["pairs"]):
            for mode in (("baseline","reusable") if pair%2==0 else ("reusable","baseline")):
                runtime.checkpoint()
                runtime.job.payload = {**original, "mode":mode}
                started = time.monotonic()
                try:
                    result = await runtime.read_orders()
                except Exception as exc:
                    if str(exc) in ("CANCELED","LEASE_LOST"):
                        raise
                    result = {"status":"FAILED","reason":type(exc).__name__}
                trial = {"pair":pair+1,"mode":mode,"status":result["status"],
                         "duration_ms":round((time.monotonic()-started)*1000),"result":result}
                trial["inference"] = usage(runtime.job.id,cursor)
                cursor = trial["inference"]["last_event"]
                trials.append(trial)
                runtime.record("BENCHMARK_TRIAL",trial)
                if result["status"] == "PORTAL_CHANGED":
                    return {"status":"BENCHMARK_INCOMPLETE","trials":trials,"learning_usage":learning_usage,
                            **summarize(trials,learning_ms)}
    finally:
        runtime.job.payload = original
    return {"status":"VERIFIED" if all(t["status"]=="VERIFIED" for t in trials) else "BENCHMARK_WITH_FAILURES",
            "trials":trials,"learning_usage":learning_usage,**summarize(trials,learning_ms)}
