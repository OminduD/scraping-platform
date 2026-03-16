"""Job listing query service."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from data_models import JobListing


class JobService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_jobs(
        self, *, skip: int = 0, limit: int = 50, source: str | None = None
    ) -> list[JobListing]:
        query = self.db.query(JobListing)
        if source:
            query = query.filter(JobListing.source == source.lower())
        return query.order_by(JobListing.created_at.desc()).offset(skip).limit(limit).all()

    def get_job(self, job_id: int) -> JobListing:
        job = self.db.query(JobListing).get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job listing not found")
        return job
