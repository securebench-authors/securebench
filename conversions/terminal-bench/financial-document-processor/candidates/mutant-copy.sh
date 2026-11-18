#!/bin/sh
# Requirement: move the documents, leaving /app/documents empty. This one
# copies each document, so the originals stay in /app/documents.
# Built from reference.sh with one sed change. It exits 1 without running
# anything if the change did not touch exactly 2 lines, so it can never
# silently become the reference.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
cat > "$work/edit.sed" <<'SED'
s/^import os$/import os, shutil/
s/^                file_path.rename(dest_path)$/                shutil.copy2(file_path, dest_path)/
SED
sed -f "$work/edit.sed" "$here/reference.sh" > "$work/solve.sh"
changed="$(diff "$here/reference.sh" "$work/solve.sh" | grep -c '^>' || true)"
if [ "$changed" -ne 2 ]; then
  echo "mutation changed $changed lines, expected 2" >&2
  exit 1
fi
cd /app
sh "$work/solve.sh"
