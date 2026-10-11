"""Spicy Lyrics plugin with an authenticated queue-bound lyrics API."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from aiohttp import ClientError, ClientTimeout
from music_assistant.models.plugin import PluginProvider
from music_assistant_models.auth import Scope
from music_assistant_models.enums import MediaType
from music_assistant_models.errors import (
    InvalidDataError,
    LoginFailed,
    ResourceTemporarilyUnavailable,
)

from .remote import Reply, SpicyClient, SpicyError, spotify_id

if TYPE_CHECKING:
    from music_assistant.mass import MusicAssistant
    from music_assistant.models import ProviderInstanceType
    from music_assistant_models.config_entries import ProviderConfig
    from music_assistant_models.provider import ProviderManifest

API_URL = "https://api.spicylyrics.org/v1/lyrics"
MAX_RESPONSE_BYTES = 2 * 1024 * 1024


async def setup(
    mass: MusicAssistant, manifest: ProviderManifest, config: ProviderConfig
) -> ProviderInstanceType:
    """Initialize the plugin."""
    return SpicyLyricsPlugin(mass, manifest, config, set())


class SpicyLyricsPlugin(PluginProvider):
    """Expose original timing and credits to the existing fullscreen lyrics area."""

    async def handle_async_init(self) -> None:
        """Prepare the transport using credentials stored by the setup flow."""
        self._key = str(self.get_setup_value("api_key") or "").strip()
        if not self._key.startswith("sl_sk_"):
            raise LoginFailed("Spicy Lyrics requires a secret API key (sl_sk_).")
        self._client = SpicyClient(self._request)
        self._unregister: Callable[[], None] | None = None

    async def loaded_in_mass(self) -> None:
        """Register the read-only lyrics command after loading."""
        self._unregister = self.mass.register_api_command(
            "spicy_lyrics/get", self.get_lyrics, required_scope=Scope.QUEUES_READ
        )

    async def unload(self, is_removed: bool = False) -> None:
        """Remove the command and release cached lyrics."""
        if self._unregister:
            self._unregister()
            self._unregister = None
        self._client.cache.clear()

    async def get_lyrics(self, queue_id: str) -> dict[str, Any]:
        """Return lyrics for the currently playing track in an existing queue."""
        queue = self.mass.player_queues.get(queue_id)
        if queue is None:
            raise InvalidDataError("Unknown queue")
        item = queue.current_item
        result: dict[str, Any] = {
            "status": "no_track",
            "queue_item_id": item.queue_item_id if item else None,
            "lyrics": None,
        }
        if not queue.active or not item or not item.media_item:
            return result
        track = item.media_item
        if track.media_type != MediaType.TRACK:
            return result
        track_id = spotify_id(track)
        if track_id is None:
            result["status"] = "unsupported_track"
            return result
        try:
            body = await self._client.get(track_id)
        except SpicyError as err:
            if str(err) == "invalid_api_key":
                raise LoginFailed("Spicy Lyrics did not accept the API key.") from None
            raise ResourceTemporarilyUnavailable(
                "Spicy Lyrics is temporarily unavailable. Please try again later."
            ) from None
        result["status"] = "ready" if body else "no_lyrics"
        result["lyrics"] = body
        return result

    async def _request(self, track_id: str) -> Reply:
        """Request the fixed endpoint; keep secrets and upstream errors server-side."""
        try:
            async with self.mass.http_session.get(
                f"{API_URL}/{track_id}",
                headers={"Authorization": f"Bearer {self._key}"},
                timeout=ClientTimeout(total=15),
                allow_redirects=False,
            ) as response:
                body: dict[str, Any] = {}
                if response.status == 200:
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in response.content.iter_chunked(65536):
                        size += len(chunk)
                        if size > MAX_RESPONSE_BYTES:
                            raise SpicyError("invalid_response")
                        chunks.append(chunk)
                    decoded = json.loads(b"".join(chunks))
                    if not isinstance(decoded, dict):
                        raise SpicyError("invalid_response")
                    body = decoded
                return Reply(
                    response.status,
                    body,
                    {"Retry-After": response.headers.get("Retry-After", "60")},
                )
        except (ClientError, TimeoutError, ValueError, UnicodeDecodeError):
            raise SpicyError("service_unavailable") from None
