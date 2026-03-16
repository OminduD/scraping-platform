"""Product query service."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from data_models import Product


class ProductService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_products(
        self, *, skip: int = 0, limit: int = 50, source: str | None = None
    ) -> list[Product]:
        query = self.db.query(Product)
        if source:
            query = query.filter(Product.source == source.lower())
        return query.order_by(Product.created_at.desc()).offset(skip).limit(limit).all()

    def get_product(self, product_id: int) -> Product:
        product = self.db.query(Product).get(product_id)
        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
