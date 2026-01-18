from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass

from ..utils.logging import get_logger

logger = get_logger("sie.jobs")


@dataclass
class JobStatus:
    job_id: str
    status: str
    domain: str
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    progress: str = "queued"
    error: str | None = None
    result: dict | None = None


class JobManager:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active_job_id: str | None = None
        self._jobs: dict[str, JobStatus] = {}

    def create_job(self, domain: str) -> JobStatus:
        with self._lock:
            if self._active_job_id is not None:
                raise RuntimeError("busy")
            job_id = uuid.uuid4().hex
            job = JobStatus(
                job_id=job_id,
                status="queued",
                domain=domain,
                created_at=time.time(),
            )
            self._jobs[job_id] = job
            self._active_job_id = job_id
            logger.info("Job queued: %s domain=%s", job_id, domain)
            return job

    def start_job(self, job_id: str) -> JobStatus:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.started_at = time.time()
            job.progress = "starting"
            logger.info("Job started: %s domain=%s", job_id, job.domain)
            return job

    def finish_job(self, job_id: str, result: dict | None = None) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "complete"
            job.finished_at = time.time()
            job.progress = "complete"
            job.result = result
            self._active_job_id = None
            logger.info("Job complete: %s", job_id)

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "failed"
            job.finished_at = time.time()
            job.progress = "failed"
            job.error = error
            self._active_job_id = None
            logger.error("Job failed: %s error=%s", job_id, error)

    def update_progress(self, job_id: str, progress: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.progress = progress
            logger.info("Job progress: %s %s", job_id, progress)

    def get_job(self, job_id: str) -> JobStatus | None:
        with self._lock:
            return self._jobs.get(job_id)

    def is_busy(self) -> bool:
        with self._lock:
            return self._active_job_id is not None


job_manager = JobManager()
