# A practical ten-year family preservation plan

The application keeps originals without automatic expiry. It cannot guarantee a host will operate, remain paid, or keep a disk healthy for ten years. Set up the following before trusting it as your family's primary archive.

## Three independent copies

1. **Working copy:** the online website's database and uploads on persistent storage.
2. **Local backup:** a verified archive on an external drive, disconnected when not updating it.
3. **Off-site backup:** an encrypted archive in a separate account/provider or physical location. Store its encryption recovery key securely with a trusted adult.

Another directory on the same server is useful for recovery mistakes, but is not an independent copy. GitHub stores the application code, not these memory backups.

## Schedule you can maintain

| When | Action |
|---|---|
| After a significant family upload | Create a backup and copy it off-site |
| Daily when uploads are frequent | Run backup creation and verify the off-site transfer |
| Monthly | Check storage, hosting payments, backup job failures and account access |
| Every three months | Restore into a new folder and open several photos/videos |
| Annually | Review provider terms, export access, software updates and the recovery contact |
| Before changing hosts | Verify complete backup, restore on the new host, compare file counts/checksums |

This is a recommended operational plan, not an automation created by the project.

## Built-in backup behavior

`backup.py` creates a consistent SQLite snapshot and copies every media file referenced by that snapshot. It checks each original against its upload-time SHA-256 digest, includes the database and a manifest, then verifies the finished archive. Removed memories are included. Uploads added after the snapshot will be in the next backup.

An interrupted backup is not a valid backup. The script removes the partial output on failure. Archive creation needs additional disk space roughly equal to the library size. Full backups can be large; retention and off-site transfer are deliberately left to your host's backup system.

`restore.py` verifies checksums and restores only into a destination that does not already exist. It does not overwrite your live data. Only restore archives you trust. The manifest detects accidental corruption; it is not a cryptographic signature against a malicious archive author.

Backups contain original files and password hashes and are **not encrypted by this script**. Encrypt copies before leaving your trusted storage. Never upload them to a public GitHub repository.

## Family continuity

Record the domain registrar, host, billing owner, administrator recovery process, backup location, encryption key recovery location and renewal dates in a private family password manager. Give another trusted adult recovery access. Do not record passwords in this repository.

Preserve original files even if a future website changes. The database, open file formats and checksum manifest let you migrate the collection instead of depending forever on this exact app.
