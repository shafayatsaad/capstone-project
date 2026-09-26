from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.rate_limit import limiter
from app.routers import public_submissions, auth, widgets, public_delivery, dashboard

app = FastAPI(
    title="Embeddable Widget & Lead-Capture Platform",
    description="A resilient embeddable lead-capture platform with tenant-scoped management and a public widget API.",
    version="1.0.0",
)

# The submission endpoint is called from arbitrary customer websites, so this
# is the intentional product behaviour, not a default left un-configured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(public_submissions.router)
app.include_router(auth.router)
app.include_router(widgets.router)
app.include_router(public_delivery.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    return {"status": "ok"}
