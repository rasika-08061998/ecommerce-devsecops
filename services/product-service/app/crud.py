from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, Tuple, List
from . import models, schemas


def get_product(db: Session, product_id: int):
    return db.query(models.Product).filter(models.Product.id == product_id).first()


def get_products(
    db: Session,
    skip: int = 0,
    limit: int = 20,
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
) -> Tuple[List, int]:
    query = db.query(models.Product).filter(models.Product.is_active == True)
    if category:
        query = query.filter(models.Product.category == category)
    if search:
        query = query.filter(
            or_(
                models.Product.name.ilike(f"%{search}%"),
                models.Product.description.ilike(f"%{search}%"),
            )
        )
    if min_price is not None:
        query = query.filter(models.Product.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Product.price <= max_price)
    total = query.count()
    products = query.offset(skip).limit(limit).all()
    return products, total


def create_product(db: Session, product: schemas.ProductCreate):
    db_product = models.Product(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


def update_product(db: Session, product_id: int, product_update: schemas.ProductUpdate):
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    for key, value in product_update.model_dump(exclude_unset=True).items():
        setattr(db_product, key, value)
    db.commit()
    db.refresh(db_product)
    return db_product


def delete_product(db: Session, product_id: int) -> bool:
    db_product = get_product(db, product_id)
    if not db_product:
        return False
    db_product.is_active = False
    db.commit()
    return True


def update_stock(db: Session, product_id: int, quantity_delta: int):
    db_product = get_product(db, product_id)
    if not db_product:
        return None
    new_qty = db_product.stock_quantity + quantity_delta
    if new_qty < 0:
        return "insufficient"
    db_product.stock_quantity = new_qty
    db.commit()
    db.refresh(db_product)
    return db_product


def get_categories(db: Session) -> List[str]:
    results = db.query(models.Product.category).distinct().filter(models.Product.is_active == True).all()
    return [r[0] for r in results]
