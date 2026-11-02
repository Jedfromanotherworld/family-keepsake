# Hosting the archive online

This configuration targets **one Linux server with a persistent local disk**. Hosting has not been purchased or set up. Keep access limited to trusted family accounts.

## Prerequisites

- A Linux host with Docker Engine and Docker Compose.
- A domain/subdomain whose DNS points to that host.
- Inbound ports 80/443 open, SSH restricted and maintained, enough persistent storage.
- An independent encrypted backup destination and a person responsible for recovery.

## Deploy

1. Copy or clone this project to the server. Store it on persistent storage.
2. Copy `.env.example` to `.env`. Set `DOMAIN` to the real hostname (no `https://`) and `SECRET_KEY` to a long random string. Generate a secret locally with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Keep that result private. Set `STORAGE_LIMIT_GB` below available disk capacity with extra headroom for temporary files/backups. This is an app quota, not a hosting purchase.

3. Build, initialize and create the first administrator before starting the services:

```bash
docker compose build
docker compose run --rm app python -m flask --app app init-db
docker compose run --rm app python -m flask --app app create-user --admin
docker compose up -d
```

Caddy is configured to handle HTTPS for `DOMAIN`. Check DNS, reachability and certificate logs if setup fails. Open `https://YOUR_DOMAIN`, sign in, upload a non-sensitive test photo, restart the services, and verify it is still there. Test video playback and download on each family device before uploading your main collection.

The application service is not published directly to the internet. Only the reverse proxy publishes ports. `HTTPS_ONLY=1` enables secure cookies. The `./data` bind mount holds the database, originals and session key. Keep it when rebuilding or updating. Do not delete the host folder.

## Back up

Run from the project directory on the host:

```bash
python3 backup.py --data ./data --output ./backups
```

This script uses only Python's standard library. Arrange a daily server scheduler for this command and an encrypted transfer to your independent backup destination. No scheduler or remote transfer has been configured by this project. Do not call a backup successful until the off-site copy has been verified.

## Deploy an update

Commit/push changes from VS Code and merge the PR. Then, on the host:

```bash
python3 backup.py
git pull --ff-only origin main
docker compose build
docker compose up -d
```

These commands assume the existing schema has not changed. Future schema changes require reviewed migrations and a fresh backup; `init-db` is not an upgrade/migration tool. Avoid running multiple app replicas with SQLite. The included two Gunicorn workers share one local database on one host.

## Restore after a failure

1. Stop the app. Retain its original data folder unchanged.
2. Copy the trusted backup to the host and verify it.
3. Run `python3 restore.py BACKUP.zip restored-data`.
4. Test the restored database and media in an isolated local instance, then change the Compose data mount to the restored directory.
5. Set your production secret again, restart, and verify uploads/downloads. Session cookies are intentionally not restored.

SQLite backup snapshots include every referenced immutable upload. Never manually delete or modify upload objects while a backup runs.

## Production maintenance

Keep Python, Flask, Gunicorn, Docker and Caddy updated; review dependency security notices, monitor disk/errors and set host-level request/connection limits. Back up before upgrades. The login limiter is per email and persists in SQLite; a production reverse proxy/network should also provide broader abuse protection. Consider MFA, managed object storage, malware scanning and thumbnail workers before expanding beyond trusted family use.

Do not deploy on a free host that sleeps, deletes disks, or lacks a documented persistence contract. Compare provider retention, capacity, availability, export and billing terms before choosing one. No provider or pricing commitment is included here.

References:
- https://flask.palletsprojects.com/en/stable/deploying/
- https://flask.palletsprojects.com/en/stable/patterns/fileuploads/
- https://caddyserver.com/docs/caddyfile
