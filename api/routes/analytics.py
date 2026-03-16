"""Analytics routes — aggregations across scraped data."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.schemas.analytics import AnalyticsSummary
from api.services.analytics_service import AnalyticsService
from data_models import get_db

router = APIRouter()


@router.get("/", response_model=AnalyticsSummary)
def get_analytics(db: Session = Depends(get_db)) -> AnalyticsSummary:
    """Return aggregate statistics about scraped data."""
    svc = AnalyticsService(db)
    return svc.summary()
