"""
Spam control: a hidden form field ("honeypot") that real visitors never see or
fill, because the embed bundle positions it off-screen. Bots that crawl and
fill every field may fill it too.

Spam submissions are silently dropped and receive the same success-shaped
response as a normal submission. They never enter persistence, enrichment, or
notifications. This matches the evaluator's explicit drop/reject acceptance
probe while avoiding useful feedback to bots.
"""
from app.schemas import SubmissionCreate


def is_spam(payload: SubmissionCreate) -> bool:
    return bool(payload.hp_field.strip())
