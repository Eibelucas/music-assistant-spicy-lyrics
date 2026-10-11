"""Create a clean Docker build context from the pinned, patched frontend build."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

FRONTEND_COMMIT = "e779b9d359e47cd210c2801f16a0ce6263571903"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frontend", type=Path, required=True, help="Patched frontend checkout")
    parser.add_argument("--output", type=Path, default=Path("dist/spicy-lyrics-2.10.6.tar.gz"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    checkout = args.frontend.resolve()
    commit = subprocess.check_output(["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True).strip()
    if commit != FRONTEND_COMMIT:
        raise SystemExit("Frontend source revision mismatch; no bundle created.")
    frontend = checkout / "music_assistant_frontend"
    if not (frontend / "index.html").is_file():
        raise SystemExit("Build the patched frontend first (pnpm run build).")
    if not any(b"spicy_lyrics/get" in path.read_bytes() for path in frontend.rglob("*.js")):
        raise SystemExit("Compiled frontend does not contain the Spicy Lyrics command.")
    provider = root / "server/music_assistant/providers/spicy_lyrics"
    manifest = json.loads((provider / "manifest.json").read_text(encoding="utf-8"))
    if manifest["domain"] != "spicy_lyrics":
        raise SystemExit("Unexpected provider manifest.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with tarfile.open(args.output, "w:gz") as archive:
        archive.add(root / "Dockerfile", arcname="Dockerfile")
        archive.add(root / "install_image.py", arcname="payload/install_image.py")
        archive.add(root / "setup_translations.json", arcname="payload/setup_translations.json")
        archive.add(root / "scripts/verify_install.py", arcname="verify_install.py")
        for path in sorted(provider.iterdir()):
            if path.is_file() and path.suffix in {".py", ".json"}:
                archive.add(path, arcname="payload/provider/" + path.name)
        for path in sorted(frontend.rglob("*")):
            if path.is_file() and path.suffix not in {".py", ".pyc"} and path.name != "py.typed":
                archive.add(path, arcname="payload/frontend/" + path.relative_to(frontend).as_posix())
                count += 1
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    checksum = args.output.with_name(args.output.name + ".sha256")
    checksum.write_text(f"{digest}  {args.output.name}\n", encoding="utf-8")
    print(json.dumps({"bundle": str(args.output), "sha256": digest, "frontend_files": count}))


if __name__ == "__main__":
    main()
