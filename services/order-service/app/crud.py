from sqlalchemy.orm import Session
from typing import Optional, List
from . import models, schemas


def create_order(db: Session, order: schemas.OrderCreate, verified_items: list, total: float):
    db_order = models.Order(
        user_id=order.user_id,
        total_amount=total,
        shipping_address=order.shipping_address,
        notes=order.notes,
    )
    db.add(db_order)
    db.flush()

    for item in verified_items:
        db_item = models.OrderItem(
            order_id=db_order.id,
            product_id=item["product_id"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            subtotal=item["subtotal"],
        )
        db.add(db_item)

    db.commit()
    db.refresh(db_order)
    return db_order


def get_order(db: Session, order_id: int):
    return db.query(models.Order).filter(models.Order.id == order_id).first()


def get_orders(db: Session, user_id: Optional[int] = None, skip: int = 0, limit: int = 20):
    query = db.query(models.Order)
    if user_id:
        query = query.filter(models.Order.user_id == user_id)
    return query.order_by(models.Order.created_at.desc()).offset(skip).limit(limit).all()


def update_order_status(db: Session, order_id: int, status: str):
    db_order = get_order(db, order_id)
    if not db_order:
        return None
    db_order.status = status
    db.commit()
    db.refresh(db_order)
    return db_order
