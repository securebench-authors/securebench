#!/bin/sh
# The reference, with the package built as version 0.1.1 instead of 0.1.0.
set -e
cd /app
here="$(dirname "$0")"
python3 "$here/variant.py" "$here/reference.sh" /tmp/variant.sh \
  'version="0.1.0"' 'version="0.1.1"'
sh /tmp/variant.sh
