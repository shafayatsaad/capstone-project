"""
The "confirmation email / webhook" side effect. In this capstone it's a log
line -- what's graded is the failure-tolerance, not the transport -- but it's
written as its own function so swapping in real SMTP or a webhook POST later
is a one-function change, not a redesign.

FORCE_NOTIFY_FAIL=true makes this raise on purpose, so Probe 5 ("a failing
side effect must not break the main path") can be proven deterministically
without needing a real flaky dependency.

Critically: this function's exceptions must never be allowed to propagate into
the request/response cycle for a submission. See submission_service.create_submission,
which calls this wrapped in a try/except and only logs on failure.
"""
import logging

from app.config import settings

logger = logging.getLogger("notify")


async def send_confirmation(submission_id: str, widget_id: str) -> None:
    if settings.force_notify_fail:
        raise RuntimeError("simulated notify failure (FORCE_NOTIFY_FAIL=true)")

    # Stand-in for a real email send or webhook POST.
    logger.info(
        "notify: would send confirmation for submission=%s widget=%s",
        submission_id,
        widget_id,
    )
