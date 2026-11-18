#!/bin/sh
# The reference, with dotproduct in vectorops/core.py and an empty __init__.py,
# so `from vectorops import dotproduct` fails.
set -e
cd /app
here="$(dirname "$0")"
python3 "$here/variant.py" "$here/reference.sh" /tmp/variant.sh \
  "cat > vectorops/__init__.py << 'EOF'" "touch vectorops/__init__.py
cat > vectorops/core.py << 'EOF'"
sh /tmp/variant.sh
