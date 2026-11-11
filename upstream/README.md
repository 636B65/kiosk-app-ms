# Upstream: kiosk-app

This repository follows [kiosk-app](https://github.com/636B65/kiosk-app), the
monolith it was split from. `kiosk-app.version` is the kiosk-app release whose
features and fixes are ported here.

`.github/workflows/track-kiosk-app.yml` (daily, or Actions > Track kiosk-app >
Run workflow) looks for a newer `vX.Y.Z` tag with `git ls-remote` - no secrets
needed. For a new release it pushes branch `track/kiosk-app-<tag>` with:

- the frontend copied from that release (`scripts/sync-frontend.sh`),
- `changes/<tag>.md` (release notes) and `changes/<tag>-backend.diff`,
- `kiosk-app.version` bumped,

starts CI on it and opens a pull request (or an issue if Actions may not open
PRs). Port the backend diff into the services with `PORTING.md`, add a
CHANGELOG version, merge - the release workflow then publishes new images.
