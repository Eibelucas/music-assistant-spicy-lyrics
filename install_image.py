"""Patch a clean, pinned MA image during Docker build; no runtime data is copied."""
import hashlib
import importlib.util
from importlib.metadata import version
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parent
assert version('music-assistant') == '2.10.6'
assert version('music-assistant-frontend') == '2.17.297'
server = Path(importlib.util.find_spec('music_assistant').origin).parent
frontend = Path(importlib.util.find_spec('music_assistant_frontend').origin).parent
target = server / 'providers/spicy_lyrics'
assert not target.exists(), 'Provider already exists in base image'
assert (root / 'frontend/index.html').is_file()
shutil.copytree(root / 'provider', target, ignore=shutil.ignore_patterns('__pycache__'))
for language, additions in json.loads((root / 'setup_translations.json').read_text()).items():
    assert language in {'en', 'de'}
    path = server / 'translations' / (language + '.json')
    data = json.loads(path.read_text())
    data.update(additions)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
files = {}
for path in (root / 'frontend').rglob('*'):
    if path.is_file():
        relative = path.relative_to(root / 'frontend')
        assert path.suffix not in {'.py', '.pyc'} and path.name != 'py.typed'
        destination = frontend / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
        files[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
import music_assistant.providers.spicy_lyrics
import music_assistant.providers.spicy_lyrics.setup_flow
(server / 'spicy_installation.json').write_text(json.dumps({
    'server': '2.10.6', 'frontend': '2.17.297', 'files': files
}, indent=2) + '\n')
print(json.dumps({'provider_import': 'ok', 'frontend_files': len(files)}))
