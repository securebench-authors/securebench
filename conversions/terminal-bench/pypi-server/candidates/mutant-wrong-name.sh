#!/bin/sh
# The reference, with the distribution named vector_ops (the import package is
# still vectorops), so pip finds no project called vectorops.
set -e
cd /app
here="$(dirname "$0")"
python3 "$here/variant.py" "$here/reference.sh" /tmp/variant.sh \
  'name="vectorops"' 'name="vector_ops"'
sh /tmp/variant.sh
