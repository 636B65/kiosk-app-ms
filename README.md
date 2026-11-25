# kiosk-app-ms

[![CI](https://github.com/636B65/kiosk-app-ms/actions/workflows/ci.yml/badge.svg)](https://github.com/636B65/kiosk-app-ms/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/636B65/kiosk-app-ms?sort=semver&logo=github)](https://github.com/636B65/kiosk-app-ms/releases/latest)
[![Publish images](https://github.com/636B65/kiosk-app-ms/actions/workflows/publish-images.yml/badge.svg)](https://github.com/636B65/kiosk-app-ms/actions/workflows/publish-images.yml)
[![Last commit](https://img.shields.io/github/last-commit/636B65/kiosk-app-ms?logo=git&logoColor=white)](https://github.com/636B65/kiosk-app-ms/commits/main)
[![License: MIT](https://img.shields.io/github/license/636B65/kiosk-app-ms)](LICENSE)

[![Follows kiosk-app](https://img.shields.io/github/v/release/636B65/kiosk-app?sort=semver&label=follows%20kiosk-app&logo=github)](https://github.com/636B65/kiosk-app/releases/latest)
[![Track kiosk-app](https://github.com/636B65/kiosk-app-ms/actions/workflows/track-kiosk-app.yml/badge.svg)](https://github.com/636B65/kiosk-app-ms/actions/workflows/track-kiosk-app.yml)
[![Semantic Versioning](https://img.shields.io/badge/semver-2.0.0-3F4551?logo=semver&logoColor=white)](https://semver.org/)

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/636B65/kiosk-app-ms/badge)](https://scorecard.dev/viewer/?uri=github.com/636B65/kiosk-app-ms)
[![Scorecard workflow](https://github.com/636B65/kiosk-app-ms/actions/workflows/scorecard.yml/badge.svg)](https://github.com/636B65/kiosk-app-ms/actions/workflows/scorecard.yml)
[![CodeQL](https://github.com/636B65/kiosk-app-ms/actions/workflows/codeql.yml/badge.svg)](https://github.com/636B65/kiosk-app-ms/actions/workflows/codeql.yml)
[![ClusterFuzzLite](https://github.com/636B65/kiosk-app-ms/actions/workflows/cflite.yml/badge.svg)](https://github.com/636B65/kiosk-app-ms/actions/workflows/cflite.yml)
[![Build provenance](https://img.shields.io/badge/build%20provenance-attested-brightgreen?logo=github)](SECURITY.md)
[![Dependabot](https://img.shields.io/badge/Dependabot-enabled-025E8C?logo=dependabot&logoColor=white)](.github/dependabot.yml)
[![Security policy](https://img.shields.io/badge/security-policy-blue?logo=github)](SECURITY.md)

[![Kubernetes](https://img.shields.io/badge/Kubernetes-ready-326CE5?logo=kubernetes&logoColor=white)](deploy/)
[![Argo CD](https://img.shields.io/badge/GitOps-Argo%20CD-EF7B4D?logo=argo&logoColor=white)](deploy/argocd)
[![Kustomize](https://img.shields.io/badge/Kustomize-base%20%2B%20overlays-326CE5?logo=kubernetes&logoColor=white)](deploy/base)
[![Docker images on GHCR](https://img.shields.io/badge/ghcr.io-9%20images-2496ED?logo=docker&logoColor=white)](https://github.com/636B65?tab=packages&repo_name=kiosk-app-ms)
[![Python 3.12](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](docker/service.Dockerfile)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL 16](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](deploy/base/postgres)
[![nginx](https://img.shields.io/badge/nginx-009639?logo=nginx&logoColor=white)](frontend/nginx/default.conf.template)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

The self-service store kiosk from [kiosk-app](https://github.com/636B65/kiosk-app),
rebuilt as microservices for Kubernetes. Customers pick products on a touchscreen,
check out on a tab under their username (optionally protected by a PIN), and the
staff settle the tabs later in the admin panel. Same features, same vanilla-JS
frontend, same HTTP API — split into eight services that each own their data,
deployed with Kustomize and Argo CD.

```
                       ┌──────────────────────┐
  browser ── Ingress ──│ frontend (nginx)     │  static UI + API gateway
                       └──┬───┬───┬───┬───┬───┘
       /api/auth,/users ──┘   │   │   │   │  /api/system, /api/health
   /api/products,... ─────────┘   │   │   └────────────────────┐
   /api/customers ────────────────┘   │ /api/orders            │
                                      │                         │
  ┌──────────┐ ┌───────────┐ ┌────────┴─────┐ ┌─────────┐ ┌─────┴──────┐
  │   auth   │ │  catalog  │ │    orders    │ │customers│ │   system   │
  └────┬─────┘ └─────┬─────┘ └───┬──────┬───┘ └────┬────┘ └─────┬──────┘
       │ users       │ products  │      │          │ PINs       │ pg_dump
  ┌────┴─────┐ ┌─────┴─────┐     │      │     ┌────┴────┐  ┌────┴──────┐
  │ settings │ │   audit   │◄────┘      └────►│ reports │  │ backups   │
  └──────────┘ └───────────┘ outbox events    └─────────┘  │ PVC       │
                                                           └───────────┘
  Postgres: one database per service (auth, catalog, customers, orders, settings, audit)
```

## Services

| Service | Owns | Public routes (via the gateway) |
| --- | --- | --- |
| `auth-service` | admin users, login, JWT | `/api/auth/*`, `/api/users` |
| `catalog-service` | categories, products, stock, restocks, counts, images | `/api/categories`, `/api/products`, `/api/restocks`, `/api/inventory`, `/api/images` |
| `customer-service` | customers, PINs | `/api/customers/*` |
| `order-service` | orders, settlement, customer statistics, purchases, extra payments | `/api/orders`, `/api/purchases`, `/api/extra-payments` |
| `settings-service` | store-wide settings, payment info (Pay screen) and its QR images | `/api/settings`, `/api/images/pay-*` |
| `audit-service` | audit log | `/api/audit` |
| `report-service` | reports, the store balance and CSV exports (no database) | `/api/reports/*` |
| `system-service` | aggregated health, System page, backups (no database) | `/api/health`, `/api/system/*` |
| `frontend` | kiosk/admin UI, API gateway | everything else |

Every service is a FastAPI app built on the shared `libs/kiosk_common` package
(config, database, JWT verification, service client, transactional outbox). The
API contract is the one the monolith had, so the frontend and any API client keep
working; the only new routes are the `/internal/*` endpoints the services use
between themselves, which the gateway never exposes and which require the
shared `INTERNAL_TOKEN`.

See [docs/architecture.md](docs/architecture.md) for how the business rules
(checkout, stock, PINs, due dates, audit) are enforced across service borders.

## Run locally with docker compose

```bash
cp .env.example .env            # fill in SECRET_KEY, INTERNAL_TOKEN, PIN_PEPPER, ADMIN_PASSWORD
docker compose up -d --build
open http://localhost:8080      # kiosk; admin panel at #/admin (user "admin")
curl -s http://localhost:8080/api/health
```

Without `ADMIN_PASSWORD` the auth service prints a random admin password once
in its log (`docker compose logs auth-service`).

## Deploy to Kubernetes

Images are published to `ghcr.io/636b65/kiosk-app-ms/<service>` (tags:
`main` for every push to main, `X.Y.Z` + `latest` for releases).

```bash
# dev: demo secrets are generated by the overlay
kubectl apply -k deploy/overlays/dev

# prod: create the Secret first (see deploy/overlays/prod/secrets.example.yaml)
kubectl create namespace kiosk
kubectl -n kiosk create secret generic kiosk-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -base64 48)" \
  --from-literal=INTERNAL_TOKEN="$(openssl rand -base64 48)" \
  --from-literal=PIN_PEPPER="$(openssl rand -base64 48)" \
  --from-literal=ADMIN_PASSWORD='choose-a-strong-one' \
  --from-literal=POSTGRES_PASSWORD="$(openssl rand -base64 24)"
kubectl apply -k deploy/overlays/prod
```

Set the Ingress host in the overlay (`kiosk.localtest.me` in dev,
`kiosk.example.com` + cert-manager TLS in prod).

### Argo CD

```bash
kubectl apply -n argocd -f deploy/argocd/application-dev.yaml    # auto-sync, self-heal
kubectl apply -n argocd -f deploy/argocd/application-prod.yaml   # manual sync
# or one ApplicationSet for both environments:
kubectl apply -n argocd -f deploy/argocd/applicationset.yaml
```

Releasing to prod = bump the image tags in `deploy/overlays/prod/kustomization.yaml`
(all services ship together under one version) and sync.

### What runs where

- **Postgres**: one StatefulSet, `deploy/base/postgres/init.sql` creates a
  database per service. Point `DATABASE_URL` at a managed database or an
  operator-managed cluster to replace it.
- **Volumes**: `product-images` (catalog) and `backups` (system) are
  ReadWriteOnce, so those two Deployments run one replica with `Recreate`.
  Every other service is stateless and scales horizontally (prod overlay: 2).
- **NetworkPolicies**: default deny; the ingress controller reaches only the
  frontend, kiosk pods reach each other's port 8000, only services reach Postgres.
- **Secrets** (`kiosk-secrets`): `SECRET_KEY` (JWT, shared), `INTERNAL_TOKEN`
  (service-to-service), `PIN_PEPPER` (customer PINs — losing it invalidates every
  PIN), `ADMIN_PASSWORD`, `POSTGRES_PASSWORD`.
- **Backups**: "Back up now" on the System page (or the scheduler, settings
  `backup_interval_hours` / `backup_keep`) writes `kiosk-YYYYmmdd-HHMMSS.tar.gz`
  with a `pg_dump --format=custom` of every database to the backup volume.
  Restore one database with `pg_restore -d <db> --clean <name>.dump`.

## Development

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install --require-hashes -r requirements-dev.txt   # kiosk_common is on pytest's pythonpath
ruff check .                     # lint
pytest -v                        # 63 tests: 50 cross-service integration tests (all services in one process, SQLite) + unit tests
node --check frontend/js/*.js    # frontend syntax (no build step)
kubectl kustomize deploy/overlays/dev | kubeconform -strict -ignore-missing-schemas

# one service on its own (SQLite under data/)
cd services/order-service && PYTHONPATH=../../libs/kiosk_common uvicorn order_service.main:create_app --factory --reload

# change a dependency: edit requirements*.in, then regenerate the hash-locked files
pip install pip-tools
pip-compile --generate-hashes --allow-unsafe requirements.in
pip-compile --generate-hashes --allow-unsafe requirements-dev.in
```

The integration tests wire every service together in-process (`tests/integration/conftest.py`),
route requests through a gateway with the same table as nginx, and cover the
kiosk's business rules end to end — checkout and stock, PINs and lockout, due
dates and the unpaid block, cancel/settle races, reports, backups, the admin
auth sweep and simultaneous checkouts.

### Layout

```
libs/kiosk_common/       shared package: config, db, auth, http client, outbox, audit, testing
services/<name>/         one FastAPI service each (package = name with "_"), own tests/
frontend/                vanilla JS UI + nginx gateway (Dockerfile, nginx/default.conf.template)
docker/service.Dockerfile  one Dockerfile for every Python service (--build-arg SERVICE=...)
deploy/base/             Kustomize base (Deployments, Services, Postgres, PVCs, Ingress, NetworkPolicies)
deploy/overlays/{dev,prod}  environments; deploy/argocd/ Applications + ApplicationSet
tests/integration/       cross-service tests through an in-process gateway
.github/workflows/       ci.yml, publish-images.yml, release.yml
```

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities. The repository is
checked by [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/636B65/kiosk-app-ms),
CodeQL and ClusterFuzzLite (Atheris fuzzers in `tests/fuzz/`). Actions are
pinned to commit SHAs, base images to digests and Python dependencies to hashes
(Dependabot updates all of them), workflows run with read-only tokens unless a
job needs more, and every published image has a signed build provenance
attestation (`gh attestation verify oci://ghcr.io/636b65/kiosk-app-ms/<service>:<version> -R 636B65/kiosk-app-ms`).

## Following kiosk-app

The [Track kiosk-app](.github/workflows/track-kiosk-app.yml) workflow checks
daily for a kiosk-app release newer than `upstream/kiosk-app.version` (now
v1.5.0), the same way terraform-kubernetes tracks ansible-role-kubernetes: no
secrets needed. It opens a PR `Track kiosk-app vX.Y.Z` with the frontend synced
and the backend diff to port; see [upstream/README.md](upstream/README.md).
Enable Settings > Actions > General > "Allow GitHub Actions to create and
approve pull requests" (otherwise it opens an issue instead).

## Releasing

Versions follow [Semantic Versioning](https://semver.org/): PATCH for fixes,
MINOR for backwards-compatible features, MAJOR for breaking API, data or
deployment changes. Releases that follow kiosk-app use the same level as the
kiosk-app release (the tracking PR sets it). Add a `## [x.y.z] - date` section to `CHANGELOG.md` and merge to main. When CI
is green, `release.yml` tags the commit and `publish-images.yml` pushes the nine
images as `x.y.z` and `latest` and creates the GitHub Release. Then bump the
tags in `deploy/overlays/prod/kustomization.yaml` and let Argo CD sync.

## License

[MIT](LICENSE)
