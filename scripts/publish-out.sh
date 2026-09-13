#!/usr/bin/env bash
# Copy the static export in out/ to the repository root (GitHub Pages serves main:/).
# Directories are replaced wholesale so pages removed from content/ disappear from the site.
set -euo pipefail
cd "$(dirname "$0")/.."
[ -d out ] || { echo "out/ not found — run npm run build first" >&2; exit 1; }
PROTECTED=" app components config content lib public scraper scripts node_modules .github .git .next "
for entry in out/*; do
  name=$(basename "$entry")
  case "$PROTECTED" in *" $name "*) echo "refusing to overwrite source dir '$name'" >&2; exit 1;; esac
  if [ -d "$entry" ]; then
    rm -rf "./$name"
    cp -r "$entry" "./$name"
  else
    cp "$entry" "./$name"
  fi
done
echo "published $(find out -name index.html | wc -l) pages to repository root"
