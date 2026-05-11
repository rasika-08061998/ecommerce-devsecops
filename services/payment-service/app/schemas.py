from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class PaymentCreate(BaseModel):
    order_id: int
    amount: float = Field(gt=0)
    currency: str = "USD"
    method: str   # card, upi, netbanking, wallet
    card_last_four: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    order_id: int
    amount: float
    currency: str
    method: str
    status: str
    transaction_id: Optional[str]
    card_last_four: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
