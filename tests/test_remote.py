"""Exercise lookup, concurrent deduplication, cooldown and safe ID matching."""

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

path = Path(__file__).resolve().parents[1] / "server/music_assistant/providers/spicy_lyrics/remote.py"
spec = importlib.util.spec_from_file_location("spicy_remote", path)
remote = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = remote
spec.loader.exec_module(remote)

TRACK = "1QV6tiMFM6fSOKOGLMHYYg"
OTHER = "7KNmIjcmGJIBrhP2s5Vioe"


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_requests_are_deduplicated(self):
        calls = []

        async def request(track):
            calls.append(track)
            await asyncio.sleep(0)
            return remote.Reply(200, {"Body": {"Type": "Line", "id": track}}, {})

        client = remote.SpicyClient(request)
        results = await asyncio.gather(client.get(TRACK), client.get(TRACK))
        self.assertEqual(len(calls), 1)
        self.assertEqual(results[0], results[1])

    async def test_not_found_is_cached(self):
        calls = []

        async def request(track):
            calls.append(track)
            return remote.Reply(404, {}, {})

        client = remote.SpicyClient(request)
        self.assertIsNone(await client.get(TRACK))
        self.assertIsNone(await client.get(TRACK))
        self.assertEqual(calls, [TRACK])

    async def test_rate_limit_blocks_later_requests(self):
        calls = []

        async def request(track):
            calls.append(track)
            return remote.Reply(429, {}, {"Retry-After": "30"})

        client = remote.SpicyClient(request)
        for track in (TRACK, OTHER):
            with self.assertRaisesRegex(remote.SpicyError, "rate_limited"):
                await client.get(track)
        self.assertEqual(calls, [TRACK])

    async def test_invalid_key_is_not_cached_as_missing_lyrics(self):
        async def request(track):
            return remote.Reply(401, {}, {})

        client = remote.SpicyClient(request)
        with self.assertRaisesRegex(remote.SpicyError, "invalid_api_key"):
            await client.get(TRACK)
        self.assertFalse(client.cache)

    async def test_invalid_track_never_reaches_transport(self):
        async def request(track):
            self.fail("Invalid input reached transport")

        with self.assertRaisesRegex(remote.SpicyError, "invalid_track"):
            await remote.SpicyClient(request).get("../../secret")

    async def test_malformed_service_body_is_rejected(self):
        async def request(track):
            return remote.Reply(200, {"Body": "invalid"}, {})

        with self.assertRaisesRegex(remote.SpicyError, "invalid_response"):
            await remote.SpicyClient(request).get(TRACK)

    def test_resolves_spotify_mapping_from_non_spotify_track(self):
        track = SimpleNamespace(
            uri="library://track/1",
            provider_mappings=[
                SimpleNamespace(provider_domain="tidal", item_id="123"),
                SimpleNamespace(provider_domain="spotify", item_id=TRACK),
            ],
        )
        self.assertEqual(remote.spotify_id(track), TRACK)

    def test_uri_fallback_and_missing_mapping(self):
        self.assertEqual(
            remote.spotify_id(SimpleNamespace(uri=f"spotify://track/{TRACK}")), TRACK
        )
        self.assertIsNone(remote.spotify_id(SimpleNamespace(uri="library://track/22")))


if __name__ == "__main__":
    unittest.main()
