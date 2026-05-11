from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)


class OrderCreate(BaseModel):
    user_id: int
    items: List[OrderItemCreate]
    shipping_address: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class OrderStatusUpdate(BaseModel):
    status: str


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class OrderResponse(BaseModel):
    id: int
    user_id: int
    status: str
    total_amount: float
    shipping_address: Optional[Dict[str, Any]]
    notes: Optional[str]
    items: List[OrderItemResponse]
    created_at: datetime

    class Config:
        from_attributes = True
