# Kiosk UI + API gateway. Runs as the unprivileged nginx user on port 8080;
# TLS terminates at the Kubernetes Ingress (or a reverse proxy in front of compose).
FROM nginxinc/nginx-unprivileged:1.27-alpine

# Only ${NGINX_*} placeholders are substituted in the template.
ENV NGINX_ENVSUBST_FILTER=^NGINX_

COPY --chown=nginx:nginx nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY --chown=nginx:nginx docker-entrypoint.d/ /docker-entrypoint.d/
COPY --chown=nginx:nginx index.html /usr/share/nginx/html/index.html
COPY --chown=nginx:nginx css/ /usr/share/nginx/html/css/
COPY --chown=nginx:nginx js/ /usr/share/nginx/html/js/

# Release info for the footer (CHANGELOG.md + scripts/release-info.sh come from
# the named build context "repo": compose additional_contexts / buildx --build-context repo=.).
ARG APP_VERSION=
ARG GIT_COMMIT=
# The unprivileged base image runs as nginx (101); the html dir is root-owned.
USER root
RUN --mount=type=bind,from=repo,target=/tmp/repo \
    cp /tmp/repo/CHANGELOG.md /usr/share/nginx/html/CHANGELOG.md \
    && sh /tmp/repo/scripts/release-info.sh /tmp/repo "$APP_VERSION" "$GIT_COMMIT" \
       > /usr/share/nginx/html/version.json \
    && chown nginx:nginx /usr/share/nginx/html/CHANGELOG.md /usr/share/nginx/html/version.json
USER 101

EXPOSE 8080
