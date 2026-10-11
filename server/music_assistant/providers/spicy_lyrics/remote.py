"""Bounded in-memory caching and rate limiting for the Spicy Lyrics API."""

from __future__ import annotations

import asyncio
import re
from collections import OrderedDict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import monotonic
from typing import Any

TRACK_ID = re.compile(r"^[A-Za-z0-9]{22}$")
CACHE_LIMIT = 128
CACHE_TTL = 300
MISSING_TTL = 60
REQUEST_INTERVAL = 1.0


@dataclass
class Reply:
    """A decoded HTTP response from the fixed API endpoint."""

    status: int
    body: dict[str, Any]
    headers: dict[str, str]


class SpicyError(Exception):
    """A safe error category suitable for returning to a client."""


class SpicyClient:
    """Fetch lyrics without duplicate concurrent lookups or unbounded caching."""

    def __init__(self, request: Callable[[str], Awaitable[Reply]]) -> None:
        """Initialize with an authenticated HTTP transport."""
        self.request = request
        self.lock = asyncio.Lock()
        self.cache: OrderedDict[str, tuple[float, dict[str, Any] | None]] = OrderedDict()
        self.next_request = 0.0
        self.cooldown = 0.0

    async def get(self, track_id: str) -> dict[str, Any] | None:
        """Return lyrics, or None when the service has no lyrics for the track."""
        if not TRACK_ID.fullmatch(track_id):
            raise SpicyError("invalid_track")
        async with self.lock:
            now = monotonic()
            if track_id in self.cache:
                expiration, body = self.cache[track_id]
                if expiration > now:
                    self.cache.move_to_end(track_id)
                    return body
                del self.cache[track_id]
            if self.cooldown > now:
                raise SpicyError("rate_limited")
            delay = self.next_request - now
            if delay > 0:
                await asyncio.sleep(delay)
            self.next_request = monotonic() + REQUEST_INTERVAL
            reply = await self.request(track_id)
            if reply.status == 429:
                try:
                    retry = float(reply.headers.get("Retry-After", "60"))
                except ValueError:
                    retry = 60.0
                self.cooldown = monotonic() + max(1.0, min(retry, 86400.0))
                raise SpicyError("rate_limited")
            if reply.status in (401, 403):
                raise SpicyError("invalid_api_key")
            if reply.status == 404:
                body = None
            elif reply.status != 200:
                raise SpicyError("service_unavailable")
            else:
                body = reply.body.get("Body")
                if not isinstance(body, dict) or body.get("Type") not in (
                    "Syllable",
                    "Line",
                    "Static",
                ):
                    raise SpicyError("invalid_response")
            self.cache[track_id] = (
                monotonic() + (CACHE_TTL if body else MISSING_TTL),
                body,
            )
            while len(self.cache) > CACHE_LIMIT:
                self.cache.popitem(last=False)
            return body


def spotify_id(track: Any) -> str | None:
    """Resolve an existing Spotify mapping without guessing a different recording."""
    for mapping in getattr(track, "provider_mappings", ()):
        if mapping.provider_domain == "spotify" and TRACK_ID.fullmatch(mapping.item_id):
            return str(mapping.item_id)
    uri = str(getattr(track, "uri", ""))
    match = re.fullmatch(r"spotify://track/([A-Za-z0-9]{22})", uri)
    return match[1] if match else None
