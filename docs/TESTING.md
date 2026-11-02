# Verification record

Result: **13 tests passed** in the build environment with Python 3.12. JavaScript syntax check passed. The suite uses temporary databases and synthetic test media, not family files.

Covered: private API access, CSRF protection, login/logout, password failure rate limit, admin account creation, member permission boundaries, upload signature rejection, exact original download and HTTP range support, albums, favorites, soft removal/restoration, quota cleanup, backup checksum verification, restoration into a new directory, database persistence and security headers.

JavaScript syntax is checked with `node --check static/app.js`.

Not verified here: real desktop/mobile browser interactions, real camera video codec playback, Docker/Caddy runtime, public HTTPS deployment, GitHub push/CI execution, actual host quotas, scheduled off-site backups or a long-term storage contract.

Before real use, verify:
- Sign in as an administrator and as a family member.
- Upload a photo and a short real phone video. Reopen both after restarting the server.
- Confirm an unauthenticated browser cannot view a copied media URL.
- Create/open an album and use search, year timeline and favorites.
- Remove and restore a memory; download and compare its original.
- Add a family account, sign in from another device and check its permissions.
- Test under/over-size uploads, slow upload connections and storage errors.
- Verify and restore a full backup into a new directory.
- Check HTTPS, cookies, phone layout, keyboard dialog interaction and host disk persistence.
