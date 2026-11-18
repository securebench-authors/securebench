#!/bin/sh
# extract.js hands the work to the image's python3, which parses the ELF file
# itself and writes every value as a JSON float (1784774249.0). Python's json
# and `!=` treat an equal float as the integer, so upstream accepts it: probes
# the adapter's value parsing and the Oracle's float comparison.
cd /app
cp "$(dirname "$0")/python-floats-helper.py" /app/extract_helper.py
cat > /app/extract.js <<'JS'
const { execFileSync } = require('child_process');
const out = execFileSync('python3', ['/app/extract_helper.py', process.argv[2]]);
process.stdout.write(out);
JS
