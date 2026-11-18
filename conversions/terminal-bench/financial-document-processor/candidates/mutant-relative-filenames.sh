#!/bin/sh
# Requirement: the summary's filename column names each invoice. This one
# writes each name relative to the working directory /app ("invoices/<name>"),
# which upstream opens as /app/invoices/invoices/<name> and does not find. It
# exercises the Oracle's resolution of summary filenames, which reimplements
# pathlib's join and the kernel's path walk.
# Built from reference.sh with one sed change. It exits 1 without running
# anything if the change did not touch exactly 1 line, so it can never
# silently become the reference.
set -e
here="$(cd "$(dirname "$0")" && pwd)"
work="$(mktemp -d)"
cat > "$work/edit.sed" <<'SED'
s/^                writer.writerow(\[result\['filename'\], total_display, vat_display\])$/                writer.writerow(['invoices\/' + result['filename'], total_display, vat_display])/
SED
sed -f "$work/edit.sed" "$here/reference.sh" > "$work/solve.sh"
changed="$(diff "$here/reference.sh" "$work/solve.sh" | grep -c '^>' || true)"
if [ "$changed" -ne 1 ]; then
  echo "mutation changed $changed lines, expected 1" >&2
  exit 1
fi
cd /app
sh "$work/solve.sh"
