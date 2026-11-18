#!/bin/sh
# The reference without its IEEE 754 branch: it decodes the one-byte integer
# values but drops every word whose value is stored as a double, so it
# recovers 6 of the 8 tested rows.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -q '                    if (0.1 <= double_value' "$here/reference.sh" || exit 1
sed 's|                    if (0.1 <= double_value|                    if False and (0.1 <= double_value|' "$here/reference.sh" | sh
