#!/bin/sh
# Semantic-versioning helpers for the release and tracking workflows.
#
#   scripts/semver.sh level <from> <to>      -> major | minor | patch | none
#       the largest component that changed between two versions (v prefix ok)
#   scripts/semver.sh bump <version> <level> -> the next version
#   scripts/semver.sh current                -> newest "## [x.y.z]" in CHANGELOG.md
set -eu

strip() { printf %s "${1#v}"; }
part() { printf %s "$1" | cut -d. -f"$2"; }

case "${1:-}" in
    level)
        a="$(strip "$2")"; b="$(strip "$3")"
        if [ "$(part "$a" 1)" != "$(part "$b" 1)" ]; then echo major
        elif [ "$(part "$a" 2)" != "$(part "$b" 2)" ]; then echo minor
        elif [ "$a" != "$b" ]; then echo patch
        else echo none
        fi
        ;;
    bump)
        v="$(strip "$2")"
        major="$(part "$v" 1)"; minor="$(part "$v" 2)"; patch="$(part "$v" 3)"
        case "$3" in
            major) echo "$((major + 1)).0.0" ;;
            minor) echo "$major.$((minor + 1)).0" ;;
            patch) echo "$major.$minor.$((patch + 1))" ;;
            *) echo "unknown level: $3" >&2; exit 1 ;;
        esac
        ;;
    current)
        here="$(cd "$(dirname "$0")/.." && pwd)"
        sed -n 's/^## \[\([0-9][0-9.]*\)\].*/\1/p' "$here/CHANGELOG.md" | head -n1
        ;;
    *)
        echo "usage: $0 level <from> <to> | bump <version> <level> | current" >&2
        exit 2
        ;;
esac
