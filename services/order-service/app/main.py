from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator
from typing import List, Optional
import httpx
import os
import uvicorn

from .database import get_db, engine
from . import models, schemas, crud

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Order Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

PRODUCT_SERVICE_URL = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8002")
USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://user-service:8001")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "order-service"}


@app.post("/orders", response_model=schemas.OrderResponse, status_code=201)
async def create_order(order: schemas.OrderCreate, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        # Verify user exists
        user_resp = await client.get(f"{USER_SERVICE_URL}/users/{order.user_id}")
        if user_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="User not found")

        # Verify products and calculate total
        total = 0.0
        verified_items = []
        for item in order.items:
            prod_resp = await client.get(f"{PRODUCT_SERVICE_URL}/products/{item.product_id}")
            if prod_resp.status_code != 200:
                raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")
            product = prod_resp.json()
            if product["stock_quantity"] < item.quantity:
                raise HTTPException(
                    status_code=409,
                    detail=f"Insufficient stock for product {item.product_id}"
                )
            item_total = product["price"] * item.quantity
            total += item_total
            verified_items.append({**item.model_dump(), "unit_price": product["price"], "subtotal": item_total})

        # Reserve stock
        for item in order.items:
            await client.patch(
                f"{PRODUCT_SERVICE_URL}/products/{item.product_id}/stock",
                json={"quantity_delta": -item.quantity}
            )

    db_order = crud.create_order(db, order, verified_items, total)
    return db_order


@app.get("/orders/{order_id}", response_model=schemas.OrderResponse)
def get_order(order_id: int, db: Session = Depends(get_db)):
    order = crud.get_order(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@app.get("/orders", response_model=List[schemas.OrderResponse])
def list_orders(
    user_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return crud.get_orders(db, user_id=user_id, skip=skip, limit=limit)


@app.patch("/orders/{order_id}/status", response_model=schemas.OrderResponse)
def update_order_status(order_id: int, status_update: schemas.OrderStatusUpdate, db: Session = Depends(get_db)):
    order = crud.update_order_status(db, order_id, status_update.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8003, reload=True)
