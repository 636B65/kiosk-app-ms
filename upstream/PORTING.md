# Porting a kiosk-app release

The *Track kiosk-app* workflow opens a PR for every new kiosk-app release with
the frontend already synced. This is the checklist for porting the backend
part (by hand, or by handing this file to an AI assistant). Below, `{{TAG}}` is
the new release and `{{FROM}}` the previously ported one; check kiosk-app out
at `{{TAG}}` into `upstream-src/` (git-ignored) to read its code.

kiosk-app (checked out in `upstream-src/`) is the original monolith: FastAPI in
`upstream-src/backend/`, the same vanilla-JS frontend, Playwright e2e tests.
kiosk-app-ms is the same product as microservices; read `AGENTS.md` and
`docs/architecture.md` first.

What changed upstream:
- `upstream/changes/{{TAG}}.md`: the CHANGELOG sections since {{FROM}}
- `upstream/changes/{{TAG}}-backend.diff`: the backend + e2e diff {{FROM}}..{{TAG}}

The frontend (`frontend/index.html`, `css/`, `js/`) has ALREADY been copied from
upstream by `scripts/sync-frontend.sh`. Do not edit those files by hand; if a
local patch is needed, add it to that script and re-run it with `upstream-src`.

Your job: make every feature, bug fix and security fix of that diff work here.

1. For each backend change, find the owning service (auth, catalog, customer,
   order, settings, audit, report, system) and port it, keeping the
   conventions: database per service, cross-service calls only over
   `/internal/*` with `require_internal`, audit via `audit.record(db, Outbox, ...)`,
   stock changes as single SQL statements, `utcnow()`, `money()`.
   New columns: add them to the model; existing Postgres tables are not
   migrated by `create_all`, so add an idempotent `ALTER TABLE ... ADD COLUMN IF
   NOT EXISTS` in that service's startup (see how `create_schema` is called).
2. New public endpoints: add them to the gateway (`frontend/nginx/default.conf.template`)
   AND `ROUTES` in `tests/integration/conftest.py`, and to `PUBLIC_ENDPOINTS`
   in `tests/integration/test_route_sweep.py` only if they are public upstream.
3. New settings with defaults: `services/settings-service/settings_service/models.py` DEFAULTS.
4. Port the upstream tests that cover the change into `tests/integration/`
   (or a service's own `tests/`). A bug fix needs a test that fails without it.
5. Changes to deployment (Dockerfile, nginx.conf, env vars): mirror them in
   `docker/`, `frontend/`, `docker-compose.yml` and `deploy/` where relevant.
6. Add a `## [x.y.z] - <today>` section to CHANGELOG.md at the top. Bump this
   repo's version the same way upstream bumped (patch -> patch, minor -> minor,
   major -> major) and say "Ported from kiosk-app {{TAG}}" plus a short list.
   Update the test count in README.md if it changed.
7. Run and make pass, fixing your code (never weakening or skipping tests):
     pip install -r requirements-dev.txt -e libs/kiosk_common
     ruff check .
     pytest -q
     node --check frontend/js/*.js

If something cannot be ported sensibly, leave a clear note in
`upstream/changes/{{TAG}}-notes.md` explaining what and why. 
