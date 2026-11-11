# Upstream: kiosk-app

This repository follows [kiosk-app](https://github.com/636B65/kiosk-app), the
monolith it was split from. `kiosk-app.version` is the kiosk-app release whose
features and fixes are ported here.

`.github/workflows/upstream-sync.yml` checks for a newer kiosk-app release every
day (or on demand / on a `kiosk-app-release` repository_dispatch) and then:

1. writes that release's CHANGELOG sections and the backend/e2e diff to
   `upstream/changes/<tag>.md` and `<tag>-backend.diff`,
2. copies the frontend (`index.html`, `css/`, `js/`) with `scripts/sync-frontend.sh`,
3. if the `ANTHROPIC_API_KEY` secret is set, lets Claude port the backend changes
   into the services (following `.github/upstream-port-prompt.md`) and run the checks,
4. bumps `kiosk-app.version`, pushes branch `upstream/kiosk-app-<tag>`, runs CI
   on it and opens a pull request (or an issue if Actions may not open PRs).

Review and merge the PR; the release workflow then publishes the new images.
