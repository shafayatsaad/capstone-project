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
    gemini_api_key: str = os.getenv("GEMINI_API_KEY", "")
    gemini_vision_model: str = os.getenv("GEMINI_VISION_MODEL", "gemini-2.5-flash")
    gemini_embedding_model: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
    gemini_input_usd_per_million: float = float(os.getenv("GEMINI_INPUT_USD_PER_MILLION", "0.30"))
    gemini_output_usd_per_million: float = float(os.getenv("GEMINI_OUTPUT_USD_PER_MILLION", "2.50"))
    gemini_embedding_usd_per_million: float = float(os.getenv("GEMINI_EMBEDDING_USD_PER_MILLION", "0.15"))
    upload_max_bytes: int = int(os.getenv("UPLOAD_MAX_BYTES", str(5 * 1024 * 1024)))
    min_confidence: float = float(os.getenv("MIN_CONFIDENCE", "0.55"))
    min_similarity: float = float(os.getenv("MIN_SIMILARITY", "0.20"))
    batch_retries: int = int(os.getenv("BATCH_RETRIES", "3"))
    batch_delay_seconds: float = float(os.getenv("BATCH_DELAY_SECONDS", "0.05"))
    cost_budget_usd: float = float(os.getenv("COST_BUDGET_USD", "0.50"))


settings = Settings()
