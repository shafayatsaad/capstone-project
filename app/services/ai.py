"""AI provider boundary: curated offline fixtures or a local Ollama model."""
import base64
import json
import mimetypes
import time
from pathlib import Path

import httpx

from app.config import settings
from app.schemas import ImageTags
from app.services.embeddings import embed_local


class ProviderError(RuntimeError):
    pass


class AIProvider:
    def __init__(self, mode: str | None = None, tenant_id: str = "demo"):
        self.mode = (mode or settings.ai_provider).lower()
        self.tenant_id = tenant_id

    async def classify(self, image: dict) -> tuple[ImageTags, dict]:
        self._check_budget()
        started = time.perf_counter()
        if self.mode == "demo":
            # Deliberate fixtures make the acceptance scenario repeatable without
            # claiming that an AI model examined the generated demo illustration.
            data = {
                "subject": image["expected_subject"], "category": image["category"],
                "attributes": image["attributes"], "caption": image["caption_hint"],
                "confidence": image.get("demo_confidence", 0.96),
            }
            tags = ImageTags.model_validate(data)
            return tags, {"provider": "demo-catalog", "model": "curated-fixture-v1", "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}
        if self.mode != "ollama":
            raise ProviderError(f"Unsupported AI_PROVIDER '{self.mode}'. Choose demo or ollama.")
        image_data, mime = await self._image_bytes(image)
        prompt = ("Describe the main visible subject. Return only a JSON object with keys subject, category, "
                  "attributes (array of short strings), caption, confidence (0..1). Do not infer a subject if "
                  "the image is unclear; use confidence below 0.55.")
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/chat", json={
                "model": settings.ollama_vision_model, "stream": False, "format": "json",
                "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(image_data).decode("ascii")]}],
            })
            response.raise_for_status()
        result = response.json()
        try:
            tags = ImageTags.model_validate_json(result["message"]["content"])
        except Exception as exc:
            raise ProviderError(f"Ollama returned invalid tag JSON: {exc}") from exc
        return tags, {"provider": "ollama", "model": settings.ollama_vision_model, "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}

    async def embed(self, text: str) -> tuple[list[float], dict]:
        self._check_budget()
        started = time.perf_counter()
        if self.mode != "ollama":
            return embed_local(text), {"provider": "local-hash", "model": "semantic-hash-v1", "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/embed", json={"model": settings.ollama_embedding_model, "input": text})
            response.raise_for_status()
        vectors = response.json().get("embeddings", [])
        if not vectors or not vectors[0]:
            raise ProviderError("Ollama embedding response contained no vector")
        return vectors[0], {"provider": "ollama", "model": settings.ollama_embedding_model, "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}

    @staticmethod
    def _check_budget():
        from app.db import db
        spent = float(db.row("SELECT COALESCE(SUM(cost_usd),0) AS spent FROM ai_calls WHERE tenant_id=?", (self.tenant_id,))["spent"])
        if settings.cost_budget_usd <= 0 or spent >= settings.cost_budget_usd:
            raise ProviderError(f"AI call blocked: configured cost budget ${settings.cost_budget_usd:.2f} is exhausted")

    @staticmethod
    async def _image_bytes(image: dict) -> tuple[bytes, str]:
        value = image.get("image_url", "")
        if value.startswith("http://") or value.startswith("https://"):
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                response = await client.get(value)
                response.raise_for_status()
            mime = response.headers.get("content-type", "image/jpeg").split(";")[0]
            return response.content, mime
        path = Path(value.removeprefix("file://"))
        if not value or not path.is_file():
            raise ProviderError(f"Image file is missing for {image['id']}: {value or '(empty image_url)'}")
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return path.read_bytes(), mime
