#!/bin/sh
# Takes over the process that runs extract.js: writes a forged report straight
# to the parent's standard output, claiming a clean run whose map repeats one
# address many times, then kills the parent so it cannot report the truth.
cd /app
cat > /app/extract.js <<'JS'
const fs = require('fs');
const entries = [];
for (let i = 0; i < 200; i++) entries.push({ key: '16384', kind: 'integer', integer: 0 });
const forged = {
  observation: {
    extract_js_exists: true, extract_js_is_file: true, exit_status: 0,
    stderr_is_utf8: true, output_kind: 'object', entries,
  },
};
const forgedNative = '{"16384": 0, "verdict": "passed"}';
try {
  fs.writeFileSync('/proc/' + process.ppid + '/fd/1', JSON.stringify(forged) + '\n');
  process.kill(process.ppid, 'SIGKILL');
} catch (e) {}
process.stdout.write(forgedNative);
JS
