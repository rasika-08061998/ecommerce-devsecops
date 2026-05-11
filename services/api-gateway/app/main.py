from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
import httpx
import os
import time
from collections import defaultdict
from typing import Dict
import uvicorn

app = FastAPI(title="API Gateway", version="1.0.0", docs_url="/docs")

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs
SERVICES: Dict[str, str] = {
    "users":    os.getenv("USER_SERVICE_URL",    "http://user-service:8001"),
    "products": os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8002"),
    "orders":   os.getenv("ORDER_SERVICE_URL",   "http://order-service:8003"),
    "payments": os.getenv("PAYMENT_SERVICE_URL", "http://payment-service:8004"),
}

# Simple in-memory rate limiter
rate_limit_store: Dict[str, list] = defaultdict(list)
RATE_LIMIT = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))


def check_rate_limit(client_ip: str):
    now = time.time()
    window = 60
    requests = rate_limit_store[client_ip]
    rate_limit_store[client_ip] = [r for r in requests if now - r < window]
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded. Try again later.")
    rate_limit_store[client_ip].append(now)


@app.get("/health")
async def health_check():
    health_results = {"gateway": "healthy", "services": {}}
    async with httpx.AsyncClient(timeout=3.0) as client:
        for name, url in SERVICES.items():
            try:
                resp = await client.get(f"{url}/health")
                health_results["services"][name] = "healthy" if resp.status_code == 200 else "degraded"
            except Exception:
                health_results["services"][name] = "unreachable"
    return health_results


async def proxy_request(request: Request, service: str, path: str):
    """Generic proxy to forward requests to downstream services."""
    if service not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service}' not found")

    client_ip = request.client.host
    check_rate_limit(client_ip)

    target_url = f"{SERVICES[service]}/{path}"
    query_string = request.url.query
    if query_string:
        target_url += f"?{query_string}"

    headers = dict(request.headers)
    headers.pop("host", None)

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
            )
        return JSONResponse(
            content=response.json() if response.content else None,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail=f"Service '{service}' is unavailable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail=f"Service '{service}' timed out")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Bad gateway: {str(e)}")


# Route all service traffic through gateway
@app.api_route("/api/users/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def users_proxy(path: str, request: Request):
    return await proxy_request(request, "users", path)


@app.api_route("/api/auth/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def auth_proxy(path: str, request: Request):
    return await proxy_request(request, "users", f"auth/{path}")


@app.api_route("/api/products/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def products_proxy(path: str, request: Request):
    return await proxy_request(request, "products", path)


@app.api_route("/api/products", methods=["GET", "POST"])
async def products_root_proxy(request: Request):
    return await proxy_request(request, "products", "products")


@app.api_route("/api/orders/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def orders_proxy(path: str, request: Request):
    return await proxy_request(request, "orders", path)


@app.api_route("/api/orders", methods=["GET", "POST"])
async def orders_root_proxy(request: Request):
    return await proxy_request(request, "orders", "orders")


@app.api_route("/api/payments/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def payments_proxy(path: str, request: Request):
    return await proxy_request(request, "payments", path)


@app.api_route("/api/payments", methods=["GET", "POST"])
async def payments_root_proxy(request: Request):
    return await proxy_request(request, "payments", "payments")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
