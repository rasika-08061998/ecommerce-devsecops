from fastapi import FastAPI, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator
from typing import List, Optional
import uvicorn

from .database import get_db, engine
from . import models, schemas, crud

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Service", version="1.0.0")
Instrumentator().instrument(app).expose(app)


@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "product-service"}


@app.post("/products", response_model=schemas.ProductResponse, status_code=201)
def create_product(product: schemas.ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, product)


@app.get("/products", response_model=schemas.ProductListResponse)
def list_products(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = None,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
):
    products, total = crud.get_products(db, skip, limit, category, search, min_price, max_price)
    return {"products": products, "total": total, "skip": skip, "limit": limit}


@app.get("/products/{product_id}", response_model=schemas.ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = crud.get_product(db, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.put("/products/{product_id}", response_model=schemas.ProductResponse)
def update_product(product_id: int, product_update: schemas.ProductUpdate, db: Session = Depends(get_db)):
    product = crud.update_product(db, product_id, product_update)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    if not crud.delete_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")


@app.patch("/products/{product_id}/stock", response_model=schemas.ProductResponse)
def update_stock(product_id: int, stock_update: schemas.StockUpdate, db: Session = Depends(get_db)):
    product = crud.update_stock(db, product_id, stock_update.quantity_delta)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    if product == "insufficient":
        raise HTTPException(status_code=409, detail="Insufficient stock")
    return product


@app.get("/categories", response_model=List[str])
def get_categories(db: Session = Depends(get_db)):
    return crud.get_categories(db)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8002, reload=True)
