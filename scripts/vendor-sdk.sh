#!/usr/bin/env bash
# Copies the Supertext Python SDK into PKG/_vendor/supertext (import it as
# PKG._vendor.supertext). Source: https://github.com/Supertext/Supertext-API-SDK-and-Guide
# (sdk/python).
#
#   scripts/vendor-sdk.sh [commit-or-branch]        (default: main)
#   SDK_DIR=/path/to/clone scripts/vendor-sdk.sh    (use a local clone as it is)
#
# The package ships this copy (a private subpackage, so an installed `supertext-sdk` can
# never clash with it); sites install nothing besides the package.
set -euo pipefail
cd "$(dirname "$0")/.."
pkg="djangocms_supertext"
ref="${1:-main}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
if [ -n "${SDK_DIR:-}" ]; then
  src="$(cd "$SDK_DIR" && pwd)"
else
  git clone -q https://github.com/Supertext/Supertext-API-SDK-and-Guide "$work/sdk"
  git -C "$work/sdk" checkout -q "$ref"
  src="$work/sdk"
fi
commit="$(git -C "$src" rev-parse HEAD)"
version="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$src/sdk/python/pyproject.toml" | head -1)"
dest="$pkg/_vendor/supertext"
rm -rf "$dest"
mkdir -p "$dest"
cp "$src"/sdk/python/src/supertext/*.py "$src/sdk/python/src/supertext/py.typed" "$dest/"
cp "$src/sdk/python/LICENSE" "$dest/LICENSE"
[ -f "$pkg/_vendor/__init__.py" ] || printf '"""Third-party code shipped with this package (see each folder\x27s SOURCE)."""\n' > "$pkg/_vendor/__init__.py"
printf '%s\n' "$commit" > "$dest/COMMIT"
printf '# Supertext SDK (bundled copy)\n\nPython part of the [Supertext SDK](https://github.com/Supertext/Supertext-API-SDK-and-Guide),\nversion %s, commit `%s`, imported as `%s._vendor.supertext`.\n\nDon\x27t edit these files: fix the SDK in its own repository, then run `scripts/vendor-sdk.sh`.\n' "$version" "$commit" "$pkg" > "$dest/README.md"
printf '%s\n' "$version" > "$dest/VERSION"
echo "$dest: Supertext SDK (Python) $version from commit $commit"
