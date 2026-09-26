"""Deterministic, dependency-free semantic features for the compact demo corpus.

For stronger paraphrase coverage configure the Ollama embedding adapter in `ai.py`.
"""
import hashlib
import math
import re

DIMENSIONS = 128
SYNONYMS = {
    "vulpes": "fox", "vulpes vulpes": "fox", "canid": "fox", "canine": "dog",
    "lupus": "wolf", "canis lupus": "wolf", "wolf-like": "wolf",
    "automobile": "car", "vehicle": "car", "motorcar": "car", "bicycle": "bike",
    "cycling": "bike", "aircraft": "airplane", "aeroplane": "airplane",
    "ocean": "beach", "seaside": "beach", "shore": "beach", "woods": "forest",
    "woodland": "forest", "mountainous": "mountain", "peak": "mountain",
    "waterfall": "waterfall", "produce": "food", "fruit": "food", "meal": "food",
}


def canonical_text(text: str) -> str:
    value = text.lower().replace("vulpes vulpes", "fox").replace("canis lupus", "wolf")
    for source, target in SYNONYMS.items():
        value = value.replace(source, target)
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def embed_local(text: str) -> list[float]:
    tokens = canonical_text(text).split()
    features = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
    vector = [0.0] * DIMENSIONS
    for token in features:
        digest = hashlib.blake2b(token.encode(), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % DIMENSIONS
        vector[index] += 1.0 if digest[4] % 2 else -1.0
    magnitude = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [round(value / magnitude, 7) for value in vector]


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
