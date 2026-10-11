"""Run with the MA image's Python; prints no credentials or runtime environment."""
import asyncio
import hashlib
from importlib.metadata import version
import json
from pathlib import Path

import music_assistant
import music_assistant_frontend
import music_assistant.providers.spicy_lyrics as provider
import music_assistant.providers.spicy_lyrics.setup_flow
from music_assistant_models.provider import ProviderManifest

assert version("music-assistant") == "2.10.6"
assert version("music-assistant-frontend") == "2.17.297"
server = Path(music_assistant.__file__).parent
frontend = Path(music_assistant_frontend.__file__).parent
record = json.loads((server / "spicy_installation.json").read_text())
mismatches = [name for name, expected in record["files"].items()
              if not (frontend / name).is_file()
              or hashlib.sha256((frontend / name).read_bytes()).hexdigest() != expected]
manifest = asyncio.run(ProviderManifest.parse(str(Path(provider.__file__).with_name("manifest.json"))))
assert manifest.domain == "spicy_lyrics"
assert not mismatches, f"Frontend verification failed: {mismatches}"
print(json.dumps({"provider_import": "ok", "manifest": manifest.domain,
                  "frontend_files_checked": len(record["files"]), "mismatches": mismatches}))
