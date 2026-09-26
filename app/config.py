"""
Central place for every environment-driven setting. Nothing in the rest of the
app should call os.getenv directly -- import `settings` instead, so the whole
config surface is visible in one file.
"""
import os
from pathlib import Path


def _load_dotenv() -> None:
    """Load the project's simple KEY=value .env file without overriding the shell."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


_load_dotenv()


class Settings:
    # --- database ---
    # Default is a local SQLite file so `python seed.py && uvicorn ...` works with
    # zero external services. Point this at Postgres for the "real" run:
    # postgresql+psycopg2://widget:widget@localhost:5432/widgetdb
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./dev.db")
    jwt_secret: str = os.getenv("JWT_SECRET", "dev-only-change-me-before-deploying")
    jwt_ttl_minutes: int = int(os.getenv("JWT_TTL_MINUTES", "60"))
    public_base_url: str = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000")

    # --- CORS ---
    # The submission + delivery endpoints are called from customer websites we
    # do not control, so "*" is the correct default for this product, not a
    # shortcut. Restrict via env if you ever need to.
    cors_allow_origins: list[str] = [
        origin.strip() for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if origin.strip()
    ]

    # --- payload limits ---
    max_payload_bytes: int = int(os.getenv("MAX_PAYLOAD_BYTES", 10_000))  # 10 KB
    max_fields: int = int(os.getenv("MAX_FIELDS", 20))
    max_field_length: int = int(os.getenv("MAX_FIELD_LENGTH", 2_000))

    # --- rate limiting ---
    rate_limit_submissions: str = os.getenv("RATE_LIMIT_SUBMISSIONS", "20/minute")

    # --- geo enrichment ---
    # "mock" gives deterministic, offline-safe results for the fallback-chain
    # proof required by the brief. "live" calls the real free providers.
    geo_mode: str = os.getenv("GEO_MODE", "mock")
    mock_provider_a_up: bool = os.getenv("MOCK_PROVIDER_A_UP", "true").lower() == "true"
    mock_provider_b_up: bool = os.getenv("MOCK_PROVIDER_B_UP", "true").lower() == "true"
    geo_provider_a_url: str = os.getenv("GEO_PROVIDER_A_URL", "http://ip-api.com/json/{ip}")
    geo_provider_b_url: str = os.getenv("GEO_PROVIDER_B_URL", "https://ipapi.co/{ip}/json/")
    geo_timeout_seconds: float = float(os.getenv("GEO_TIMEOUT_SECONDS", 2.0))

    # --- notification side effect (email / webhook stand-in) ---
    # Forcing this to fail is how Probe 5 (side effect must not break the main
    # path) gets proven deterministically.
    force_notify_fail: bool = os.getenv("FORCE_NOTIFY_FAIL", "false").lower() == "true"

settings = Settings()
