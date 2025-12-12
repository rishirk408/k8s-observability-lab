from fastapi import FastAPI
from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from fastapi.responses import Response
import random
import time

app = FastAPI(title="Observability Demo App")

# Prometheus metrics
REQUEST_COUNT = Counter(
    "demo_app_requests_total",
    "Total HTTP requests for demo app",
    ["method", "endpoint"]
)


@app.get("/")
def root():
    REQUEST_COUNT.labels(method="GET", endpoint="/").inc()
    return {"status": "ok", "message": "Observability demo app running"}


@app.get("/api/items")
def get_items():
    REQUEST_COUNT.labels(method="GET", endpoint="/api/items").inc()
    # simulate some work
    time.sleep(random.uniform(0.05, 0.2))
    return {"items": ["item1", "item2", "item3"]}


@app.get("/health")
def health():
    REQUEST_COUNT.labels(method="GET", endpoint="/health").inc()
    return {"status": "healthy"}


@app.get("/error")
def error():
    REQUEST_COUNT.labels(method="GET", endpoint="/error").inc()
    # simulate an error endpoint to trigger alerts
    return Response(content="Error!", status_code=500)


@app.get("/metrics")
def metrics():
    # Expose Prometheus metrics
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

