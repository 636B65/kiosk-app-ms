# Kiosk UI + API gateway. Runs as the unprivileged nginx user (101) on port 8080;
# TLS terminates at the Kubernetes Ingress (or a reverse proxy in front of compose).
#
# Built on the official nginx image and made unprivileged here (the same changes
# nginxinc/nginx-unprivileged applies), because that image lagged behind nginx
# security releases. nginx 1.31.10 (mainline) includes the 1.31.9 fixes for
# CVE-2026-123007/-123633/-121810 (HTTP/2, HTTP/3), CVE-2026-125283 (try_files +
# alias) and 1.31.10's CVE-2026-132779 (ssl_early_data).
FROM nginx:alpine@sha256:b50897d5c7b1aa08067c3d90c5e8b3e47ec4e3c91c91446f67820228f7b41e34

# Alpine security fixes released after the base image was built, then run
# without root: no "user" directive, pid and temp files in /tmp, and the
# config/cache directories writable by nginx (the entrypoint renders templates).
RUN apk upgrade --no-cache \
    && sed -i '/^user /d' /etc/nginx/nginx.conf \
    && sed -i 's,^pid .*;,pid /tmp/nginx.pid;,' /etc/nginx/nginx.conf \
    && sed -i '/^http {/a \    client_body_temp_path /tmp/client_temp;\n    proxy_temp_path /tmp/proxy_temp;\n    fastcgi_temp_path /tmp/fastcgi_temp;\n    uwsgi_temp_path /tmp/uwsgi_temp;\n    scgi_temp_path /tmp/scgi_temp;' /etc/nginx/nginx.conf \
    && rm -f /etc/nginx/conf.d/default.conf \
    && chown -R 101:0 /etc/nginx /var/cache/nginx /usr/share/nginx/html \
    && chmod -R g+w /etc/nginx /var/cache/nginx

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
# Write the release files as root, then drop to the nginx user (101) for runtime.
USER root
RUN --mount=type=bind,from=repo,target=/tmp/repo \
    cp /tmp/repo/CHANGELOG.md /usr/share/nginx/html/CHANGELOG.md \
    && sh /tmp/repo/scripts/release-info.sh /tmp/repo "$APP_VERSION" "$GIT_COMMIT" \
       > /usr/share/nginx/html/version.json \
    && chown nginx:nginx /usr/share/nginx/html/CHANGELOG.md /usr/share/nginx/html/version.json
USER 101

EXPOSE 8080
