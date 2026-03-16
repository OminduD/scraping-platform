"""Job listing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.schemas.job import JobOut
from api.services.job_service import JobService
from data_models import get_db

router = APIRouter()


@router.get("/", response_model=list[JobOut])
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    source: str | None = None,
    db: Session = Depends(get_db),
) -> list[JobOut]:
    """Return paginated job listings, optionally filtered by source."""
    svc = JobService(db)
    return svc.list_jobs(skip=skip, limit=limit, source=source)


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobOut:
    """Return a single job listing by ID."""
    svc = JobService(db)
    return svc.get_job(job_id)
