#!/bin/sh
# Copy the kiosk UI from a kiosk-app checkout into frontend/.
# Usage: scripts/sync-frontend.sh <kiosk-app-dir>
#
# The UI is shared unchanged with kiosk-app; only the lines listed below are
# patched for the microservice deployment. Add a sed line here when another
# local difference is needed, so every sync keeps it.
set -eu
src="$1"
here="$(cd "$(dirname "$0")/.." && pwd)"
dst="$here/frontend"

for f in index.html css js; do
    [ -e "$src/frontend/$f" ] || { echo "missing $src/frontend/$f" >&2; exit 1; }
done
rm -rf "$dst/css" "$dst/js"
cp "$src/frontend/index.html" "$dst/index.html"
cp -R "$src/frontend/css" "$dst/css"
cp -R "$src/frontend/js" "$dst/js"

# Backups live on the system service's volume, not next to a SQLite file.
sed -i 's|keeps the newest ${b.keep} · stored in <code>data/backups/</code> next to the database.|keeps the newest ${b.keep} · stored on the backup volume of the system service (one archive with every service database).|' "$dst/js/admin.js"

echo "frontend synced from $src"
