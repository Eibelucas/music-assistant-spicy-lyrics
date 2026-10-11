# Development and validation

The native provider is under `server/music_assistant/providers/spicy_lyrics/`. It registers `spicy_lyrics/get` with Music Assistant's queue-read scope and returns lyrics for the requested queue's current track. A browser never receives the secret key.

`frontend.patch` adds the renderer/composable/parser and modifies the existing player component to use it while the provider is available. It adds no route or alternate player screen. The existing timing composable and lyrics-offset setting are reused.

## Transport tests

These tests use fake responses and the Python standard library; they make no real API requests:

```sh
python -m unittest discover -s tests -v
```

They cover Spotify ID mapping, caching, concurrent-request deduplication, negative results, rate limits and expiry. The GitHub Actions workflow runs these eight tests and checks Python syntax.

## Frontend tests and build

Use the exact frontend checkout and patch procedure in [the tutorial](INSTALLATION.md). In that checkout:

```sh
pnpm exec vitest run src/helpers/spicyLyrics.test.ts src/composables/lyrics/useSpicyLyrics.test.ts
pnpm run build
```

The initial validation also ran the existing playback-clock tests: 19 tests passed in total. Production build/type checking and lint for changed files passed. New UI data covers syllable, line and static lyrics, rejects invalid input, and ignores stale results after a track change.

## Server source patch

For server development, use a clean checkout of tag `2.10.6` / commit `c24866405bd2068c25a60e1014e5ef8c3f6445bb` and apply `server.patch`. This patch includes the provider and flattened English/German setup translations.

```sh
git clone --branch 2.10.6 --depth 1 https://github.com/music-assistant/server.git ma-server
git -C ma-server apply --check ../music-assistant-spicy-lyrics/server.patch
git -C ma-server apply ../music-assistant-spicy-lyrics/server.patch
```

The full server requires Python 3.14. Follow the [upstream developer documentation](https://developers.music-assistant.io/) for its development environment. The image installation does not require rebuilding the entire server: it overlays the provider/translations and compiled frontend onto a clean compatible image.

## Checks performed and remaining limits

The initial deployment used Music Assistant 2.10.6, frontend 2.17.297 and Python 3.14. Provider/setup imports passed inside the installed runtime; 306 frontend asset hashes matched after a Supervisor restart. Music Assistant reported `running`, and its log confirmed the configured provider loaded.

A full live lyric request and animation session has not been verified. The original Spicy animation renderer is not included. Server pre-commit hooks could not all run in the original Windows environment because Bash was unavailable. Installation on different versions and architectures has not been checked.

Use `scripts/verify_install.py` with the image's own Python to verify imports, the provider manifest and recorded frontend hashes. That script does not access secrets and does not call the lyrics API.

## Contributions

Include exact MA/frontend versions, a reproducible problem and the relevant non-secret error in reports. Never attach secret API keys, Home Assistant tokens, runtime environment dumps or private backups. Changes to track matching or rendering should include a meaningful fixture/test and respect upstream attribution.
