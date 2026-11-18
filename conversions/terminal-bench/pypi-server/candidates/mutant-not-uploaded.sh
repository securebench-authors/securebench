#!/bin/sh
# The reference without its last step: the server runs and the package is
# built in /tmp/vectorops/dist, but never uploaded, so the server does not
# host it.
set -e
cd /app
here="$(dirname "$0")"
python3 "$here/variant.py" "$here/reference.sh" /tmp/variant.sh \
  'twine upload --verbose --repository-url http://localhost:8080 \' 'true \'
sh /tmp/variant.sh
