# Spicy Lyrics for Music Assistant

Animated Spicy Lyrics inside Music Assistant's **existing player lyrics area**. Use the usual **Lyrics** button next to the queue/player controls; the cover, queue, playback controls and lyrics offset stay in place.

This project combines a native Music Assistant plugin provider with a small frontend patch. Music Assistant 2.10.6 does not expose a provider hook for replacing that Vue component, so both parts must be installed together.

**[Installation tutorial](docs/INSTALLATION.md)** · **[Rollback and updates](docs/ROLLBACK.md)** · **[Development](docs/DEVELOPMENT.md)**

## Compatibility

| Component | Supported version |
| --- | --- |
| Music Assistant server / Home Assistant add-on | **2.10.6** |
| Music Assistant frontend | **2.17.297** |
| Server source commit | `c24866405bd2068c25a60e1014e5ef8c3f6445bb` |
| Frontend source commit | `e779b9d359e47cd210c2801f16a0ce6263571903` |

Status: **experimental**. Installation into an existing Home Assistant add-on, server startup, provider loading and persistence across a Supervisor restart have been checked. A complete live lyrics/animation session has not yet been verified. Other versions are not supported by the installer.

## Features

- Syllable timing with progressive text highlighting, movement and glow.
- Line-timed and static lyrics when syllable data is unavailable.
- Background vocals, opposite-side vocals and translations when supplied by the API.
- Automatic scrolling and the existing Music Assistant playback clock and lyrics offset.
- Reduced-motion support and source/credit links.
- Server-side secret storage, request caching, concurrent-request deduplication and rate-limit handling.
- Existing Music Assistant lyrics renderer when this plugin is disabled or unavailable.

The animation renderer is an original implementation for Music Assistant. It is **not a port of Spicy Lyrics' original Spicetify renderer**, and identical animation effects are not promised.

## Requirements

You need the supported Music Assistant versions, a Spicy Lyrics **secret API key** (`sl_sk_…`) and administrative Docker access to install the modified program image into the existing Home Assistant add-on.

The API requires a Spotify track ID. This plugin uses Spotify IDs already present in the current track's Music Assistant provider mappings. Tracks without a suitable mapping show an unsupported-track message. Automatic matching by title/artist is not implemented.

Normal add-on restarts retain the local modified image. **An official update, reinstall, or image cleanup may replace it.** Rebuild for the target Music Assistant versions before installing again. This is not a Home Assistant add-on store repository or a ZIP uploader for stock Music Assistant.

## Quick start

1. Follow the [installation tutorial](docs/INSTALLATION.md) to build the patched frontend and install a derived image into your existing add-on.
2. Open Music Assistant → **Settings → Plugins → Add plugin → Spicy Lyrics**.
3. Enter your secret API key in the Music Assistant setup dialog. Do not put it in source files, the image, GitHub, or issue reports.
4. Reload Music Assistant, play a track with a Spotify mapping, and open the existing **Lyrics** area.

## Repository layout

| Path | Purpose |
| --- | --- |
| `server/music_assistant/providers/spicy_lyrics/` | Native plugin and API transport |
| `frontend.patch` | Existing player integration, renderer and frontend tests |
| `server.patch` | Provider and setup translations for source development |
| `install_image.py` | Version-checked installer used during the clean image build |
| `scripts/build_bundle.py` | Package a compiled patched frontend and plugin |
| `scripts/verify_install.py` | Import and installed-file verification |
| `tests/test_remote.py` | Transport tests using no live credentials |
| `docs/` | Installation, rollback and development guides |

## Validation

The initial implementation passed 19 frontend tests and eight transport tests, TypeScript checking, production frontend build and lint checks for the changed frontend files. Both patches were checked against the pinned source revisions. On the installed add-on, the provider/setup imports and 306 frontend files were verified after a Supervisor restart, and the server reported `running`. The plugin was subsequently configured and the server logged `Loaded plugin provider Spicy Lyrics`.

No API key, personal deployment record, SSH credential, Home Assistant backup, or installation-specific network address is included in this repository. See [development notes](docs/DEVELOPMENT.md) for reproducible checks and remaining validation limits.

## License and upstream projects

Apache-2.0; see [LICENSE](LICENSE) and [NOTICE](NOTICE). Existing upstream copyright notices are retained. Use of the external lyrics API remains subject to the service's own terms.

- [Music Assistant server](https://github.com/music-assistant/server/tree/2.10.6)
- [Music Assistant frontend](https://github.com/music-assistant/frontend/tree/2.17.297)
- [Music Assistant provider development](https://developers.music-assistant.io/)
- [Spicy Lyrics API documentation](https://developers.spicylyrics.org/)

This is a community project and is not an official Music Assistant or Spicy Lyrics release.
