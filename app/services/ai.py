"""AI provider boundary: offline fixtures, local Ollama, Gemini API, or NVIDIA."""
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


def _parse_image_tags(text: str) -> ImageTags:
    """Validate model JSON, tolerating the common Markdown code-fence wrapper."""
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        candidate = "\n".join(lines).strip()
    try:
        return ImageTags.model_validate_json(candidate)
    except Exception:
        # Some providers add a short preamble despite the JSON-only instruction.
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end < start:
            raise
        return ImageTags.model_validate_json(candidate[start:end + 1])


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
        image_data, mime = await self._image_bytes(image)
        prompt = ("Describe the main visible subject. Return only a JSON object with keys subject, category, "
                  "attributes (array of short strings), caption, confidence (0..1). Do not infer a subject if "
                  "the image is unclear; use confidence below 0.55.")
        if self.mode == "gemini":
            if not settings.gemini_api_key:
                raise ProviderError("GEMINI_API_KEY is missing. Add it to .env and restart the server.")
            schema = {"type": "OBJECT", "properties": {
                "subject": {"type": "STRING"}, "category": {"type": "STRING"},
                "attributes": {"type": "ARRAY", "items": {"type": "STRING"}},
                "caption": {"type": "STRING"}, "confidence": {"type": "NUMBER"}},
                "required": ["subject", "category", "attributes", "caption", "confidence"]}
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_vision_model}:generateContent",
                    headers={"x-goog-api-key": settings.gemini_api_key},
                    json={"contents": [{"parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime, "data": base64.b64encode(image_data).decode("ascii")}},
                    ]}], "generationConfig": {"responseMimeType": "application/json", "responseSchema": schema}},
                )
                if response.is_error:
                    raise ProviderError(f"Gemini request failed ({response.status_code}): {response.text[:600]}")
            result = response.json()
            try:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                tags = _parse_image_tags(text)
            except Exception as exc:
                raise ProviderError(f"Gemini returned invalid tag JSON: {exc}") from exc
            usage = result.get("usageMetadata", {})
            input_tokens = int(usage.get("promptTokenCount", 0))
            output_tokens = int(usage.get("candidatesTokenCount", 0))
            cost = (input_tokens * settings.gemini_input_usd_per_million + output_tokens * settings.gemini_output_usd_per_million) / 1_000_000
            return tags, {"provider": "gemini", "model": settings.gemini_vision_model,
                "duration_ms": int((time.perf_counter()-started)*1000), "input_tokens": input_tokens,
                "output_tokens": output_tokens, "cost_usd": cost}
        if self.mode == "nvidia":
            if not settings.nvidia_api_key:
                raise ProviderError("NVIDIA_API_KEY is missing. Add it to .env and restart the server.")
            data_url = f"data:{mime};base64,{base64.b64encode(image_data).decode('ascii')}"
            async with httpx.AsyncClient(timeout=120) as client:
                response = await client.post(
                    f"{settings.nvidia_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                    json={
                        "model": settings.nvidia_vision_model,
                        "messages": [{"role": "user", "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ]}],
                        "temperature": 0, "top_p": 1, "max_tokens": 1024,
                    },
                )
                if response.is_error:
                    raise ProviderError(f"NVIDIA request failed ({response.status_code}): {response.text[:600]}")
            result = response.json()
            try:
                text = result["choices"][0]["message"]["content"]
                tags = _parse_image_tags(text)
            except Exception as exc:
                raise ProviderError(f"NVIDIA returned invalid tag JSON: {exc}") from exc
            usage = result.get("usage", {})
            input_tokens = int(usage.get("prompt_tokens", 0))
            output_tokens = int(usage.get("completion_tokens", 0))
            return tags, {"provider": "nvidia", "model": settings.nvidia_vision_model,
                "duration_ms": int((time.perf_counter()-started)*1000), "input_tokens": input_tokens,
                "output_tokens": output_tokens, "cost_usd": 0.0}
        if self.mode != "ollama":
            raise ProviderError(f"Unsupported AI_PROVIDER '{self.mode}'. Choose demo, ollama, gemini, or nvidia.")
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/chat", json={
                "model": settings.ollama_vision_model, "stream": False, "format": "json",
                "messages": [{"role": "user", "content": prompt, "images": [base64.b64encode(image_data).decode("ascii")]}],
            })
            response.raise_for_status()
        result = response.json()
        try:
            tags = _parse_image_tags(result["message"]["content"])
        except Exception as exc:
            raise ProviderError(f"Ollama returned invalid tag JSON: {exc}") from exc
        return tags, {"provider": "ollama", "model": settings.ollama_vision_model, "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}

    async def embed(self, text: str) -> tuple[list[float], dict]:
        self._check_budget()
        started = time.perf_counter()
        if self.mode == "gemini":
            if not settings.gemini_api_key:
                raise ProviderError("GEMINI_API_KEY is missing. Add it to .env and restart the server.")
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_embedding_model}:embedContent",
                    headers={"x-goog-api-key": settings.gemini_api_key},
                    json={"content": {"parts": [{"text": text}]},
                          "embedContentConfig": {"taskType": "SEMANTIC_SIMILARITY"}},
                )
                if response.is_error:
                    raise ProviderError(f"Gemini embedding failed ({response.status_code}): {response.text[:600]}")
            result = response.json()
            vector = result.get("embedding", {}).get("values", [])
            if not vector:
                raise ProviderError("Gemini embedding response contained no vector")
            tokens = int(result.get("usageMetadata", {}).get("promptTokenCount", 0))
            cost = tokens * settings.gemini_embedding_usd_per_million / 1_000_000
            return vector, {"provider": "gemini", "model": settings.gemini_embedding_model,
                "duration_ms": int((time.perf_counter()-started)*1000), "input_tokens": tokens,
                "output_tokens": 0, "cost_usd": cost}
        if self.mode == "demo":
            return embed_local(text), {"provider": "local-hash", "model": "semantic-hash-v1", "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}
        if self.mode == "nvidia":
            # Option A: NVIDIA vision is used for classification; embeddings stay in the
            # deterministic local space so images and posts rank in matching dimensions.
            return embed_local(text), {"provider": "nvidia-local", "model": "semantic-hash-v1", "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}
        if self.mode != "ollama":
            raise ProviderError(f"Unsupported AI_PROVIDER '{self.mode}'. Choose demo, ollama, gemini, or nvidia.")
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(f"{settings.ollama_base_url}/api/embed", json={"model": settings.ollama_embedding_model, "input": text})
            response.raise_for_status()
        vectors = response.json().get("embeddings", [])
        if not vectors or not vectors[0]:
            raise ProviderError("Ollama embedding response contained no vector")
        return vectors[0], {"provider": "ollama", "model": settings.ollama_embedding_model, "duration_ms": int((time.perf_counter()-started)*1000), "cost_usd": 0.0}

    def _check_budget(self):
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
