# Changelog

All notable changes to this project are documented here. Versions follow
[Semantic Versioning](https://semver.org/); the newest `## [x.y.z]` heading is
what `release.yml` tags and publishes.

## [1.0.2] - 2026-11-21

### Security
- **nginx 1.30.6 -> 1.31.9** in the frontend/gateway image. 1.31.9 fixes, among others,
  CVE-2026-123007 (HTTP/2 flow-control overflow), CVE-2026-123633 / CVE-2026-121810
  (HTTP/2 and HTTP/3 use-after-free), CVE-2026-125283 (`try_files` + `alias` buffer
  overflow), CVE-2026-123634 (resolver use-after-free) and CVE-2026-120967 (stream SNI).
  `nginxinc/nginx-unprivileged` had no build with these fixes, so the image is now built
  on the official `nginx:alpine` and made unprivileged in our Dockerfile. It still runs as
  uid 101 on port 8080, with pid and temp files in `/tmp`, so deployments are unchanged.
- Every image applies the OS security updates published after its base image was built
  (`apt-get upgrade` / `apk upgrade` at build time).
- Python: fastapi 0.165.0, SQLAlchemy 2.1.9, pydantic 2.14.4, python-multipart 0.0.34 and
  refreshed transitive locks (`pip-audit`: no known vulnerabilities); dev: ruff 0.17.6,
  pyyaml 6.0.4.
- Postgres 16 pinned to the current `postgres:16-alpine` digest (compose and Kubernetes).
- Actions: ossf/scorecard-action 2.6.0, github/codeql-action 4.39.4.

### Changed
- Ported from kiosk-app v1.5.2 ([release notes](https://github.com/636B65/kiosk-app/releases/tag/v1.5.2)),
  the same security patch release. The frontend code is unchanged; the backend changes
  (lock files, image updates) are covered above. The e2e Playwright bump has no
  counterpart here.

## [1.0.1] - 2026-11-18

### Changed
- Ported from kiosk-app v1.5.1 ([release notes](https://github.com/636B65/kiosk-app/releases/tag/v1.5.1)),
  a patch release with supply-chain hardening only. The frontend is unchanged. The
  hash-locked dependencies, digest-pinned base images, provenance attestations,
  Scorecard, CodeQL, ClusterFuzzLite and the MIT license were already in place here.
- New fuzz targets ported from kiosk-app's: customer PIN validation (in
  `fuzz_usernames.py`) and request payloads for orders, products, stock counts and
  users (`fuzz_schemas.py`).
- Since 1.0.0: OpenSSF Scorecard and supply-chain hardening, the *Track kiosk-app*
  workflow with Semantic Versioning, `pg_dump` from Debian, and Dependabot updates
  (fastapi 0.163.1, psycopg, pydantic-settings, ruff).

## [1.0.0] - 2026-11-11

First release of the kiosk as microservices (a rewrite of
[kiosk-app](https://github.com/636B65/kiosk-app) 1.x for Kubernetes).

### Services

- **auth-service**: admin users, login with per-IP rate limiting, JWT issuing,
  token introspection for the other services (password changes revoke tokens).
- **catalog-service**: categories, products (weekly specials, barcodes, cost
  prices hidden from the public, images), deliveries (restocks), inventory
  counts, and the atomic all-or-nothing stock reservation used by checkout.
- **customer-service**: customers, username rules, PINs (Argon2id over a
  peppered HMAC, lockout after 5 wrong PINs), public lookup with history/stats/
  favorites, reset payment, reset PIN, self-mark-paid.
- **order-service**: tab checkout (PIN -> overdue check -> stock reservation ->
  order), status changes with compare-and-set, stock restored on cancel,
  per-customer statistics and settlement.
- **settings-service**: store-wide settings (currency, payment due date, kiosk
  idle reset, barcode scanning, backup schedule).
- **audit-service**: the audit log, fed by every service through a
  transactional outbox.
- **report-service**: summary, margins, top products/customers, sales by day,
  shrinkage, reorder suggestions and the CSV exports (sales or paid basis).
- **system-service**: aggregated `/api/health`, the admin System page and
  backups (`pg_dump` of every service database into one archive, scheduled).
- **frontend**: the unchanged vanilla-JS kiosk/admin UI served by nginx, which
  is also the API gateway routing `/api/*` to the services.

### Platform

- Kustomize base with a dev and a prod overlay, Argo CD Applications and an
  ApplicationSet, NetworkPolicies, non-root pods with read-only root
  filesystems, liveness/readiness probes.
- One Postgres StatefulSet with a database per service (swap for a managed
  database by changing `DATABASE_URL`).
- docker compose stack for local development; GitHub Actions CI (lint, 40
  in-process integration tests across all services, manifest validation,
  image builds, compose smoke) and image publishing to GHCR. 53 tests in all.
- Track kiosk-app: a daily workflow follows kiosk-app releases (ported: v1.5.0)
  and opens a PR with the synced frontend and the backend diff to port.
