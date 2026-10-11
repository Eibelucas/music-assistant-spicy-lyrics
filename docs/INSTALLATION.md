# Install Spicy Lyrics into the existing Home Assistant add-on

This guide targets **Music Assistant 2.10.6 / frontend 2.17.297**. It replaces the renderer inside the existing player lyrics area. You keep using your existing Music Assistant add-on and its usual Lyrics button.

The installation builds a clean derived Docker image and assigns it to the image name already used by the add-on. Copying files into a running container alone does not work permanently: a Supervisor restart can recreate that container from its image.

## 1. Prepare the build computer

You need Git, Python 3.12 or later, Node.js 24 and pnpm 11.8.0. Build the frontend on your computer rather than on the Home Assistant host. PowerShell users can use the same Git/Python/pnpm commands; run the Linux Docker commands later inside the Home Assistant terminal.

```sh
git clone https://github.com/Eibelucas/music-assistant-spicy-lyrics.git
git clone --branch 2.17.297 --depth 1 https://github.com/music-assistant/frontend.git ma-frontend
git -C ma-frontend rev-parse HEAD
```

The last command must print `e779b9d359e47cd210c2801f16a0ce6263571903`. Keep both repositories beside each other.

Apply the frontend patch from the plugin repository:

```sh
cd music-assistant-spicy-lyrics
git -C ../ma-frontend apply --check ../music-assistant-spicy-lyrics/frontend.patch
git -C ../ma-frontend apply ../music-assistant-spicy-lyrics/frontend.patch
cd ../ma-frontend
pnpm install --frozen-lockfile
pnpm exec vitest run src/helpers/spicyLyrics.test.ts src/composables/lyrics/useSpicyLyrics.test.ts
pnpm run build
cd ../music-assistant-spicy-lyrics
python -m unittest discover -s tests -v
python scripts/build_bundle.py --frontend ../ma-frontend
```

If pnpm is not installed, install the pinned version using your normal Node.js package-manager setup; for example, `npm install -g pnpm@11.8.0`. The frontend build downloads its upstream dependencies and web fonts.

The bundle builder creates:

- `dist/spicy-lyrics-2.10.6.tar.gz`: plugin, compiled frontend, translations and clean image build instructions.
- `dist/spicy-lyrics-2.10.6.tar.gz.sha256`: checksum for verifying the transfer.

The bundle contains no API key or Home Assistant runtime configuration. The provider and translations are included automatically; do not also apply `server.patch` to the installed image.

## 2. Obtain temporary Docker access

Use an existing administrative shell with Docker access on your Home Assistant host. On Home Assistant OS, **Advanced SSH & Web Terminal** can provide this access when its Protection mode is disabled and the terminal app is restarted. That grants access to all add-on containers, so use it only for this installation and close that access afterward.

If you set up temporary external SSH access, use key authentication and restore/remove that access when finished. Do not post passwords, API keys or Home Assistant tokens in GitHub issues.

Transfer the two bundle files to `/share/spicy-lyrics/` using your existing file transfer method. For example, with an already configured SSH account:

```sh
scp -P YOUR_SSH_PORT dist/spicy-lyrics-2.10.6.tar.gz dist/spicy-lyrics-2.10.6.tar.gz.sha256 YOUR_SSH_USER@YOUR_HA_HOST:/share/spicy-lyrics/
```

Create that destination directory first if necessary. Replace the uppercase placeholders with your own connection details. Commands below assume a terminal account that can run `docker`; prepend `sudo -n` when your terminal account requires it.

## 3. Identify and preserve the original image

In the Home Assistant terminal:

```sh
docker ps --format '{{.Names}}  {{.Image}}'
```

Find your **existing Music Assistant** container. Its name may start with `app_` or `addon_`, followed by the repository prefix and `music_assistant`. Set its exact name below; do not use the example placeholder literally.

```sh
MA_CONTAINER=YOUR_EXISTING_MUSIC_ASSISTANT_CONTAINER
MA_IMAGE=$(docker inspect --format '{{.Config.Image}}' "$MA_CONTAINER")
ORIGINAL_ID=$(docker inspect --format '{{.Image}}' "$MA_CONTAINER")
printf 'Current image: %s\nImage ID: %s\n' "$MA_IMAGE" "$ORIGINAL_ID"
```

The supported official image name is `ghcr.io/music-assistant/server:2.10.6`. Stop if the image/version differs. Do not downgrade an updated installation to follow this guide.

Verify both package versions inside the original image. This runs only Python in an isolated temporary container:

```sh
docker run --rm --network none --entrypoint /app/venv/bin/python "$ORIGINAL_ID" -c 'from importlib.metadata import version; import importlib.util; assert version("music-assistant") == "2.10.6"; assert version("music-assistant-frontend") == "2.17.297"; assert importlib.util.find_spec("music_assistant.providers.spicy_lyrics") is None, "Already patched: use your saved original image"; print("Original versions verified")'
```

Create a unique backup tag and a build tag. Keep these values for rollback:

```sh
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
BACKUP_TAG="local/ma-spicy-original:2.10.6-$STAMP"
PATCHED_TAG="local/ma-spicy-patched:2.10.6-$STAMP"
docker tag "$ORIGINAL_ID" "$BACKUP_TAG"
mkdir -p /share/spicy-lyrics
printf 'Original ID: %s\nOriginal tag: %s\nBackup tag: %s\nPatched tag: %s\n' "$ORIGINAL_ID" "$MA_IMAGE" "$BACKUP_TAG" "$PATCHED_TAG" > "/share/spicy-lyrics/image-backup-$STAMP.txt"
```

For a backup independent of Docker's image cache, save the original image. This can use substantial disk space:

```sh
docker save "$BACKUP_TAG" -o "/share/spicy-lyrics/original-image-$STAMP.tar"
```

Copy that image backup and the small backup record to another device if you want recovery after host storage failure. Keep backups private.

## 4. Build and verify the modified image

```sh
cd /share/spicy-lyrics
sha256sum -c spicy-lyrics-2.10.6.tar.gz.sha256
mkdir "build-$STAMP"
tar -xzf spicy-lyrics-2.10.6.tar.gz -C "build-$STAMP"
cd "build-$STAMP"
docker build --pull=false --network=none --build-arg BASE_IMAGE="$BACKUP_TAG" -t "$PATCHED_TAG" .
docker run --rm -i --network none --entrypoint /app/venv/bin/python "$PATCHED_TAG" - < verify_install.py
```

Verification must report `provider_import: ok` and an empty `mismatches` list. The installer also rejects server/frontend version mismatches and an already installed provider. The original implementation included 306 compiled frontend files; a reproducible build can have a different asset count, so use the bundle's own recorded hashes.

This build uses the clean original image plus the plugin/frontend payload. **Do not use `docker commit` on the running add-on**: it can include runtime credentials and configuration in the saved image.

## 5. Activate in your existing add-on

Assign the verified patched image to the same image name the existing add-on uses:

```sh
docker tag "$PATCHED_TAG" "$MA_IMAGE"
docker image inspect --format '{{.Id}}' "$PATCHED_TAG"
```

In Home Assistant, open **Settings → Apps / Add-ons → Music Assistant → Restart**. Avoid an update or reinstall at this point, since that can fetch the stock image again. Restarting Music Assistant briefly interrupts playback.

After the restart, verify the running container and installed files:

```sh
docker inspect --format '{{.Image}}' "$MA_CONTAINER"
docker exec -i "$MA_CONTAINER" /app/venv/bin/python - < verify_install.py
```

The running image ID should match the patched image ID printed above, and file verification should still pass. Check the Music Assistant app logs for startup errors. If the app does not start or the image differs, use [rollback](ROLLBACK.md); do not keep restarting an unknown state.

## 6. Configure and use the plugin

1. Reload the Music Assistant browser tab; use a hard refresh if it still serves old assets.
2. Open **Settings → Plugins → Add plugin → Spicy Lyrics**.
3. Enter a secret key from [Spicy Lyrics for Developers](https://developers.spicylyrics.org/). Secret keys start with `sl_sk_`; a public/client key is not accepted.
4. Finish setup. The server should log `Loaded plugin provider Spicy Lyrics`.
5. Play a song whose Music Assistant metadata includes a Spotify provider mapping. Open the player and the **existing Lyrics button**.

The key stays in Music Assistant's encrypted server-side setup data. When reconfiguring, leave the key field empty to retain the saved key. You do not need to add an API key to the frontend or image build.

## 7. Close temporary access

Re-enable **Protection mode** for the temporary terminal app, stop it, remove any temporary SSH authorized key and external SSH port mapping, and leave its startup setting on manual. If you had a pre-existing terminal setup, restore its prior settings instead of removing access you normally use.

Music Assistant keeps running from the installed image. For later official updates, read [the update and rollback guide](ROLLBACK.md) before installing again.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Spicy Lyrics does not appear in Plugins | Verify the running image, provider imports and server/frontend versions. Reload the frontend. |
| Existing renderer still appears | Ensure the plugin finished setup and is available; check provider errors. |
| Unsupported track | The current track needs an existing Spotify mapping. Matching arbitrary titles is not implemented. |
| No lyrics | The service may not have lyrics for that Spotify ID. |
| Authentication error | Use a valid Spicy secret key, not a public/client key. |
| Temporarily unavailable | Retry after the service's cooldown; repeated requests are deliberately limited. |
| Wrong timing | Adjust Music Assistant's existing lyrics offset. Line/static lyrics do not contain word timing. |
| Patch fails | Confirm the exact source commit and use a clean checkout. Do not force-apply to a different release. |
| Changes disappear after an official update | Build a compatible patch for the new version; this repository only supports the pinned versions. |
