from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from .database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, nullable=False, unique=True, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    method = Column(String(50), nullable=False)   # card, upi, netbanking
    status = Column(String(50), nullable=False)   # pending, completed, failed, refunded
    transaction_id = Column(String(255), unique=True, nullable=True)
    card_last_four = Column(String(4), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
