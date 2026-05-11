from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator
import httpx
import os
import uuid
import uvicorn

from .database import get_db, engine
from . import models, schemas, crud

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Payment Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)

ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://order-service:8003")


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "payment-service"}


@app.post("/payments", response_model=schemas.PaymentResponse, status_code=201)
async def process_payment(payment: schemas.PaymentCreate, db: Session = Depends(get_db)):
    # Verify order exists
    async with httpx.AsyncClient() as client:
        order_resp = await client.get(f"{ORDER_SERVICE_URL}/orders/{payment.order_id}")
        if order_resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Order not found")
        order = order_resp.json()

    if order["status"] not in ["pending", "confirmed"]:
        raise HTTPException(status_code=409, detail=f"Order is in {order['status']} state, cannot process payment")

    # Simulate payment gateway (replace with Stripe/PayPal SDK in production)
    transaction_id = str(uuid.uuid4())
    payment_success = _simulate_payment_gateway(payment)

    db_payment = crud.create_payment(
        db, payment, transaction_id,
        status="completed" if payment_success else "failed"
    )

    if payment_success:
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"{ORDER_SERVICE_URL}/orders/{payment.order_id}/status",
                json={"status": "confirmed"}
            )

    return db_payment


@app.get("/payments/{payment_id}", response_model=schemas.PaymentResponse)
def get_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment


@app.get("/payments/order/{order_id}", response_model=schemas.PaymentResponse)
def get_payment_by_order(order_id: int, db: Session = Depends(get_db)):
    payment = crud.get_payment_by_order(db, order_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found for this order")
    return payment


@app.post("/payments/{payment_id}/refund", response_model=schemas.PaymentResponse)
async def refund_payment(payment_id: int, db: Session = Depends(get_db)):
    payment = crud.get_payment(db, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status != "completed":
        raise HTTPException(status_code=409, detail="Only completed payments can be refunded")

    refunded = crud.update_payment_status(db, payment_id, "refunded")

    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{ORDER_SERVICE_URL}/orders/{payment.order_id}/status",
            json={"status": "refunded"}
        )

    return refunded


def _simulate_payment_gateway(payment: schemas.PaymentCreate) -> bool:
    """Simulate payment gateway — replace with real Stripe/PayPal integration."""
    if payment.method == "card" and payment.card_last_four == "0000":
        return False
    return True


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8004, reload=True)
