# One Dockerfile for every Python service. Build from the repository root:
#
#   docker build -f docker/service.Dockerfile --build-arg SERVICE=order-service \
#       --build-context repo=. -t ghcr.io/636b65/kiosk-app-ms/order-service .
#
# SERVICE            directory under services/ (its package is the name with "-" -> "_")
# PG_CLIENT          "1" installs pg_dump from Debian's own archive (system-service).
#                    Debian trixie ships PostgreSQL 17, which dumps the 16 server
#                    (pg_dump must be >= the server version). No third-party
#                    repository or key download, so builds do not depend on it.
FROM python:3.12-slim

ARG SERVICE
ARG PG_CLIENT=""
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1

RUN if [ -n "$PG_CLIENT" ]; then \
        apt-get -o Acquire::Retries=5 update \
        && apt-get -o Acquire::Retries=5 install -y --no-install-recommends postgresql-client \
        && pg_dump --version \
        && rm -rf /var/lib/apt/lists/*; \
    fi

WORKDIR /app
COPY requirements.txt /app/requirements.txt
COPY libs/kiosk_common /app/libs/kiosk_common
RUN pip install -r /app/requirements.txt /app/libs/kiosk_common

COPY services/${SERVICE}/ /app/

# Release info for /healthz and the admin System page (see scripts/release-info.sh).
ARG APP_VERSION=
ARG GIT_COMMIT=
RUN --mount=type=bind,from=repo,target=/tmp/repo \
    sh /tmp/repo/scripts/release-info.sh /tmp/repo "$APP_VERSION" "$GIT_COMMIT" > /app/release.json

RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin kiosk \
    && mkdir -p /app/data/backups /app/data/product_images && chown -R kiosk:kiosk /app
USER 10001

ENV APP_MODULE=${SERVICE}
EXPOSE 8000
# The package name is the service name with dashes replaced by underscores.
CMD ["sh", "-c", "exec uvicorn \"$(echo \"$APP_MODULE\" | tr - _).main:create_app\" --factory --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
