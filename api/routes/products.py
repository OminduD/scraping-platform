"""Product listing routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.schemas.product import ProductOut
from api.services.product_service import ProductService
from data_models import get_db

router = APIRouter()


@router.get("/", response_model=list[ProductOut])
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    source: str | None = None,
    db: Session = Depends(get_db),
) -> list[ProductOut]:
    """Return paginated product listings, optionally filtered by source."""
    svc = ProductService(db)
    return svc.list_products(skip=skip, limit=limit, source=source)


@router.get("/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductOut:
    """Return a single product by ID."""
    svc = ProductService(db)
    return svc.get_product(product_id)
