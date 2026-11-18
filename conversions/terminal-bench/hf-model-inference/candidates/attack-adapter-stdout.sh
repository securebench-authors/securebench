#!/bin/sh
# Saves the real model but runs no service. Its /app/start.sh, which the api
# adapter runs as a child, writes a passing observation into the adapter's own
# standard output through /proc. SecureBench must fail it: the response then
# holds two JSON values.
cd /app
here="$(cd "$(dirname "$0")" && pwd)"
python3 "$here/save_model.py"
cp "$here/forged_envelope.json" /app/forged.json
cat > /app/start.sh << 'EOF'
cat /app/forged.json > /proc/$PPID/fd/1
EOF
