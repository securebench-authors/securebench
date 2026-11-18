#!/bin/sh
# The reference writing every value as a JSON string ("10.0") instead of a
# number, against the format in the instructions.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
grep -q '                        "value": value,' "$here/reference.sh" || exit 1
grep -q '                            "value": double_value,' "$here/reference.sh" || exit 1
sed -e 's|                        "value": value,|                        "value": str(value),|' \
    -e 's|                            "value": double_value,|                            "value": str(double_value),|' \
    "$here/reference.sh" | sh
