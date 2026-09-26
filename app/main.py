from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.rate_limit import limiter
from app.routers import public_submissions

app = FastAPI(
    title="Embeddable Widget & Lead-Capture Platform",
    description="FlyRank Backend Track capstone -- Phase 2: the hardened public submission path.",
    version="0.2.0",
)

# The submission endpoint is called from arbitrary customer websites, so this
# is the intentional product behaviour, not a default left un-configured.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=False,
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.include_router(public_submissions.router)


@app.get("/health")
def health():
    return {"status": "ok"}
