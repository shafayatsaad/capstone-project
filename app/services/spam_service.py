"""
Spam control: a hidden form field ("honeypot") that real visitors never see or
fill, because it's styled off-screen in the actual widget (Phase 3). Bots that
crawl and fill every field will fill it too.

Design choice, documented here on purpose: a spam hit is stored (so the owner's
counts stay accurate and there's a record) but flagged `is_spam=True`, skips
enrichment and the notify side effect, and the HTTP response looks identical to
a normal success. Telling a bot "rejected" just teaches it to iterate; silence
doesn't.
"""
from app.config import settings
from app.schemas import SubmissionCreate


def is_spam(payload: SubmissionCreate) -> bool:
    return bool(payload.hp_field.strip())


def honeypot_field_name() -> str:
    return settings.honeypot_field_name
