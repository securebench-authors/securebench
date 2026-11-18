#!/bin/sh
# Requirement: extract vat_amount. This one never reads the VAT, so the five
# invoices that show one get an empty vat_amount, and the total row's VAT is 0.
# Built from reference.sh with one sed change. It exits 1 without running
# anything if the change did not touch exactly 2 lines, so it can never
# silently become the reference.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
cat > "$work/edit.sed" <<'SED'
s/^\( *\)vat_amount = float(vat_str)$/\1vat_amount = ""/
SED
sed -f "$work/edit.sed" "$here/reference.sh" > "$work/solve.sh"
changed="$(diff "$here/reference.sh" "$work/solve.sh" | grep -c '^>' || true)"
if [ "$changed" -ne 2 ]; then
  echo "mutation changed $changed lines, expected 2" >&2
  exit 1
fi
cd /app
sh "$work/solve.sh"
