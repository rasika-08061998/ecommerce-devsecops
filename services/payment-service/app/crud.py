from sqlalchemy.orm import Session
from . import models, schemas


def create_payment(db: Session, payment: schemas.PaymentCreate, transaction_id: str, status: str):
    db_payment = models.Payment(
        order_id=payment.order_id,
        amount=payment.amount,
        currency=payment.currency,
        method=payment.method,
        card_last_four=payment.card_last_four,
        transaction_id=transaction_id,
        status=status,
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment


def get_payment(db: Session, payment_id: int):
    return db.query(models.Payment).filter(models.Payment.id == payment_id).first()


def get_payment_by_order(db: Session, order_id: int):
    return db.query(models.Payment).filter(models.Payment.order_id == order_id).first()


def update_payment_status(db: Session, payment_id: int, status: str):
    db_payment = get_payment(db, payment_id)
    if not db_payment:
        return None
    db_payment.status = status
    db.commit()
    db.refresh(db_payment)
    return db_payment
