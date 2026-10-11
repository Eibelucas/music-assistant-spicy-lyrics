# Rollback and official updates

## Disable Spicy Lyrics

Disable the Spicy Lyrics plugin in Music Assistant's plugin settings. When it is unavailable, the frontend uses the existing Music Assistant lyrics renderer. This keeps the installed frontend patch in place but stops using the plugin.

## Restore the original program image

Use the backup record created during installation in `/share/spicy-lyrics/image-backup-TIMESTAMP.txt`. It contains your original image ID, original tag and backup tag. Obtain temporary administrative Docker access again if you already closed it.

Set the values from **your own record**, verify the backup image ID, and reassign the original image to the original tag:

```sh
BACKUP_TAG=YOUR_SAVED_ORIGINAL_BACKUP_TAG
MA_IMAGE=YOUR_SAVED_ORIGINAL_IMAGE_TAG
docker image inspect --format '{{.Id}}' "$BACKUP_TAG"
docker tag "$BACKUP_TAG" "$MA_IMAGE"
```

The ID must match the original ID in your record. Restart the **existing Music Assistant add-on through Home Assistant**, then check that its running image ID matches that original ID. Reload the browser tab.

If the image cache no longer contains the backup tag but you saved an image archive:

```sh
docker load -i /share/spicy-lyrics/YOUR_SAVED_ORIGINAL_IMAGE_ARCHIVE.tar
```

Then repeat the verification/tagging steps. The program image backup does not restore Music Assistant's database; this installation does not replace that database. The now-unavailable Spicy provider configuration may still appear in settings and can be disabled or removed through Music Assistant.

Restore only the image for the Music Assistant version it belongs to. Do not use an old 2.10.6 image over a later version with migrated runtime data without checking Music Assistant's supported downgrade procedure.

## Updating Music Assistant

The modified image is local. Official add-on updates and reinstallations can replace it with the stock image, and storage cleanup can remove unused backup images. There is no automatic update hook in this project.

Before updating:

1. Retain your program-image backup and a normal Music Assistant/Home Assistant data backup.
2. Disable the Spicy provider if the next release does not include this custom provider.
3. Update Music Assistant through its normal supported process.
4. Check which server and frontend versions now run.
5. Rebase and validate the provider/frontend patch for those versions before reinstalling. The current installer intentionally rejects other versions.

Do not rename an older compiled frontend to pretend it is compatible. Server API changes and frontend component changes require an actual compatibility check.

After maintenance, restore protection and close any temporary terminal/SSH access used for the work.
