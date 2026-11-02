# Keepsake — our family, remembered

A complete, editable family photo/video website for VS Code. Includes a responsive sage-and-cream design, private family accounts, albums, search, year timeline, shared favorites, downloads, recoverable removals, storage tracking, backup/restore scripts, tests, and GitHub Actions.

**Delivery status:** source project hosted in the private GitHub repository `Jedfromanotherworld/family-keepsake`. The website itself is not deployed; external hosting and off-site backups have not been provisioned. No sample family photos or default passwords are included.

## 1. Run it on Windows in VS Code

Install Python 3.12 or newer, Git, and VS Code. Extract the ZIP, then open the `family-keepsake` folder in VS Code. Choose **Terminal → New Terminal**.

Run these commands one at a time in PowerShell (activation is not required):

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app app init-db
.\.venv\Scripts\python.exe -m flask --app app create-user --admin
.\.venv\Scripts\python.exe app.py
```

Enter your name, email and a password of at least 12 characters when prompted. Password entry is hidden; this is normal. Open **http://127.0.0.1:5000** and sign in. Keep the terminal open while using the local website. Ctrl+C stops it without deleting memories.

For macOS/Linux:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m flask --app app init-db
.venv/bin/python -m flask --app app create-user --admin
.venv/bin/python app.py
```

If port 5000 is occupied, run `python -m flask --app app run --port 5001` using your virtual environment's Python.

## 2. Use the website

1. Create albums such as **Birthdays**, **Christmas**, **Family trips** or **Everyday moments**.
2. Select **Add a memory**, choose one file, then enter a title, date, album and story.
3. Open any memory to play its video or download the original.
4. Tap the heart to add it to the family's shared favorites.
5. Open **Family members → Add family member** to create another private account. Share its credentials directly with that person; no invitation emails are sent.
6. Use **Recently removed** to restore something accidentally removed. The app never automatically purges these files.

All accounts belong to one shared family archive. All members can browse/download every active memory, upload files, create albums and change shared favorites. Only the uploader or administrator can remove/restore a memory. Only administrators can add accounts. There is no public registration or public share link.

## 3. What stores your memories?

| Part | Technology / location |
|---|---|
| Interface | HTML, CSS, JavaScript in `templates/` and `static/` |
| Server | Python Flask, `app.py` |
| Database | SQLite, `data/family.db` |
| Original photos/videos | Private filesystem objects in `data/uploads/` |
| Passwords | Werkzeug salted password hashes |
| Sessions | Signed, HTTP-only cookies; CSRF protection on mutations |
| Production | Docker, Gunicorn and Caddy configuration supplied |

SQLite is a real database, suitable for a modest single-server family archive. Media bytes are stored separately to keep the database small. Copying only the database does **not** preserve your photos/videos. Never put live data on an ephemeral hosting disk. Do not use this SQLite configuration across multiple replicas or a shared network filesystem.

## 4. GitHub from VS Code

See **[docs/GITHUB.md](docs/GITHUB.md)** for the full push, pull, branch and pull-request walkthrough. A GitHub Actions test workflow and PR template are included. GitHub stores your source code; it is not the runtime database or the family photo/video backup.

## 5. Put it online

See **[docs/HOSTING.md](docs/HOSTING.md)** for the supplied Docker deployment. You need a persistent Linux host, a domain you control, HTTPS, sufficient disk space and maintained backups. GitHub Pages cannot run this Python backend.

Do not expose the Flask development server to the internet. Flask's official documentation recommends a production WSGI server instead: https://flask.palletsprojects.com/en/stable/deploying/

## 6. Your 10-year preservation goal

**No automatic expiry is not a 10-year guarantee.** This project supplies the application and recovery tools, not a prepaid storage contract. Keeping memories for ten years requires ongoing hosting, payments, software updates, independent backups, restore checks and a family account-recovery plan. See **[docs/PRESERVATION.md](docs/PRESERVATION.md)**.

Run backups from the project folder:

```bash
python backup.py
python backup.py --verify backups/keepsake-YOUR-TIMESTAMP.zip
python restore.py backups/keepsake-YOUR-TIMESTAMP.zip restored-data
```

Use your virtual environment's Python if needed. Restore only into a new directory. Backups include family media and password hashes; keep them private and encrypt off-site copies. Backups are not scheduled automatically.

## 7. Tests and maintenance

```bash
python -m unittest discover -s tests -v
```

The tests cover authentication, authorization, upload/download and byte ranges, rejected file types, quota cleanup, albums, favorites, restore, backup verification and persistence. See `docs/TESTING.md` for the actual verification status and remaining manual checks.

Forgot a password? From the server terminal:

```bash
python -m flask --app app reset-password
```

This changes the password but does not revoke already issued signed session cookies. If a session is compromised, rotate `SECRET_KEY` to log everyone out. With no explicit `SECRET_KEY`, replace the local `data/session.key` while the server is stopped. Keep the new secret consistent across workers.

## Limits of this version

- One file per upload, 250 MiB maximum; no resumable uploads or video transcoding.
- Supported signatures: JPEG, PNG, GIF, WebP, common MP4/MOV and WebM. HEIC needs conversion. Unsupported video codecs may require downloading/converting to H.264 MP4 for playback.
- Header/signature checking is not antivirus scanning or a full media decoder. Use accounts only for trusted family members.
- Originals are used for gallery previews; large libraries would benefit from a thumbnail/background-processing service.
- No email password reset, MFA, public sharing, account-removal interface, metadata editor, automatic off-site backups or automatic deployments.
- Soft removal does not free storage. Permanent deletion is deliberately not offered in the interface.
- 100 GiB default app quota is a configuration limit, not provisioned or purchased disk space. Ensure your host has room for originals, temporary uploads and backups.
- This release has automated backend tests; live hosting, TLS, Docker startup and real-browser/mobile operation require verification on your machine.

## Project map

```text
app.py                 Server, API and SQLite schema
backup.py / restore.py Portable archive creation, verification and recovery
templates/index.html   Login, gallery and dialogs
static/                Styling, client logic and original SVG illustrations
tests/                 Automated integration tests
docs/                  GitHub, hosting, preservation and test guides
.github/               CI workflow and pull-request template
Dockerfile             Production image
compose.yaml           Persistent host + HTTPS reverse proxy
```

Keep `data/`, `backups/`, `.env`, and passwords out of Git. They are excluded by `.gitignore` and `.dockerignore`.
