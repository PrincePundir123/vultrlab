"""Print bounded latest failure diagnostics, without environment or credentials."""
from sqlalchemy import select
from guard.db import Job, JobEvent, db
import time

with db() as s:
    rows = list(s.scalars(select(JobEvent).where(JobEvent.kind == "SANDBOX_RESULT").order_by(JobEvent.id.desc()).limit(1)))
    for row in rows:
        print({k: v for k, v in row.data.items() if k in ("status", "reason", "error", "cleanup", "sandbox")})
        job = s.get(Job, row.job_id)
        rejected = s.scalar(select(JobEvent).where(JobEvent.job_id == job.id,
                                                   JobEvent.kind == "CANDIDATE_REJECTED"))
        if job.state == "RUNNING" and rejected:
            job.state, job.finished, job.result = "FAILED", time.time(), {"reason": "Acceptance driver stopped after recorded candidate rejection"}
    s.commit()
