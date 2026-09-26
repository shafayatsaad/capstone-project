"""Environment-backed service settings."""
import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_path: str = os.getenv("DATABASE_PATH", "data/app.db")
    ai_provider: str = os.getenv("AI_PROVIDER", "demo").lower()
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
    ollama_vision_model: str = os.getenv("OLLAMA_VISION_MODEL", "llava")
    ollama_embedding_model: str = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.55"))
    min_similarity: float = float(os.getenv("MIN_SIMILARITY", "0.20"))
    batch_retries: int = int(os.getenv("BATCH_RETRIES", "3"))
    batch_delay_seconds: float = float(os.getenv("BATCH_DELAY_SECONDS", "0.05"))
    cost_budget_usd: float = float(os.getenv("COST_BUDGET_USD", "0.50"))


settings = Settings()
