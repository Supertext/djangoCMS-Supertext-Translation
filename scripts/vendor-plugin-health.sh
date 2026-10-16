#!/usr/bin/env bash
# Copies Supertext Plugin Health (Python) into PKG/_vendor/plugin_health (import it as
# PKG._vendor.plugin_health). Source: https://github.com/Supertext/Commando-Center-Supertext-Translation
# (plugin-health/python).
#
#   scripts/vendor-plugin-health.sh [commit-or-branch]                 (default: main)
#   PLUGIN_HEALTH_DIR=/path/to/clone scripts/vendor-plugin-health.sh   (use a local clone as it is)
#
# The package ships this copy next to the SDK's (a private subpackage, so an installed
# `supertext-plugin-health` can never clash with it); sites install nothing besides the package.
set -euo pipefail
cd "$(dirname "$0")/.."
pkg="djangocms_supertext"
ref="${1:-main}"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
if [ -n "${PLUGIN_HEALTH_DIR:-}" ]; then
  src="$(cd "$PLUGIN_HEALTH_DIR" && pwd)"
else
  git clone -q https://github.com/Supertext/Commando-Center-Supertext-Translation "$work/center"
  git -C "$work/center" checkout -q "$ref"
  src="$work/center"
fi
commit="$(git -C "$src" rev-parse HEAD)"
version="$(sed -n 's/^version = "\(.*\)"$/\1/p' "$src/plugin-health/python/pyproject.toml" | head -1)"
dest="$pkg/_vendor/plugin_health"
rm -rf "$dest"
mkdir -p "$dest"
# The package; it uses relative imports, so only stray absolute references would need rewriting.
(cd "$src/plugin-health/python/src/supertext_plugin_health" && find . -name __pycache__ -prune -o \( -name '*.py' -o -name py.typed \) -print) |
  while read -r file; do
    mkdir -p "$dest/$(dirname "$file")"
    sed "s/\bsupertext_plugin_health\b/$pkg._vendor.plugin_health/g" "$src/plugin-health/python/src/supertext_plugin_health/$file" > "$dest/$file"
  done
if grep -rnE '(^|[^.])\bsupertext_plugin_health\b' "$dest" --include='*.py'; then
  echo "$dest: unprefixed supertext_plugin_health reference left (see above)" >&2
  exit 1
fi
cp "$src/plugin-health/python/LICENSE" "$dest/LICENSE"
[ -f "$pkg/_vendor/__init__.py" ] || printf '"""Third-party code shipped with this package (see each folder\x27s SOURCE)."""\n' > "$pkg/_vendor/__init__.py"
printf '%s\n' "$commit" > "$dest/COMMIT"
printf '# Supertext Plugin Health (bundled copy)\n\nPython part of [Supertext Plugin Health](https://github.com/Supertext/Commando-Center-Supertext-Translation/tree/main/plugin-health),\nversion %s, commit `%s`, imported as `%s._vendor.plugin_health`.\n\nDon\x27t edit these files: fix it in Commando-Center-Supertext-Translation/plugin-health, then run `scripts/vendor-plugin-health.sh`.\n' "$version" "$commit" "$pkg" > "$dest/README.md"
printf '%s\n' "$version" > "$dest/VERSION"
echo "$dest: Supertext Plugin Health (Python) $version from commit $commit"
