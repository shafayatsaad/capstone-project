"""
IP -> geo enrichment with a two-provider fallback chain, per the brief:
provider A (ip-api.com) tried first, provider B (ipapi.co) tried on failure,
and if both fail the submission is still stored -- just without geo data.
Enrichment is a nice-to-have, never a gate.

GEO_MODE=mock (the default) makes the fallback chain deterministic and
network-free, which is exactly what the brief asks for when *proving* the
chain: MOCK_PROVIDER_A_UP=false forces the fallback to provider B, and setting
both to false proves clean degradation. GEO_MODE=live calls the real free
APIs (no key, no card) during manual development.
"""
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable

import httpx

from app.config import settings


class ProviderDown(Exception):
    """Raised by a provider lookup to signal 'try the next one'."""


@dataclass
class GeoResult:
    country: Optional[str]
    city: Optional[str]


async def _mock_provider_a(ip: str) -> GeoResult:
    if not settings.mock_provider_a_up:
        raise ProviderDown("provider A is toggled down (MOCK_PROVIDER_A_UP=false)")
    return GeoResult(country="Bangladesh", city="Dhaka")


async def _mock_provider_b(ip: str) -> GeoResult:
    if not settings.mock_provider_b_up:
        raise ProviderDown("provider B is toggled down (MOCK_PROVIDER_B_UP=false)")
    return GeoResult(country="Bangladesh", city="Dhaka (via provider B)")


async def _live_provider_a(ip: str) -> GeoResult:
    url = settings.geo_provider_a_url.format(ip=ip)
    try:
        async with httpx.AsyncClient(timeout=settings.geo_timeout_seconds) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        body = resp.json()
        if body.get("status") == "fail":
            raise ProviderDown(body.get("message", "provider A returned a failure status"))
        return GeoResult(country=body.get("country"), city=body.get("city"))
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderDown(str(exc)) from exc


async def _live_provider_b(ip: str) -> GeoResult:
    url = settings.geo_provider_b_url.format(ip=ip)
    try:
        async with httpx.AsyncClient(timeout=settings.geo_timeout_seconds) as client:
            resp = await client.get(url)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise ProviderDown(body.get("reason", "provider B returned an error"))
        return GeoResult(country=body.get("country_name"), city=body.get("city"))
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderDown(str(exc)) from exc


def _chain() -> list[Callable[[str], Awaitable[GeoResult]]]:
    if settings.geo_mode == "live":
        return [_live_provider_a, _live_provider_b]
    return [_mock_provider_a, _mock_provider_b]


async def enrich(ip: str) -> Optional[GeoResult]:
    """Try each provider in order. Return the first success, or None if every
    provider in the chain failed -- the caller must treat None as "store
    without geo data", never as an error."""
    for provider in _chain():
        try:
            return await provider(ip)
        except ProviderDown:
            continue
        except Exception:
            # Any unexpected provider failure degrades the same way a known
            # ProviderDown does -- enrichment is never allowed to raise past
            # this function.
            continue
    return None
