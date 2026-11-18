#!/bin/sh
# Requirement: classify by content. This one calls a document an invoice
# when its text contains "total", so the shipping record that lists line
# totals (an "other" document) goes to /app/invoices and into the summary.
# Built from reference.sh with one sed change. It exits 1 without running
# anything if the change did not touch exactly 1 line, so it can never
# silently become the reference.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
cat > "$work/edit.sed" <<'SED'
/^        text_lower = text.lower()$/a\
        return 'invoice' if 'total' in text_lower else 'other'
SED
sed -f "$work/edit.sed" "$here/reference.sh" > "$work/solve.sh"
changed="$(diff "$here/reference.sh" "$work/solve.sh" | grep -c '^>' || true)"
if [ "$changed" -ne 1 ]; then
  echo "mutation changed $changed lines, expected 1" >&2
  exit 1
fi
cd /app
sh "$work/solve.sh"
